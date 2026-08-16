/**
 * WebSocket client for real-time updates
 */

class WebSocketClient {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.subscriptions = new Set();
        this.messageHandlers = new Map();
        this.isConnected = false;
    }

    connect() {
        try {
            this.ws = new WebSocket(this.url);

            this.ws.onopen = () => {
                console.log('🔌 WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;

                // Update store
                store.setState({
                    connected: true,
                    connectionStatus: 'connected'
                });

                // Re-subscribe to topics
                this.subscriptions.forEach(topic => {
                    this._sendSubscribe(topic);
                });

                // Emit connected event
                this._emit('connected');
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this._handleMessage(message);
                } catch (e) {
                    console.error('WebSocket message parse error:', e);
                }
            };

            this.ws.onclose = () => {
                console.log('🔌 WebSocket disconnected');
                this.isConnected = false;

                store.setState({
                    connected: false,
                    connectionStatus: 'disconnected'
                });

                this._emit('disconnected');
                this._attemptReconnect();
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this._emit('error', error);
            };

        } catch (e) {
            console.error('WebSocket connection failed:', e);
            this._attemptReconnect();
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    subscribe(topic, handler) {
        this.subscriptions.add(topic);

        if (!this.messageHandlers.has(topic)) {
            this.messageHandlers.set(topic, []);
        }
        this.messageHandlers.get(topic).push(handler);

        // Subscribe on server if connected
        if (this.isConnected) {
            this._sendSubscribe(topic);
        }

        // Return unsubscribe function
        return () => {
            const handlers = this.messageHandlers.get(topic);
            if (handlers) {
                const index = handlers.indexOf(handler);
                if (index > -1) {
                    handlers.splice(index, 1);
                }
            }
        };
    }

    send(message) {
        if (this.ws && this.isConnected) {
            this.ws.send(JSON.stringify(message));
        }
    }

    _sendSubscribe(topic) {
        this.send({
            type: 'subscribe',
            topic: topic
        });
    }

    _handleMessage(message) {
        const { type, topic } = message;

        if (type === 'event' && topic) {
            this._emit(topic, message);
        } else if (type === 'connected') {
            this._emit('connected', message);
        } else if (type === 'pong') {
            this._emit('pong', message);
        }
    }

    _emit(event, data = null) {
        const handlers = this.messageHandlers.get(event) || [];
        handlers.forEach(handler => {
            try {
                handler(data);
            } catch (e) {
                console.error(`WebSocket handler error for ${event}:`, e);
            }
        });
    }

    _attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

            store.setState({
                connectionStatus: `reconnecting (${this.reconnectAttempts}/${this.maxReconnectAttempts})`
            });

            console.log(`🔄 Reconnecting in ${delay}ms...`);
            setTimeout(() => this.connect(), delay);
        } else {
            store.setState({
                connectionStatus: 'failed'
            });
            console.error('❌ Max reconnection attempts reached');
        }
    }

    // Ping server to keep connection alive
    startHeartbeat(interval = 30000) {
        setInterval(() => {
            if (this.isConnected) {
                this.send({ type: 'ping' });
            }
        }, interval);
    }
}

// Create global WebSocket client
const wsUrl = `ws://${window.location.hostname}:${parseInt(window.location.port) + 1}`;
const wsClient = new WebSocketClient(wsUrl);

// Export
window.wsClient = wsClient;