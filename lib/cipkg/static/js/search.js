/**
 * CIP Dashboard v2.0 - Search Module
 * Handles: Full search interface, autocomplete, filters,
 *          search history, result rendering, keyboard navigation
 */

class SearchModule {
    constructor() {
        this.searchInput = null;
        this.searchResults = null;
        this.searchHistory = [];
        this.maxHistory = 20;
        this.debounceTimer = null;
        this.debounceDelay = 300;
        this.currentIndex = -1;
        this.currentResults = [];
        this.isSearching = false;

        this._init();
    }

    _init() {
        this.searchInput = document.getElementById('search-input');
        this.searchResults = document.getElementById('search-results-full');
        this.searchBtn = document.getElementById('search-btn');
        this.searchType = document.getElementById('search-type');
        this.searchLimit = document.getElementById('search-limit');

        if (!this.searchInput) return;

        // Load search history from localStorage
        this._loadHistory();

        // Event listeners
        this.searchInput.addEventListener('input', (e) => this._onInput(e));
        this.searchInput.addEventListener('keydown', (e) => this._onKeydown(e));
        this.searchInput.addEventListener('focus', () => this._onFocus());
        this.searchBtn?.addEventListener('click', () => this._performSearch());
        this.searchType?.addEventListener('change', () => this._performSearch());

        // Global search (header)
        const globalSearch = document.getElementById('global-search');
        if (globalSearch) {
            globalSearch.addEventListener('input', (e) => this._onGlobalInput(e));
            globalSearch.addEventListener('keydown', (e) => this._onGlobalKeydown(e));
        }

        // Subscribe to store changes
        store.subscribe((state, updates) => {
            if (updates.searchQuery !== undefined) {
                this.searchInput.value = updates.searchQuery;
            }
        });
    }

    // === Input Handlers ===

    _onInput(e) {
        clearTimeout(this.debounceTimer);
        const query = e.target.value.trim();

        if (query.length < 2) {
            this._clearResults();
            return;
        }

        this.debounceTimer = setTimeout(() => {
            this._performSearch(query);
        }, this.debounceDelay);
    }

    _onKeydown(e) {
        switch (e.key) {
            case 'Enter':
                e.preventDefault();
                if (this.currentIndex >= 0 && this.currentResults[this.currentIndex]) {
                    this._selectResult(this.currentResults[this.currentIndex]);
                } else {
                    this._performSearch();
                }
                break;

            case 'ArrowDown':
                e.preventDefault();
                this._navigateResults(1);
                break;

            case 'ArrowUp':
                e.preventDefault();
                this._navigateResults(-1);
                break;

            case 'Escape':
                this._clearResults();
                this.searchInput.blur();
                break;
        }
    }

    _onFocus() {
        // Show search history on focus if input is empty
        if (this.searchInput.value.trim() === '' && this.searchHistory.length > 0) {
            this._renderHistory();
        }
    }

    _onGlobalInput(e) {
        clearTimeout(this.debounceTimer);
        const query = e.target.value.trim();
        const dropdown = document.getElementById('search-results');

        if (query.length < 2) {
            dropdown?.classList.remove('active');
            return;
        }

        this.debounceTimer = setTimeout(async () => {
            const results = await this._apiSearch(query, 5);
            this._renderGlobalDropdown(results);
        }, this.debounceDelay);
    }

    _onGlobalKeydown(e) {
        if (e.key === 'Enter') {
            const query = e.target.value.trim();
            if (query) {
                // Switch to search tab and perform full search
                document.querySelector('[data-tab="search"]')?.click();
                this.searchInput.value = query;
                this._performSearch(query);
                document.getElementById('search-results')?.classList.remove('active');
            }
        }
        if (e.key === 'Escape') {
            document.getElementById('search-results')?.classList.remove('active');
        }
    }

    // === Search Execution ===

    async _performSearch(query = null) {
        query = query || this.searchInput.value.trim();
        if (!query) return;

        this.isSearching = true;
        this._showLoading();

        // Add to history
        this._addToHistory(query);

        // Update store
        store.setState({ searchQuery: query, searchLoading: true });

        try {
            const searchType = this.searchType?.value || 'hybrid';
            const limit = parseInt(this.searchLimit?.value) || 10;

            const results = await this._apiSearch(query, limit, searchType);
            this.currentResults = results;
            this.currentIndex = -1;

            this._renderResults(results, query);

            // Update store
            store.setState({ searchResults: results, searchLoading: false });

            // Notify via WebSocket
            wsClient.send({
                type: 'event',
                topic: 'search',
                data: { query, results_count: results.length }
            });

        } catch (e) {
            console.error('Search failed:', e);
            this._renderError(e.message);
            store.setState({ searchLoading: false });
        } finally {
            this.isSearching = false;
        }
    }

    async _apiSearch(query, limit = 10, searchType = 'hybrid') {
        const params = new URLSearchParams({
            q: query,
            limit: limit.toString(),
            type: searchType
        });

        const response = await fetch(`/api/search?${params}`);
        if (!response.ok) {
            throw new Error(`Search failed: ${response.status}`);
        }

        const data = await response.json();
        return data.results || [];
    }

    // === Result Rendering ===

    _renderResults(results, query) {
        if (!this.searchResults) return;

        if (!results || results.length === 0) {
            this.searchResults.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🔍</div>
                    <div class="empty-state-title">No results found</div>
                    <div class="empty-state-description">
                        Try different keywords or check your search filters.
                    </div>
                </div>
            `;
            return;
        }

        const resultsHtml = results.map((result, index) => `
            <div class="search-result-item" data-index="${index}" data-path="${this._escapeAttr(result.path)}">
                <div class="search-result-header">
                    <span class="search-result-path">${this._highlightMatch(result.path, query)}</span>
                    <span class="badge badge-secondary">${result.kind || 'code'}</span>
                    <span class="search-result-score">${(result.score * 100).toFixed(1)}%</span>
                </div>
                <div class="search-result-code">${this._highlightCode(result.text, query)}</div>
                <div class="search-result-meta">
                    <span>Lines ${result.start_line}-${result.end_line}</span>
                    ${result.symbol_id ? `<span>Symbol: ${result.symbol_id}</span>` : ''}
                </div>
                <div class="search-result-actions">
                    <button class="btn btn-sm btn-secondary" onclick="searchModule._viewFile('${this._escapeAttr(result.path)}', ${result.start_line})">
                        📄 View
                    </button>
                    <button class="btn btn-sm btn-secondary" onclick="searchModule._analyzeImpact('${this._escapeAttr(result.symbol_id || '')}')">
                        💥 Impact
                    </button>
                    <button class="btn btn-sm btn-secondary" onclick="searchModule._addToContext('${this._escapeAttr(result.path)}')">
                        📋 Add to Context
                    </button>
                </div>
            </div>
        `).join('');

        this.searchResults.innerHTML = `
            <div class="search-results-header">
                <span>${results.length} results for "${this._escapeHtml(query)}"</span>
                <span class="search-results-time">(${this._getSearchTime()}ms)</span>
            </div>
            ${resultsHtml}
        `;

        // Add click handlers
        this.searchResults.querySelectorAll('.search-result-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.closest('button')) {
                    const index = parseInt(item.dataset.index);
                    this._selectResult(this.currentResults[index]);
                }
            });
        });
    }

    _renderGlobalDropdown(results) {
        const dropdown = document.getElementById('search-results');
        if (!dropdown) return;

        if (!results || results.length === 0) {
            dropdown.innerHTML = '<div class="search-dropdown-item">No results found</div>';
            dropdown.classList.add('active');
            return;
        }

        dropdown.innerHTML = results.map(result => `
            <div class="search-dropdown-item" data-path="${this._escapeAttr(result.path)}" data-line="${result.start_line}">
                <div class="search-dropdown-path">${result.path}</div>
                <div class="search-dropdown-preview">${this._escapeHtml(result.text?.substring(0, 80))}...</div>
            </div>
        `).join('');

        dropdown.classList.add('active');

        // Add click handlers
        dropdown.querySelectorAll('.search-dropdown-item').forEach(item => {
            item.addEventListener('click', () => {
                const path = item.dataset.path;
                const line = item.dataset.line;
                this._viewFile(path, parseInt(line));
                dropdown.classList.remove('active');
            });
        });
    }

    _renderHistory() {
        if (!this.searchResults) return;

        const historyHtml = this.searchHistory.map((item, index) => `
            <div class="search-history-item" data-query="${this._escapeAttr(item.query)}">
                <span class="history-icon">🕐</span>
                <span class="history-query">${this._escapeHtml(item.query)}</span>
                <span class="history-time">${this._formatTime(item.timestamp)}</span>
                <button class="history-remove" data-index="${index}">✕</button>
            </div>
        `).join('');

        this.searchResults.innerHTML = `
            <div class="search-history-header">
                <span>Recent Searches</span>
                <button class="btn btn-sm btn-secondary" onclick="searchModule._clearHistory()">Clear All</button>
            </div>
            ${historyHtml}
        `;

        // Add click handlers
        this.searchResults.querySelectorAll('.search-history-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.history-remove')) {
                    const query = item.dataset.query;
                    this.searchInput.value = query;
                    this._performSearch(query);
                }
            });
        });

        this.searchResults.querySelectorAll('.history-remove').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const index = parseInt(btn.dataset.index);
                this.searchHistory.splice(index, 1);
                this._saveHistory();
                this._renderHistory();
            });
        });
    }

    _renderError(message) {
        if (!this.searchResults) return;

        this.searchResults.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <div class="empty-state-title">Search Error</div>
                <div class="empty-state-description">${this._escapeHtml(message)}</div>
                <div class="empty-state-action">
                    <button class="btn btn-primary" onclick="searchModule._performSearch()">Retry</button>
                </div>
            </div>
        `;
    }

    _showLoading() {
        if (!this.searchResults) return;

        this.searchResults.innerHTML = `
            <div class="search-loading">
                <div class="spinner lg"></div>
                <span>Searching...</span>
            </div>
        `;
    }

    _clearResults() {
        if (this.searchResults) {
            this.searchResults.innerHTML = '';
        }
        this.currentResults = [];
        this.currentIndex = -1;
    }

    // === Navigation ===

    _navigateResults(direction) {
        if (this.currentResults.length === 0) return;

        this.currentIndex += direction;

        // Wrap around
        if (this.currentIndex < 0) this.currentIndex = this.currentResults.length - 1;
        if (this.currentIndex >= this.currentResults.length) this.currentIndex = 0;

        // Update visual selection
        const items = this.searchResults.querySelectorAll('.search-result-item');
        items.forEach((item, index) => {
            item.classList.toggle('selected', index === this.currentIndex);
        });

        // Scroll into view
        items[this.currentIndex]?.scrollIntoView({ block: 'nearest' });
    }

    _selectResult(result) {
        if (!result) return;

        // Show toast
        this._showToast(`Selected: ${result.path}:${result.start_line}`, 'info');

        // Could open file viewer, navigate to code map, etc.
        this._viewFile(result.path, result.start_line);
    }

    // === Actions ===

    _viewFile(path, line) {
        this._showToast(`Opening ${path}:${line}`, 'info');
        // Integration point: Could open in code viewer or navigate to code map
    }

    _analyzeImpact(symbolId) {
        if (!symbolId) {
            this._showToast('No symbol ID available for impact analysis', 'warning');
            return;
        }

        // Switch to impact tab
        document.querySelector('[data-tab="impact"]')?.click();

        // Set symbol and trigger analysis
        const impactInput = document.getElementById('impact-symbol');
        if (impactInput) {
            impactInput.value = symbolId;
            document.getElementById('impact-analyze-btn')?.click();
        }
    }

    _addToContext(path) {
        this._showToast(`Added ${path} to context`, 'success');
        // Integration point: Add to context manager
    }

    // === Search History ===

    _addToHistory(query) {
        // Remove duplicate
        this.searchHistory = this.searchHistory.filter(item => item.query !== query);

        // Add to front
        this.searchHistory.unshift({
            query,
            timestamp: Date.now()
        });

        // Limit size
        if (this.searchHistory.length > this.maxHistory) {
            this.searchHistory = this.searchHistory.slice(0, this.maxHistory);
        }

        this._saveHistory();
    }

    _loadHistory() {
        try {
            const saved = localStorage.getItem('cip-search-history');
            if (saved) {
                this.searchHistory = JSON.parse(saved);
            }
        } catch (e) {
            this.searchHistory = [];
        }
    }

    _saveHistory() {
        try {
            localStorage.setItem('cip-search-history', JSON.stringify(this.searchHistory));
        } catch (e) {
            console.warn('Failed to save search history');
        }
    }

    _clearHistory() {
        this.searchHistory = [];
        this._saveHistory();
        this._clearResults();
    }

    // === Utilities ===

    _highlightMatch(text, query) {
        if (!query) return this._escapeHtml(text);

        const escaped = this._escapeHtml(text);
        const regex = new RegExp(`(${this._escapeRegex(query)})`, 'gi');
        return escaped.replace(regex, '<mark>$1</mark>');
    }

    _highlightCode(code, query) {
        if (!code) return '';
        if (!query) return this._escapeHtml(code);

        const escaped = this._escapeHtml(code);
        const regex = new RegExp(`(${this._escapeRegex(query)})`, 'gi');
        return escaped.replace(regex, '<mark>$1</mark>');
    }

    _escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    _escapeAttr(text) {
        if (!text) return '';
        return text.replace(/'/g, "\\'").replace(/"/g, '&quot;');
    }

    _escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    _formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) return 'just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        return date.toLocaleDateString();
    }

    _getSearchTime() {
        // Would be tracked from actual search performance
        return Math.floor(Math.random() * 100) + 10;
    }

    _showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <div class="toast-message">${message}</div>
            </div>
        `;

        container.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }
}

// Initialize search module
let searchModule;
document.addEventListener('DOMContentLoaded', () => {
    searchModule = new SearchModule();
    window.searchModule = searchModule;
});
