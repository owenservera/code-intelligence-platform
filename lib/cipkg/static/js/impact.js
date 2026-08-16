/**
 * CIP Dashboard v2.0 - Impact Analysis Module
 * Handles: Impact visualization, blast radius graph,
 *          affected files list, recommendations
 */

class ImpactModule {
    constructor() {
        this.container = null;
        this.graphContainer = null;
        this.summaryContainer = null;
        this.detailsContainer = null;
        this.svg = null;
        this.simulation = null;
        this.currentResult = null;

        this._init();
    }

    _init() {
        this.container = document.getElementById('tab-impact');
        this.graphContainer = document.getElementById('impact-graph');
        this.summaryContainer = document.getElementById('impact-summary');
        this.detailsContainer = document.getElementById('impact-details');

        const analyzeBtn = document.getElementById('impact-analyze-btn');
        const symbolInput = document.getElementById('impact-symbol');

        if (analyzeBtn) {
            analyzeBtn.addEventListener('click', () => this._analyze());
        }

        if (symbolInput) {
            symbolInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') this._analyze();
            });
        }
    }

    async _analyze() {
        const symbolInput = document.getElementById('impact-symbol');
        const symbolId = symbolInput?.value.trim();

        if (!symbolId) {
            this._showToast('Please enter a symbol ID or name', 'warning');
            return;
        }

        this._showLoading();

        try {
            const response = await fetch(`/api/impact?symbol=${encodeURIComponent(symbolId)}`);
            if (!response.ok) throw new Error(`Impact analysis failed: ${response.status}`);

            const result = await response.json();
            this.currentResult = result;

            this._renderSummary(result);
            this._renderGraph(result);
            this._renderDetails(result);

            // Update store
            store.setState({
                impact: { symbolId, result, loading: false }
            });

        } catch (e) {
            console.error('Impact analysis error:', e);
            this._renderError(e.message);
        }
    }

    _renderSummary(result) {
        if (!this.summaryContainer) return;

        const impactLevel = result.impact_level || 'unknown';
        const levelColors = {
            'critical': '#F44336',
            'high': '#FF9800',
            'medium': '#FFC107',
            'low': '#4CAF50',
            'unknown': '#9E9E9E'
        };

        const levelColor = levelColors[impactLevel] || levelColors.unknown;

        this.summaryContainer.innerHTML = `
            <div class="impact-metric">
                <div class="impact-metric-value" style="color: ${levelColor}">
                    ${impactLevel.toUpperCase()}
                </div>
                <div class="impact-metric-label">Impact Level</div>
            </div>
            <div class="impact-metric">
                <div class="impact-metric-value">${result.affected_files?.length || 0}</div>
                <div class="impact-metric-label">Affected Files</div>
            </div>
            <div class="impact-metric">
                <div class="impact-metric-value">${result.total_affected_symbols || 0}</div>
                <div class="impact-metric-label">Affected Symbols</div>
            </div>
            <div class="impact-metric">
                <div class="impact-metric-value">${result.test_files?.length || 0}</div>
                <div class="impact-metric-label">Test Files</div>
            </div>
        `;
    }

    _renderGraph(result) {
        if (!this.graphContainer) return;

        // Clear previous
        this.graphContainer.innerHTML = '';

        const width = this.graphContainer.clientWidth || 800;
        const height = this.graphContainer.clientHeight || 400;

        // Build graph data from impact result
        const nodes = [];
        const edges = [];

        // Source node
        nodes.push({
            id: result.symbol_id,
            name: result.symbol_id,
            type: 'source',
            impact: 'source'
        });

        // Affected files as nodes
        (result.affected_files || []).forEach((file, index) => {
            const nodeId = `file_${index}`;
            nodes.push({
                id: nodeId,
                name: file.path.split('/').pop(),
                path: file.path,
                type: 'file',
                impact: this._getFileImpactLevel(index, result.affected_files.length)
            });

            edges.push({
                source: result.symbol_id,
                target: nodeId,
                type: 'affects'
            });

            // Symbols within file
            (file.symbols || []).slice(0, 5).forEach((symbol, symIndex) => {
                const symNodeId = `sym_${index}_${symIndex}`;
                nodes.push({
                    id: symNodeId,
                    name: typeof symbol === 'string' ? symbol : symbol.name || symbol,
                    type: 'symbol',
                    impact: 'low'
                });

                edges.push({
                    source: nodeId,
                    target: symNodeId,
                    type: 'contains'
                });
            });
        });

        // Test files
        (result.test_files || []).forEach((testFile, index) => {
            const testNodeId = `test_${index}`;
            nodes.push({
                id: testNodeId,
                name: testFile.split('/').pop(),
                path: testFile,
                type: 'test',
                impact: 'test'
            });

            edges.push({
                source: result.symbol_id,
                target: testNodeId,
                type: 'tested_by'
            });
        });

        // Create D3 visualization
        this._createD3Graph(nodes, edges, width, height);
    }

    _createD3Graph(nodes, edges, width, height) {
        const svg = d3.select(this.graphContainer)
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        const g = svg.append('g');

        // Zoom
        const zoom = d3.zoom()
            .scaleExtent([0.3, 3])
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            });

        svg.call(zoom);

        // Color scale
        const colorMap = {
            'source': '#2196F3',
            'critical': '#F44336',
            'high': '#FF9800',
            'medium': '#FFC107',
            'low': '#4CAF50',
            'test': '#9C27B0',
            'file': '#607D8B',
            'symbol': '#78909C'
        };

        const sizeMap = {
            'source': 20,
            'file': 14,
            'symbol': 8,
            'test': 12
        };

        // Force simulation
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(edges).id(d => d.id).distance(80))
            .force('charge', d3.forceManyBody().strength(-200))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(d => (sizeMap[d.type] || 10) + 5));

        // Edges
        const edgeElements = g.append('g')
            .selectAll('line')
            .data(edges)
            .enter()
            .append('line')
            .attr('class', 'impact-edge')
            .attr('stroke', d => d.type === 'affects' ? '#F44336' : '#4a5568')
            .attr('stroke-width', d => d.type === 'affects' ? 2 : 1)
            .attr('stroke-opacity', 0.6)
            .attr('stroke-dasharray', d => d.type === 'tested_by' ? '5,3' : null);

        // Nodes
        const nodeElements = g.append('g')
            .selectAll('circle')
            .data(nodes)
            .enter()
            .append('circle')
            .attr('class', 'impact-node')
            .attr('r', d => sizeMap[d.type] || 10)
            .attr('fill', d => colorMap[d.impact] || colorMap[d.type] || '#999')
            .attr('stroke', d => d.type === 'source' ? '#FFD700' : 'rgba(255,255,255,0.5)')
            .attr('stroke-width', d => d.type === 'source' ? 3 : 1.5)
            .attr('cursor', 'pointer')
            .call(d3.drag()
                .on('start', (event, d) => {
                    if (!event.active) simulation.alphaTarget(0.3).restart();
                    d.fx = d.x;
                    d.fy = d.y;
                })
                .on('drag', (event, d) => {
                    d.fx = event.x;
                    d.fy = event.y;
                })
                .on('end', (event, d) => {
                    if (!event.active) simulation.alphaTarget(0);
                    d.fx = null;
                    d.fy = null;
                })
            )
            .on('click', (event, d) => {
                this._nodeClicked(d);
            })
            .on('mouseover', (event, d) => {
                this._showNodeTooltip(event, d);
            })
            .on('mouseout', () => {
                this._hideNodeTooltip();
            });

        // Labels
        const labelElements = g.append('g')
            .selectAll('text')
            .data(nodes)
            .enter()
            .append('text')
            .attr('font-size', '9px')
            .attr('fill', '#e8eaed')
            .attr('text-anchor', 'middle')
            .attr('dy', d => -(sizeMap[d.type] + 5))
            .attr('pointer-events', 'none')
            .text(d => d.name);

        // Tick
        simulation.on('tick', () => {
            edgeElements
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            nodeElements
                .attr('cx', d => d.x)
                .attr('cy', d => d.y);

            labelElements
                .attr('x', d => d.x)
                .attr('y', d => d.y);
        });

        this.simulation = simulation;
    }

    _renderDetails(result) {
        if (!this.detailsContainer) return;

        let html = '';

        // Recommendation
        if (result.recommendation) {
            html += `
                <div class="impact-recommendation">
                    <h4>📋 Recommendation</h4>
                    <p>${this._escapeHtml(result.recommendation)}</p>
                </div>
            `;
        }

        // Affected files list
        if (result.affected_files && result.affected_files.length > 0) {
            html += `
                <div class="impact-files">
                    <h4>📁 Affected Files (${result.affected_files.length})</h4>
                    <div class="impact-files-list">
                        ${result.affected_files.map(file => `
                            <div class="impact-file-item">
                                <span class="file-path">${this._escapeHtml(file.path)}</span>
                                <span class="file-symbols">${file.count || file.symbols?.length || 0} symbols</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        // Test files
        if (result.test_files && result.test_files.length > 0) {
            html += `
                <div class="impact-tests">
                    <h4>🧪 Test Files (${result.test_files.length})</h4>
                    <div class="impact-tests-list">
                        ${result.test_files.map(test => `
                            <div class="impact-test-item">
                                <span class="test-path">${this._escapeHtml(test)}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        this.detailsContainer.innerHTML = html;
    }

    _renderError(message) {
        if (this.summaryContainer) {
            this.summaryContainer.innerHTML = '';
        }
        if (this.graphContainer) {
            this.graphContainer.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">⚠️</div>
                    <div class="empty-state-title">Analysis Failed</div>
                    <div class="empty-state-description">${this._escapeHtml(message)}</div>
                </div>
            `;
        }
        if (this.detailsContainer) {
            this.detailsContainer.innerHTML = '';
        }
    }

    _showLoading() {
        if (this.graphContainer) {
            this.graphContainer.innerHTML = `
                <div class="graph-loading">
                    <div class="spinner lg"></div>
                    <span>Analyzing impact...</span>
                </div>
            `;
        }
        if (this.summaryContainer) {
            this.summaryContainer.innerHTML = `
                <div class="skeleton skeleton-card"></div>
            `;
        }
    }

    _nodeClicked(node) {
        if (node.path) {
            this._showToast(`Opening ${node.path}`, 'info');
        } else {
            this._showToast(`Symbol: ${node.name}`, 'info');
        }
    }

    _showNodeTooltip(event, node) {
        // Create or update tooltip
        let tooltip = document.getElementById('impact-tooltip');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'impact-tooltip';
            tooltip.className = 'map-tooltip';
            document.body.appendChild(tooltip);
        }

        tooltip.innerHTML = `
            <div class="tooltip-header">
                <span class="tooltip-name">${node.name}</span>
                <span class="tooltip-kind">${node.type}</span>
            </div>
            ${node.path ? `<div class="tooltip-path">${node.path}</div>` : ''}
            <div class="tooltip-meta">
                <span>Impact: ${node.impact || 'N/A'}</span>
            </div>
        `;

        tooltip.style.display = 'block';
        tooltip.style.left = (event.pageX + 10) + 'px';
        tooltip.style.top = (event.pageY + 10) + 'px';
    }

    _hideNodeTooltip() {
        const tooltip = document.getElementById('impact-tooltip');
        if (tooltip) {
            tooltip.style.display = 'none';
        }
    }

    _getFileImpactLevel(index, total) {
        if (total <= 3) return 'high';
        if (index < total * 0.3) return 'high';
        if (index < total * 0.6) return 'medium';
        return 'low';
    }

    _escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    _showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `<div class="toast-content"><div class="toast-message">${message}</div></div>`;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }
}

// Initialize
let impactModule;
document.addEventListener('DOMContentLoaded', () => {
    impactModule = new ImpactModule();
    window.impactModule = impactModule;
});
