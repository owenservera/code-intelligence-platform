/**
 * CIP Dashboard v2.0 - Memory Module
 * Handles: Temporal facts timeline, episodic memory,
 *          memory graph visualization, consolidation controls
 */

class MemoryModule {
    constructor() {
        this.factsContainer = null;
        this.episodesContainer = null;
        this.graphContainer = null;
        this.facts = [];
        this.episodes = [];
        this.memoryGraph = null;

        this._init();
    }

    _init() {
        this.factsContainer = document.getElementById('memory-facts');
        this.episodesContainer = document.getElementById('memory-episodes');
        this.graphContainer = document.getElementById('memory-graph');

        // Consolidate button
        const consolidateBtn = document.getElementById('memory-consolidate');
        if (consolidateBtn) {
            consolidateBtn.addEventListener('click', () => this._consolidate());
        }

        // Clear button
        const clearBtn = document.getElementById('memory-clear');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this._confirmClear());
        }

        // Subscribe to WebSocket memory events
        wsClient.subscribe('memory', (data) => {
            this._onMemoryUpdate(data);
        });
    }

    async load() {
        this._showLoading();

        try {
            const response = await fetch('/api/memory');
            if (!response.ok) throw new Error(`Memory load failed: ${response.status}`);

            const data = await response.json();
            this.facts = data.facts || [];
            this.episodes = data.episodes || [];

            this._renderFacts();
            this._renderEpisodes();
            this._renderMemoryGraph();

            // Update store
            store.setState({
                memory: {
                    facts: this.facts,
                    episodes: this.episodes,
                    loading: false
                }
            });

        } catch (e) {
            console.error('Memory load error:', e);
            this._renderError(e.message);
        }
    }

    // === Rendering ===

    _renderFacts() {
        if (!this.factsContainer) return;

        if (this.facts.length === 0) {
            this.factsContainer.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🧠</div>
                    <div class="empty-state-title">No Memories</div>
                    <div class="empty-state-description">
                        Temporal facts will appear here as the agent learns.
                    </div>
                </div>
            `;
            return;
        }

        // Group facts by subject
        const grouped = {};
        this.facts.forEach(fact => {
            const key = fact.subject || 'general';
            if (!grouped[key]) grouped[key] = [];
            grouped[key].push(fact);
        });

        let html = '';

        Object.entries(grouped).forEach(([subject, facts]) => {
            html += `
                <div class="memory-fact-group">
                    <div class="memory-fact-group-header">
                        <span class="group-subject">${this._escapeHtml(subject)}</span>
                        <span class="badge badge-secondary">${facts.length} facts</span>
                    </div>
                    <div class="memory-fact-group-items">
                        ${facts.map(fact => `
                            <div class="memory-fact">
                                <div class="fact-header">
                                    <span class="fact-predicate">${this._escapeHtml(fact.predicate)}</span>
                                    <span class="fact-confidence" title="Confidence: ${(fact.confidence * 100).toFixed(0)}%">
                                        ${this._getConfidenceBadge(fact.confidence)}
                                    </span>
                                </div>
                                <div class="fact-value">${this._formatValue(fact.object_value)}</div>
                                <div class="fact-time">
                                    📅 ${this._formatTimestamp(fact.valid_from)}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        });

        this.factsContainer.innerHTML = html;
    }

    _renderEpisodes() {
        if (!this.episodesContainer) return;

        if (this.episodes.length === 0) {
            this.episodesContainer.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📝</div>
                    <div class="empty-state-title">No Episodes</div>
                    <div class="empty-state-description">
                        Agent interactions and experiences will be recorded here.
                    </div>
                </div>
            `;
            return;
        }

        const typeIcons = {
            'interaction': '💬',
            'error': '❌',
            'success': '✅',
            'debug': '🔧'
        };

        const typeColors = {
            'interaction': '#2196F3',
            'error': '#F44336',
            'success': '#4CAF50',
            'debug': '#FF9800'
        };

        this.episodesContainer.innerHTML = `
            <div class="episodes-timeline">
                ${this.episodes.map(episode => `
                    <div class="episode-item" data-type="${episode.type}">
                        <div class="episode-marker" style="background: ${typeColors[episode.type] || '#999'}">
                            ${typeIcons[episode.type] || '📌'}
                        </div>
                        <div class="episode-content">
                            <div class="episode-header">
                                <span class="episode-type badge" style="background: ${typeColors[episode.type]}20; color: ${typeColors[episode.type]}">
                                    ${episode.type}
                                </span>
                                <span class="episode-time">${this._formatTimestamp(episode.timestamp)}</span>
                            </div>
                            <div class="episode-context">
                                ${this._formatEpisodeContext(episode.context)}
                            </div>
                            ${episode.outcome ? `
                                <div class="episode-outcome">
                                    Outcome: <span class="outcome-${episode.outcome}">${episode.outcome}</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    _renderMemoryGraph() {
        if (!this.graphContainer) return;

        // Build graph from facts and episodes
        const nodes = [];
        const edges = [];

        // Add fact nodes
        this.facts.forEach((fact, index) => {
            nodes.push({
                id: `fact_${index}`,
                name: fact.predicate,
                type: 'fact',
                subject: fact.subject,
                value: fact.object_value
            });

            // Connect to subject node
            const subjectId = `subject_${fact.subject}`;
            if (!nodes.find(n => n.id === subjectId)) {
                nodes.push({
                    id: subjectId,
                    name: fact.subject,
                    type: 'subject'
                });
            }

            edges.push({
                source: subjectId,
                target: `fact_${index}`,
                type: 'has_fact'
            });
        });

        // Add episode nodes (limited)
        this.episodes.slice(0, 20).forEach((episode, index) => {
            nodes.push({
                id: `episode_${index}`,
                name: episode.type,
                type: 'episode'
            });
        });

        // Create simple visualization
        if (nodes.length === 0) {
            this.graphContainer.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🕸️</div>
                    <div class="empty-state-title">No Graph Data</div>
                </div>
            `;
            return;
        }

        // Use D3 for memory graph
        this.graphContainer.innerHTML = '';
        const width = this.graphContainer.clientWidth || 400;
        const height = this.graphContainer.clientHeight || 300;

        const svg = d3.select(this.graphContainer)
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        const g = svg.append('g');

        const colorMap = {
            'fact': '#2196F3',
            'subject': '#4CAF50',
            'episode': '#FF9800'
        };

        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(edges).id(d => d.id).distance(60))
            .force('charge', d3.forceManyBody().strength(-100))
            .force('center', d3.forceCenter(width / 2, height / 2));

        const edgeElements = g.selectAll('line')
            .data(edges)
            .enter()
            .append('line')
            .attr('stroke', '#4a5568')
            .attr('stroke-width', 1)
            .attr('stroke-opacity', 0.4);

        const nodeElements = g.selectAll('circle')
            .data(nodes)
            .enter()
            .append('circle')
            .attr('r', d => d.type === 'subject' ? 10 : 6)
            .attr('fill', d => colorMap[d.type] || '#999')
            .attr('stroke', 'rgba(255,255,255,0.5)')
            .attr('stroke-width', 1);

        simulation.on('tick', () => {
            edgeElements
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            nodeElements
                .attr('cx', d => d.x)
                .attr('cy', d => d.y);
        });
    }

    // === Actions ===

    async _consolidate() {
        this._showToast('Starting memory consolidation...', 'info');

        try {
            const response = await fetch('/api/memory/consolidate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) throw new Error('Consolidation failed');

            const result = await response.json();
            this._showToast(`Consolidation complete: ${result.promoted || 0} patterns promoted`, 'success');

            // Reload memory
            await this.load();

        } catch (e) {
            this._showToast(`Consolidation failed: ${e.message}`, 'error');
        }
    }

    _confirmClear() {
        // Show confirmation modal
        const confirmed = confirm('Are you sure you want to clear all memories? This cannot be undone.');
        if (confirmed) {
            this._clearMemories();
        }
    }

    async _clearMemories() {
        try {
            const response = await fetch('/api/memory/clear', {
                method: 'POST'
            });

            if (!response.ok) throw new Error('Clear failed');

            this._showToast('All memories cleared', 'success');
            this.facts = [];
            this.episodes = [];
            this._renderFacts();
            this._renderEpisodes();
            this._renderMemoryGraph();

        } catch (e) {
            this._showToast(`Clear failed: ${e.message}`, 'error');
        }
    }

    _onMemoryUpdate(data) {
        // Handle real-time memory updates
        if (data.event === 'memory_update') {
            this._showToast(`Memory updated: ${data.type} (${data.count} items)`, 'info');
            this.load(); // Reload
        }
    }

    // === Utilities ===

    _formatValue(value) {
        if (value === null || value === undefined) return 'null';
        if (typeof value === 'object') {
            return `<code>${JSON.stringify(value, null, 2).substring(0, 200)}</code>`;
        }
        return this._escapeHtml(String(value));
    }

    _formatEpisodeContext(context) {
        if (!context) return 'No context';

        const entries = Object.entries(context);
        if (entries.length === 0) return 'Empty context';

        return entries.slice(0, 3).map(([key, value]) =>
            `<span class="context-item"><strong>${key}:</strong> ${this._escapeHtml(String(value).substring(0, 50))}</span>`
        ).join('<br>');
    }

    _formatTimestamp(timestamp) {
        if (!timestamp) return 'Unknown';
        const date = new Date(timestamp * 1000);
        return date.toLocaleString();
    }

    _getConfidenceBadge(confidence) {
        if (confidence >= 0.9) return '<span class="badge badge-primary">High</span>';
        if (confidence >= 0.6) return '<span class="badge badge-warning">Medium</span>';
        return '<span class="badge badge-danger">Low</span>';
    }

    _showLoading() {
        if (this.factsContainer) {
            this.factsContainer.innerHTML = '<div class="skeleton skeleton-card"></div>';
        }
        if (this.episodesContainer) {
            this.episodesContainer.innerHTML = '<div class="skeleton skeleton-card"></div>';
        }
    }

    _renderError(message) {
        const errorHtml = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <div class="empty-state-title">Error Loading Memory</div>
                <div class="empty-state-description">${this._escapeHtml(message)}</div>
            </div>
        `;

        if (this.factsContainer) this.factsContainer.innerHTML = errorHtml;
        if (this.episodesContainer) this.episodesContainer.innerHTML = errorHtml;
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
let memoryModule;
document.addEventListener('DOMContentLoaded', () => {
    memoryModule = new MemoryModule();
    window.memoryModule = memoryModule;
});
