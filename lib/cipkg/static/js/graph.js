/**
 * Interactive Code Graph Visualization using D3.js
 */

class CodeGraph {
    constructor(containerId) {
        this.container = d3.select(`#${containerId}`);
        this.svg = null;
        this.g = null;
        this.zoom = null;
        this.simulation = null;
        this.nodes = [];
        this.edges = [];
        this.nodeElements = null;
        this.edgeElements = null;
        this.labelElements = null;

        this.colorMap = {
            'function': '#4CAF50',
            'method': '#4CAF50',
            'class': '#2196F3',
            'module': '#FF9800',
            'interface': '#9C27B0',
            'variable': '#F44336'
        };

        this.sizeMap = {
            'function': 8,
            'method': 8,
            'class': 12,
            'module': 15,
            'interface': 10,
            'variable': 6
        };

        this._init();
    }

    _init() {
        const width = this.container.node().clientWidth;
        const height = this.container.node().clientHeight;

        // Create SVG
        this.svg = this.container.append('svg')
            .attr('width', width)
            .attr('height', height);

        // Create zoom behavior
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                this.g.attr('transform', event.transform);
            });

        this.svg.call(this.zoom);

        // Create main group
        this.g = this.svg.append('g');

        // Create layers
        this.edgeLayer = this.g.append('g').attr('class', 'edges');
        this.nodeLayer = this.g.append('g').attr('class', 'nodes');
        this.labelLayer = this.g.append('g').attr('class', 'labels');

        // Initialize force simulation
        this.simulation = d3.forceSimulation()
            .force('link', d3.forceLink().id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(d => this.sizeMap[d.kind] + 5));
    }

    setData(nodes, edges) {
        this.nodes = nodes.map(n => ({ ...n }));
        this.edges = edges.map(e => ({ ...e }));

        this._render();
    }

    _render() {
        // Clear existing
        this.edgeLayer.selectAll('*').remove();
        this.nodeLayer.selectAll('*').remove();
        this.labelLayer.selectAll('*').remove();

        // Render edges
        this.edgeElements = this.edgeLayer.selectAll('line')
            .data(this.edges)
            .enter()
            .append('line')
            .attr('class', 'graph-edge')
            .attr('stroke', '#4a5568')
            .attr('stroke-width', 1)
            .attr('stroke-opacity', 0.6);

        // Render nodes
        this.nodeElements = this.nodeLayer.selectAll('circle')
            .data(this.nodes)
            .enter()
            .append('circle')
            .attr('class', 'graph-node')
            .attr('r', d => this.sizeMap[d.kind] || 8)
            .attr('fill', d => this.colorMap[d.kind] || '#999')
            .attr('stroke', '#fff')
            .attr('stroke-width', 2)
            .attr('cursor', 'pointer')
            .call(d3.drag()
                .on('start', (event, d) => this._dragStarted(event, d))
                .on('drag', (event, d) => this._dragged(event, d))
                .on('end', (event, d) => this._dragEnded(event, d))
            )
            .on('click', (event, d) => this._nodeClicked(event, d))
            .on('mouseover', (event, d) => this._nodeHovered(event, d))
            .on('mouseout', () => this._nodeUnhovered());

        // Render labels
        this.labelElements = this.labelLayer.selectAll('text')
            .data(this.nodes)
            .enter()
            .append('text')
            .attr('class', 'graph-label')
            .attr('font-size', '10px')
            .attr('fill', '#e8eaed')
            .attr('text-anchor', 'middle')
            .attr('dy', d => -(this.sizeMap[d.kind] + 5))
            .text(d => d.name)
            .attr('pointer-events', 'none');

        // Update simulation
        this.simulation.nodes(this.nodes)
            .on('tick', () => this._ticked());

        this.simulation.force('link')
            .links(this.edges);
    }

    _ticked() {
        this.edgeElements
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

        this.nodeElements
            .attr('cx', d => d.x)
            .attr('cy', d => d.y);

        this.labelElements
            .attr('x', d => d.x)
            .attr('y', d => d.y);
    }

    _dragStarted(event, d) {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    _dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    _dragEnded(event, d) {
        if (!event.active) this.simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    _nodeClicked(event, d) {
        event.stopPropagation();

        // Update store
        store.setState({
            codeMap: {
                ...store.getState().codeMap,
                selectedNode: d
            }
        });

        // Highlight connected nodes
        this._highlightConnections(d);

        // Show tooltip with details
        this._showTooltip(event, d);
    }

    _nodeHovered(event, d) {
        // Enlarge node
        d3.select(event.target)
            .transition()
            .duration(200)
            .attr('r', (this.sizeMap[d.kind] || 8) * 1.5);

        // Show tooltip
        this._showTooltip(event, d);
    }

    _nodeUnhovered() {
        // Reset all nodes
        this.nodeElements
            .transition()
            .duration(200)
            .attr('r', d => this.sizeMap[d.kind] || 8);

        // Hide tooltip
        this._hideTooltip();
    }

    _highlightConnections(node) {
        const connectedIds = new Set();
        connectedIds.add(node.id);

        this.edges.forEach(edge => {
            if (edge.source.id === node.id) connectedIds.add(edge.target.id);
            if (edge.target.id === node.id) connectedIds.add(edge.source.id);
        });

        // Dim non-connected nodes
        this.nodeElements
            .transition()
            .duration(300)
            .attr('opacity', d => connectedIds.has(d.id) ? 1 : 0.2);

        this.edgeElements
            .transition()
            .duration(300)
            .attr('stroke-opacity', d =>
                (d.source.id === node.id || d.target.id === node.id) ? 1 : 0.1
            );
    }

    _showTooltip(event, node) {
        const tooltip = document.getElementById('map-tooltip');
        tooltip.innerHTML = `
            <strong>${node.name}</strong><br>
            <span style="color: ${this.colorMap[node.kind]}">${node.kind}</span><br>
            <small>${node.path}</small>
        `;
        tooltip.style.display = 'block';
        tooltip.style.left = (event.pageX + 10) + 'px';
        tooltip.style.top = (event.pageY + 10) + 'px';
    }

    _hideTooltip() {
        const tooltip = document.getElementById('map-tooltip');
        tooltip.style.display = 'none';
    }

    // Layout methods
    setLayout(layoutType) {
        switch (layoutType) {
            case 'force':
                this._applyForceLayout();
                break;
            case 'tree':
                this._applyTreeLayout();
                break;
            case 'radial':
                this._applyRadialLayout();
                break;
            case 'grid':
                this._applyGridLayout();
                break;
        }
    }

    _applyForceLayout() {
        this.simulation
            .force('link', d3.forceLink().id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(
                this.container.node().clientWidth / 2,
                this.container.node().clientHeight / 2
            ))
            .alpha(1)
            .restart();
    }

    _applyTreeLayout() {
        // Simplified tree layout
        const width = this.container.node().clientWidth;
        const height = this.container.node().clientHeight;

        this.nodes.forEach((node, i) => {
            node.fx = (i % 10) * (width / 10) + 50;
            node.fy = Math.floor(i / 10) * 60 + 50;
        });

        this.simulation.alpha(0.1).restart();
    }

    _applyRadialLayout() {
        const width = this.container.node().clientWidth;
        const height = this.container.node().clientHeight;
        const centerX = width / 2;
        const centerY = height / 2;
        const radius = Math.min(width, height) / 3;

        this.nodes.forEach((node, i) => {
            const angle = (2 * Math.PI * i) / this.nodes.length;
            node.fx = centerX + radius * Math.cos(angle);
            node.fy = centerY + radius * Math.sin(angle);
        });

        this.simulation.alpha(0.1).restart();
    }

    _applyGridLayout() {
        const width = this.container.node().clientWidth;
        const cols = Math.ceil(Math.sqrt(this.nodes.length));
        const cellWidth = width / cols;
        const cellHeight = 60;

        this.nodes.forEach((node, i) => {
            node.fx = (i % cols) * cellWidth + cellWidth / 2;
            node.fy = Math.floor(i / cols) * cellHeight + 50;
        });

        this.simulation.alpha(0.1).restart();
    }

    // Filter nodes by kind
    filterByKind(kind) {
        if (kind === 'all') {
            this.nodeElements.attr('display', null);
            this.labelElements.attr('display', null);
        } else {
            this.nodeElements
                .attr('display', d => d.kind === kind ? null : 'none');
            this.labelElements
                .attr('display', d => d.kind === kind ? null : 'none');
        }
    }

    // Zoom controls
    zoomIn() {
        this.svg.transition().duration(300).call(
            this.zoom.scaleBy, 1.3
        );
    }

    zoomOut() {
        this.svg.transition().duration(300).call(
            this.zoom.scaleBy, 0.7
        );
    }

    fitToView() {
        const bounds = this.g.node().getBBox();
        const width = this.container.node().clientWidth;
        const height = this.container.node().clientHeight;

        const scale = Math.min(
            width / bounds.width,
            height / bounds.height
        ) * 0.9;

        const translate = [
            width / 2 - scale * (bounds.x + bounds.width / 2),
            height / 2 - scale * (bounds.y + bounds.height / 2)
        ];

        this.svg.transition().duration(500).call(
            this.zoom.transform,
            d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
        );
    }

    reset() {
        this.svg.transition().duration(500).call(
            this.zoom.transform,
            d3.zoomIdentity
        );
        this.simulation.alpha(1).restart();
    }

    // Resize handler
    resize() {
        const width = this.container.node().clientWidth;
        const height = this.container.node().clientHeight;

        this.svg.attr('width', width).attr('height', height);
        this.simulation.force('center', d3.forceCenter(width / 2, height / 2));
        this.simulation.alpha(0.3).restart();
    }
}

// Export
window.CodeGraph = CodeGraph;