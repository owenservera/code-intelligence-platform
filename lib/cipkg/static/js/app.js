/**
 * CIP Dashboard Main Application
 */

class DashboardApp {
    constructor() {
        this.codeGraph = null;
        this.healthChart = null;
        this._init();
    }

    async _init() {
        // Initialize components
        this._initTheme();
        this._initNavigation();
        this._initSearch();
        this._initWebSocket();
        this._initKeyboardShortcuts();

        // Load initial data
        await this._loadInitialData();

        // Initialize code graph when tab is activated
        this._initCodeGraph();

        // Start heartbeat
        wsClient.startHeartbeat();

        console.log('🚀 CIP Dashboard v2.0 initialized');
    }

    _initTheme() {
        const themeBtn = document.getElementById('btn-theme');
        const savedTheme = localStorage.getItem('cip-theme') || 'dark';

        document.documentElement.setAttribute('data-theme', savedTheme);

        themeBtn.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme');
            const newTheme = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('cip-theme', newTheme);
        });
    }

    _initNavigation() {
        const tabs = document.querySelectorAll('.nav-tab');

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabId = tab.dataset.tab;

                // Update active tab
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                // Show corresponding content
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                document.getElementById(`tab-${tabId}`).classList.add('active');

                // Update store
                store.setState({ activeTab: tabId });

                // Load tab-specific data
                this._loadTabData(tabId);
            });
        });
    }

    _initSearch() {
        const searchInput = document.getElementById('global-search');
        const searchResults = document.getElementById('search-results');
        let debounceTimer = null;

        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            const query = e.target.value.trim();

            if (query.length < 2) {
                searchResults.classList.remove('active');
                return;
            }

            debounceTimer = setTimeout(async () => {
                const results = await this._apiSearch(query, 5);
                this._renderSearchDropdown(results);
            }, 300);
        });

        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const query = searchInput.value.trim();
                if (query) {
                    this._performFullSearch(query);
                }
            }
            if (e.key === 'Escape') {
                searchResults.classList.remove('active');
            }
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-container')) {
                searchResults.classList.remove('active');
            }
        });
    }

    _initWebSocket() {
        // Connect WebSocket
        wsClient.connect();

        // Subscribe to events
        wsClient.subscribe('index', (data) => {
            this._showToast('Index updated', 'success');
            this._loadStats();
        });

        wsClient.subscribe('health', (data) => {
            this._updateHealthGauge(data.score);
        });

        wsClient.subscribe('sync', (data) => {
            this._showToast('Sync complete', 'success');
            this._loadStats();
        });

        wsClient.subscribe('memory', (data) => {
            this._showToast('Memory updated', 'info');
        });
    }

    _initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K for search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                document.getElementById('global-search').focus();
            }

            // Ctrl/Cmd + Z for undo
            if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
                if (e.shiftKey) {
                    store.redo();
                } else {
                    store.undo();
                }
            }

            // Number keys for tab switching
            if (e.altKey && e.key >= '1' && e.key <= '7') {
                const tabIndex = parseInt(e.key) - 1;
                const tabs = document.querySelectorAll('.nav-tab');
                if (tabs[tabIndex]) {
                    tabs[tabIndex].click();
                }
            }
        });
    }

    _initCodeGraph() {
        // Initialize when code map tab is first activated
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.target.id === 'tab-code-map' &&
                    mutation.target.classList.contains('active')) {
                    this._loadCodeMap();
                }
            });
        });

        observer.observe(document.getElementById('tab-code-map'), {
            attributes: true,
            attributeFilter: ['class']
        });

        // Map toolbar controls
        document.getElementById('map-zoom-in')?.addEventListener('click', () => {
            this.codeGraph?.zoomIn();
        });

        document.getElementById('map-zoom-out')?.addEventListener('click', () => {
            this.codeGraph?.zoomOut();
        });

        document.getElementById('map-fit')?.addEventListener('click', () => {
            this.codeGraph?.fitToView();
        });

        document.getElementById('map-reset')?.addEventListener('click', () => {
            this.codeGraph?.reset();
        });

        document.getElementById('map-layout')?.addEventListener('change', (e) => {
            this.codeGraph?.setLayout(e.target.value);
        });

        document.getElementById('map-filter')?.addEventListener('change', (e) => {
            this.codeGraph?.filterByKind(e.target.value);
        });
    }

    async _loadInitialData() {
        try {
            // Load stats
            await this._loadStats();

            // Load health
            await this._loadHealth();

            // Load activity
            await this._loadActivity();

            // Update footer
            this._updateFooter();

        } catch (e) {
            console.error('Failed to load initial data:', e);
            this._showToast('Failed to load data', 'error');
        }
    }

    async _loadTabData(tabId) {
        switch (tabId) {
            case 'overview':
                await this._loadHealth();
                await this._loadStats();
                break;
            case 'code-map':
                await this._loadCodeMap();
                break;
            case 'gaps':
                await this._loadGaps();
                break;
            case 'memory':
                await this._loadMemory();
                break;
            case 'settings':
                await this._loadSettings();
                break;
        }
    }

    async _loadStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();

            document.getElementById('stat-files').textContent = this._formatNumber(data.files);
            document.getElementById('stat-symbols').textContent = this._formatNumber(data.symbols);
            document.getElementById('stat-chunks').textContent = this._formatNumber(data.chunks);
            document.getElementById('stat-edges').textContent = this._formatNumber(data.edges);
            document.getElementById('last-sync').textContent = `Last sync: ${data.last_sync}`;

        } catch (e) {
            console.error('Failed to load stats:', e);
        }
    }

    async _loadHealth() {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();

            this._updateHealthGauge(data.score || 0);
            this._renderHealthDetails(data);

        } catch (e) {
            console.error('Failed to load health:', e);
        }
    }

    async _loadCodeMap() {
        try {
            const response = await fetch('/api/graph');
            const data = await response.json();

            if (!this.codeGraph) {
                this.codeGraph = new CodeGraph('code-map');
            }

            this.codeGraph.setData(data.nodes, data.edges);

        } catch (e) {
            console.error('Failed to load code map:', e);
        }
    }

    async _loadGaps() {
        try {
            const response = await fetch('/api/gaps');
            const data = await response.json();

            this._renderGaps(data.gaps);

        } catch (e) {
            console.error('Failed to load gaps:', e);
        }
    }

    async _loadMemory() {
        try {
            const response = await fetch('/api/memory');
            const data = await response.json();

            this._renderMemoryFacts(data.facts);
            this._renderMemoryEpisodes(data.episodes);

        } catch (e) {
            console.error('Failed to load memory:', e);
        }
    }

    async _loadSettings() {
        try {
            const response = await fetch('/api/config');
            const data = await response.json();

            this._renderSettings(data);

        } catch (e) {
            console.error('Failed to load settings:', e);
        }
    }

    async _loadActivity() {
        // For now, show placeholder
        const activityList = document.getElementById('activity-list');
        activityList.innerHTML = `
            <div class="activity-item">🔄 System initialized</div>
            <div class="activity-item">📊 Dashboard loaded</div>
        `;
    }

    // === Rendering Methods ===

    _updateHealthGauge(score) {
        const scoreEl = document.getElementById('health-score');
        scoreEl.textContent = score;

        // Color based on score
        if (score >= 80) {
            scoreEl.style.color = '#4CAF50';
        } else if (score >= 60) {
            scoreEl.style.color = '#FF9800';
        } else {
            scoreEl.style.color = '#F44336';
        }

        // Draw gauge using Chart.js
        const ctx = document.getElementById('health-gauge').getContext('2d');
        if (this.healthChart) {
            this.healthChart.destroy();
        }

        this.healthChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [score, 100 - score],
                    backgroundColor: [
                        score >= 80 ? '#4CAF50' : score >= 60 ? '#FF9800' : '#F44336',
                        '#2a3a4a'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                cutout: '80%',
                responsive: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            }
        });
    }

    _renderHealthDetails(data) {
        const details = document.getElementById('health-details');
        details.innerHTML = `
            <div class="health-detail">
                <span>Coverage:</span>
                <span>${data.coverage || '--'}%</span>
            </div>
            <div class="health-detail">
                <span>Quality:</span>
                <span>${data.quality || '--'}%</span>
            </div>
            <div class="health-detail">
                <span>Recency:</span>
                <span>${data.recency || '--'}%</span>
            </div>
        `;
    }

    _renderSearchDropdown(results) {
        const dropdown = document.getElementById('search-results');

        if (!results || results.length === 0) {
            dropdown.innerHTML = '<div class="search-dropdown-item">No results found</div>';
            dropdown.classList.add('active');
            return;
        }

        dropdown.innerHTML = results.map(result => `
            <div class="search-dropdown-item" data-path="${result.path}" data-line="${result.start_line}">
                <div class="search-dropdown-path">${result.path}</div>
                <div class="search-dropdown-preview">${this._escapeHtml(result.text?.substring(0, 100))}...</div>
            </div>
        `).join('');

        dropdown.classList.add('active');

        // Add click handlers
        dropdown.querySelectorAll('.search-dropdown-item').forEach(item => {
            item.addEventListener('click', () => {
                const path = item.dataset.path;
                const line = item.dataset.line;
                this._showToast(`Opening ${path}:${line}`, 'info');
                dropdown.classList.remove('active');
            });
        });
    }

    _renderGaps(gaps) {
        const list = document.getElementById('gaps-list');
        const summary = document.getElementById('gaps-summary');

        if (!gaps || gaps.length === 0) {
            list.innerHTML = '<div class="gap-item">No gaps found! 🎉</div>';
            summary.textContent = 'No knowledge gaps detected.';
            return;
        }

        // Summary
        const byType = {};
        gaps.forEach(gap => {
            byType[gap.type] = (byType[gap.type] || 0) + 1;
        });

        summary.innerHTML = Object.entries(byType).map(([type, count]) =>
            `<span class="gap-summary-item">${type.replace('_', ' ')}: ${count}</span>`
        ).join(' | ');

        // List
        list.innerHTML = gaps.map(gap => `
            <div class="gap-item">
                <div class="gap-severity ${gap.severity}"></div>
                <div class="gap-content">
                    <div class="gap-title">${gap.description}</div>
                    <div class="gap-description">${gap.path}</div>
                    <div class="gap-fix">💡 ${gap.suggested_fix}</div>
                </div>
            </div>
        `).join('');
    }

    _renderMemoryFacts(facts) {
        const container = document.getElementById('memory-facts');

        if (!facts || facts.length === 0) {
            container.innerHTML = '<div class="memory-fact">No memories stored yet.</div>';
            return;
        }

        container.innerHTML = facts.map(fact => `
            <div class="memory-fact">
                <div class="fact-predicate">${fact.predicate}</div>
                <div class="fact-value">${JSON.stringify(fact.object_value)}</div>
                <div class="fact-time">${new Date(fact.valid_from * 1000).toLocaleString()}</div>
            </div>
        `).join('');
    }

    _renderMemoryEpisodes(episodes) {
        const container = document.getElementById('memory-episodes');

        if (!episodes || episodes.length === 0) {
            container.innerHTML = '<div class="memory-fact">No episodes recorded yet.</div>';
            return;
        }

        container.innerHTML = episodes.map(ep => `
            <div class="memory-fact">
                <div class="fact-predicate">${ep.type}</div>
                <div class="fact-value">${JSON.stringify(ep.context).substring(0, 100)}...</div>
                <div class="fact-time">${new Date(ep.timestamp * 1000).toLocaleString()}</div>
            </div>
        `).join('');
    }

    _renderSettings(config) {
        const sections = {
            'settings-index': config.index,
            'settings-embed': config.embed,
            'settings-retrieval': config.retrieval,
            'settings-memory': config.memory
        };

        Object.entries(sections).forEach(([elementId, sectionConfig]) => {
            const element = document.getElementById(elementId);
            if (element && sectionConfig) {
                element.innerHTML = Object.entries(sectionConfig).map(([key, value]) => `
                    <div class="setting-item">
                        <span class="setting-label">${key}</span>
                        <span class="setting-value">${value}</span>
                    </div>
                `).join('');
            }
        });
    }

    // === API Methods ===

    async _apiSearch(query, limit = 10) {
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=${limit}`);
            const data = await response.json();
            return data.results || [];
        } catch (e) {
            console.error('Search API error:', e);
            return [];
        }
    }

    async _performFullSearch(query) {
        // Switch to search tab
        document.querySelector('[data-tab="search"]').click();

        // Set search input
        document.getElementById('search-input').value = query;

        // Perform search
        const results = await this._apiSearch(query, 20);
        this._renderFullSearchResults(results);
    }

    _renderFullSearchResults(results) {
        const container = document.getElementById('search-results-full');

        if (!results || results.length === 0) {
            container.innerHTML = '<div class="search-result-item">No results found.</div>';
            return;
        }

        container.innerHTML = results.map(result => `
            <div class="search-result-item">
                <div class="search-result-path">${result.path}:${result.start_line}-${result.end_line}</div>
                <div class="search-result-code">${this._escapeHtml(result.text)}</div>
                <div class="search-result-score">Score: ${(result.score * 100).toFixed(1)}%</div>
            </div>
        `).join('');
    }

    // === Utility Methods ===

    _showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        container.appendChild(toast);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }

    _formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    _updateFooter() {
        document.getElementById('footer-time').textContent = new Date().toLocaleTimeString();

        // Update time every second
        setInterval(() => {
            document.getElementById('footer-time').textContent = new Date().toLocaleTimeString();
        }, 1000);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardApp = new DashboardApp();
});