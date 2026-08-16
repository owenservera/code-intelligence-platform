/**
 * CIP Dashboard State Management
 * Redux-like store with undo/redo support
 */

class Store {
    constructor(initialState = {}) {
        this.state = initialState;
        this.listeners = [];
        this.history = [];
        this.historyIndex = -1;
        this.maxHistory = 50;
    }

    getState() {
        return { ...this.state };
    }

    setState(updates, addToHistory = true) {
        const prevState = { ...this.state };
        this.state = { ...this.state, ...updates };

        // Add to history for undo/redo
        if (addToHistory) {
            // Remove any future history if we're not at the end
            if (this.historyIndex < this.history.length - 1) {
                this.history = this.history.slice(0, this.historyIndex + 1);
            }

            this.history.push({
                prev: prevState,
                next: { ...this.state },
                timestamp: Date.now()
            });

            // Limit history size
            if (this.history.length > this.maxHistory) {
                this.history.shift();
            } else {
                this.historyIndex++;
            }
        }

        // Notify listeners
        this._notifyListeners(updates);
    }

    subscribe(listener) {
        this.listeners.push(listener);
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    }

    undo() {
        if (this.historyIndex > 0) {
            this.historyIndex--;
            this.state = { ...this.history[this.historyIndex].prev };
            this._notifyListeners(this.state);
            return true;
        }
        return false;
    }

    redo() {
        if (this.historyIndex < this.history.length - 1) {
            this.historyIndex++;
            this.state = { ...this.history[this.historyIndex].next };
            this._notifyListeners(this.state);
            return true;
        }
        return false;
    }

    canUndo() {
        return this.historyIndex > 0;
    }

    canRedo() {
        return this.historyIndex < this.history.length - 1;
    }

    _notifyListeners(updates) {
        this.listeners.forEach(listener => {
            try {
                listener(this.state, updates);
            } catch (e) {
                console.error('Store listener error:', e);
            }
        });
    }

    // Persist state to localStorage
    persist(key = 'cip-dashboard-state') {
        try {
            localStorage.setItem(key, JSON.stringify(this.state));
        } catch (e) {
            console.warn('Failed to persist state:', e);
        }
    }

    // Restore state from localStorage
    restore(key = 'cip-dashboard-state') {
        try {
            const saved = localStorage.getItem(key);
            if (saved) {
                this.state = JSON.parse(saved);
                this._notifyListeners(this.state);
            }
        } catch (e) {
            console.warn('Failed to restore state:', e);
        }
    }
}

// Create global store instance
const store = new Store({
    // Connection state
    connected: false,
    connectionStatus: 'connecting',

    // Repository state
    repository: {
        root: '',
        name: '',
        health: null,
        stats: null,
        lastSync: null
    },

    // UI state
    activeTab: 'overview',
    theme: 'dark',
    searchQuery: '',
    searchResults: [],
    searchLoading: false,

    // Code map state
    codeMap: {
        nodes: [],
        edges: [],
        layout: 'force',
        filter: 'all',
        zoom: 1,
        panX: 0,
        panY: 0,
        selectedNode: null,
        hoveredNode: null
    },

    // Impact analysis state
    impact: {
        symbolId: '',
        result: null,
        loading: false
    },

    // Gaps state
    gaps: {
        items: [],
        filter: { type: 'all', severity: 'all' },
        loading: false
    },

    // Memory state
    memory: {
        facts: [],
        episodes: [],
        loading: false
    },

    // Activity log
    activity: [],

    // Notifications
    toasts: []
});

// Auto-persist state changes
store.subscribe(() => {
    store.persist();
});

// Export for use in other modules
window.store = store;