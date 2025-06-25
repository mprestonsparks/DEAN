// API Client for DEAN Evolution Dashboard

class APIClient {
    constructor() {
        this.baseURL = 'http://localhost:8082/api/v1';
        this.authToken = localStorage.getItem('dean_auth_token');
    }

    // Set authentication token
    setAuthToken(token) {
        this.authToken = token;
        localStorage.setItem('dean_auth_token', token);
    }

    // Clear authentication
    clearAuth() {
        this.authToken = null;
        localStorage.removeItem('dean_auth_token');
    }

    // Check if authenticated
    isAuthenticated() {
        return !!this.authToken;
    }

    // Make authenticated request
    async request(method, endpoint, data = null) {
        const headers = {
            'Content-Type': 'application/json'
        };

        if (this.authToken) {
            headers['Authorization'] = `Bearer ${this.authToken}`;
        }

        const options = {
            method,
            headers
        };

        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, options);
            
            if (response.status === 401) {
                // Unauthorized - clear auth and redirect to login
                this.clearAuth();
                showToast('Authentication expired. Please login again.', 'error');
                showAuthModal();
                throw new Error('Unauthorized');
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    // Evolution Trial endpoints
    async startEvolutionTrial(params) {
        return this.request('POST', '/orchestration/evolution/start', params);
    }

    async getEvolutionTrialStatus(trialId) {
        return this.request('GET', `/orchestration/evolution/${trialId}/status`);
    }

    async listEvolutionTrials(status = null) {
        const query = status ? `?status=${status}` : '';
        return this.request('GET', `/orchestration/evolution/list${query}`);
    }

    async cancelEvolutionTrial(trialId) {
        return this.request('POST', `/orchestration/evolution/${trialId}/cancel`);
    }

    // Service health check
    async checkHealth() {
        try {
            const response = await fetch(`${this.baseURL.replace('/api/v1', '')}/health`);
            return response.ok;
        } catch (error) {
            return false;
        }
    }

    // Get patterns (mock for now, replace with actual endpoint)
    async getPatterns() {
        // TODO: Replace with actual patterns endpoint when available
        return {
            patterns: [
                {
                    id: '1',
                    type: 'optimization',
                    effectiveness: 0.85,
                    discovered_at: new Date().toISOString(),
                    description: 'Efficient token usage pattern'
                },
                {
                    id: '2',
                    type: 'refactoring',
                    effectiveness: 0.72,
                    discovered_at: new Date().toISOString(),
                    description: 'Code structure improvement'
                }
            ]
        };
    }
}

// Create global API client instance
const apiClient = new APIClient();