// WebSocket Client for DEAN Evolution Dashboard

class WebSocketClient {
    constructor() {
        this.ws = null;
        this.subscriptions = new Map();
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
        this.reconnectAttempts = 0;
        this.shouldReconnect = true;
    }

    // Connect to WebSocket endpoint
    connect(trialId) {
        const wsUrl = `ws://localhost:8082/ws/evolution/${trialId}`;
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                this.reconnectDelay = 1000;
                updateConnectionStatus(true);
                
                // Notify subscribers
                this.notifySubscribers('connected', { trialId });
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                updateConnectionStatus(false);
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                updateConnectionStatus(false);
                
                // Attempt reconnection if enabled
                if (this.shouldReconnect) {
                    this.attemptReconnect(trialId);
                }
            };
            
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            updateConnectionStatus(false);
        }
    }

    // Handle incoming messages
    handleMessage(data) {
        switch (data.type) {
            case 'status':
                this.handleStatusMessage(data);
                break;
            case 'update':
                this.handleUpdateMessage(data);
                break;
            case 'complete':
                this.handleCompleteMessage(data);
                break;
            case 'error':
                this.handleErrorMessage(data);
                break;
            default:
                console.warn('Unknown message type:', data.type);
        }
    }

    // Handle status message
    handleStatusMessage(data) {
        this.notifySubscribers('status', data.trial);
    }

    // Handle update message
    handleUpdateMessage(data) {
        // Update trial progress
        if (window.trialManager) {
            window.trialManager.updateTrialProgress(data);
        }
        
        // Update charts
        if (window.chartManager) {
            window.chartManager.updateCharts(data);
        }
        
        // Notify subscribers
        this.notifySubscribers('update', data);
    }

    // Handle completion message
    handleCompleteMessage(data) {
        this.shouldReconnect = false;
        
        // Show completion notification
        showToast(`Trial ${data.trial_id} completed!`, 'success');
        
        // Update trial status
        if (window.trialManager) {
            window.trialManager.handleTrialComplete(data.trial_id);
        }
        
        // Notify subscribers
        this.notifySubscribers('complete', data);
    }

    // Handle error message
    handleErrorMessage(data) {
        showToast(`Error: ${data.message}`, 'error');
        this.notifySubscribers('error', data);
    }

    // Attempt reconnection with exponential backoff
    attemptReconnect(trialId) {
        this.reconnectAttempts++;
        
        setTimeout(() => {
            console.log(`Attempting reconnection (attempt ${this.reconnectAttempts})...`);
            this.connect(trialId);
        }, this.reconnectDelay);
        
        // Exponential backoff
        this.reconnectDelay = Math.min(
            this.reconnectDelay * 2,
            this.maxReconnectDelay
        );
    }

    // Subscribe to WebSocket events
    subscribe(event, callback) {
        if (!this.subscriptions.has(event)) {
            this.subscriptions.set(event, []);
        }
        this.subscriptions.get(event).push(callback);
    }

    // Unsubscribe from WebSocket events
    unsubscribe(event, callback) {
        if (this.subscriptions.has(event)) {
            const callbacks = this.subscriptions.get(event);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }

    // Notify all subscribers of an event
    notifySubscribers(event, data) {
        if (this.subscriptions.has(event)) {
            this.subscriptions.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in subscriber callback for ${event}:`, error);
                }
            });
        }
    }

    // Disconnect WebSocket
    disconnect() {
        this.shouldReconnect = false;
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.close();
        }
        this.subscriptions.clear();
    }

    // Check if connected
    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
}

// Create global WebSocket client instance
const wsClient = new WebSocketClient();

// Update connection status UI
function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('connection-status');
    if (statusElement) {
        if (connected) {
            statusElement.classList.remove('disconnected');
            statusElement.classList.add('connected');
            statusElement.querySelector('.status-text').textContent = 'Connected';
        } else {
            statusElement.classList.remove('connected');
            statusElement.classList.add('disconnected');
            statusElement.querySelector('.status-text').textContent = 'Disconnected';
        }
    }
}