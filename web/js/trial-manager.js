// Trial Manager for DEAN Evolution Dashboard

class TrialManager {
    constructor() {
        this.activeTrials = new Map();
        this.currentTrialId = null;
        this.refreshInterval = null;
        this.refreshRate = 5000; // 5 seconds
    }

    // Initialize the trial manager
    async initialize() {
        // Check authentication
        if (!apiClient.isAuthenticated()) {
            showAuthModal();
            return;
        }

        // Load active trials
        await this.loadActiveTrials();

        // Set up event listeners
        this.setupEventListeners();

        // Start auto-refresh
        this.startAutoRefresh();
    }

    // Set up event listeners
    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.getAttribute('data-page');
                showPage(page);
            });
        });

        // Auth button
        const authBtn = document.getElementById('auth-btn');
        if (authBtn) {
            authBtn.addEventListener('click', () => {
                if (apiClient.isAuthenticated()) {
                    this.logout();
                } else {
                    showAuthModal();
                }
            });
        }

        // Auth form
        const authForm = document.getElementById('auth-form');
        if (authForm) {
            authForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.authenticate();
            });
        }

        // Create trial form
        const createForm = document.getElementById('create-trial-form');
        if (createForm) {
            createForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.createTrial();
            });
        }

        // Refresh button
        const refreshBtn = document.getElementById('refresh-trials');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadActiveTrials());
        }

        // History filter
        const historyFilter = document.getElementById('history-filter');
        if (historyFilter) {
            historyFilter.addEventListener('change', () => this.loadTrialHistory());
        }
    }

    // Authenticate user
    async authenticate() {
        const tokenInput = document.getElementById('auth-token');
        const token = tokenInput.value.trim();

        if (!token) {
            showToast('Please enter a JWT token', 'error');
            return;
        }

        try {
            // Set the token
            apiClient.setAuthToken(token);

            // Test authentication by checking health
            const isHealthy = await apiClient.checkHealth();
            if (!isHealthy) {
                throw new Error('Service unavailable');
            }

            // Update UI
            document.getElementById('auth-btn').textContent = 'Logout';
            closeAuthModal();
            showToast('Authentication successful', 'success');

            // Reload trials
            await this.loadActiveTrials();
            this.startAutoRefresh();

        } catch (error) {
            apiClient.clearAuth();
            showToast('Authentication failed: ' + error.message, 'error');
        }
    }

    // Logout user
    logout() {
        apiClient.clearAuth();
        document.getElementById('auth-btn').textContent = 'Login';
        this.stopAutoRefresh();
        this.clearUI();
        showToast('Logged out successfully', 'info');
    }

    // Load active trials
    async loadActiveTrials() {
        if (!apiClient.isAuthenticated()) {
            return;
        }

        try {
            const response = await apiClient.listEvolutionTrials('running');
            this.displayActiveTrials(response.trials || []);
        } catch (error) {
            showToast('Failed to load trials: ' + error.message, 'error');
        }
    }

    // Display active trials
    displayActiveTrials(trials) {
        const container = document.getElementById('active-trials');
        const noTrials = document.getElementById('no-trials');

        if (trials.length === 0) {
            container.innerHTML = '';
            noTrials.style.display = 'block';
            return;
        }

        noTrials.style.display = 'none';
        container.innerHTML = trials.map(trial => this.createTrialCard(trial)).join('');

        // Add click handlers
        container.querySelectorAll('.trial-card').forEach(card => {
            card.addEventListener('click', () => {
                const trialId = card.getAttribute('data-trial-id');
                this.showTrialDetails(trialId);
            });
        });
    }

    // Create trial card HTML
    createTrialCard(trial) {
        const progress = (trial.current_generation / trial.generations) * 100;
        
        return `
            <div class="trial-card" data-trial-id="${trial.trial_id}">
                <div class="trial-header">
                    <div>
                        <h3 class="trial-title">${trial.name || 'Evolution Trial'}</h3>
                        <p class="trial-id">${trial.trial_id.substring(0, 8)}...</p>
                    </div>
                    <span class="trial-status ${trial.status}">${trial.status}</span>
                </div>
                
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress}%"></div>
                </div>
                <p class="progress-text">${trial.current_generation} / ${trial.generations} generations</p>
                
                <div class="trial-metrics">
                    <div class="metric">
                        <p class="metric-label">Population</p>
                        <p class="metric-value">${trial.population_size}</p>
                    </div>
                    <div class="metric">
                        <p class="metric-label">Best Fitness</p>
                        <p class="metric-value">${(trial.best_fitness || 0).toFixed(2)}</p>
                    </div>
                    <div class="metric">
                        <p class="metric-label">Tokens Used</p>
                        <p class="metric-value">${(trial.tokens_used || 0).toLocaleString()}</p>
                    </div>
                    <div class="metric">
                        <p class="metric-label">Patterns</p>
                        <p class="metric-value">${trial.patterns_discovered || 0}</p>
                    </div>
                </div>
            </div>
        `;
    }

    // Create new trial
    async createTrial() {
        const params = {
            population_size: parseInt(document.getElementById('population-size').value),
            generations: parseInt(document.getElementById('generations').value),
            token_budget: parseInt(document.getElementById('token-budget').value),
            diversity_threshold: parseFloat(document.getElementById('diversity-threshold').value)
        };

        try {
            const response = await apiClient.startEvolutionTrial(params);
            showToast('Evolution trial started successfully', 'success');
            
            // Switch to overview page and refresh
            showPage('overview');
            await this.loadActiveTrials();
            
            // Show trial details
            this.showTrialDetails(response.trial_id);
            
        } catch (error) {
            showToast('Failed to start trial: ' + error.message, 'error');
        }
    }

    // Show trial details
    async showTrialDetails(trialId) {
        try {
            const trial = await apiClient.getEvolutionTrialStatus(trialId);
            this.currentTrialId = trialId;
            
            // Update modal content
            this.updateTrialModal(trial);
            
            // Show modal
            const modal = document.getElementById('trial-detail-modal');
            modal.classList.add('active');
            
            // Initialize charts
            chartManager.initializeTrialCharts();
            
            // Load historical data
            if (trial.generation_metrics) {
                chartManager.loadHistoricalData(trial.generation_metrics);
            }
            
            // Connect WebSocket
            wsClient.connect(trialId);
            
        } catch (error) {
            showToast('Failed to load trial details: ' + error.message, 'error');
        }
    }

    // Update trial modal with data
    updateTrialModal(trial) {
        // Update title
        document.getElementById('trial-detail-title').textContent = 
            trial.name || `Trial ${trial.trial_id.substring(0, 8)}...`;
        
        // Update progress
        const progress = (trial.progress.current_generation / trial.progress.total_generations) * 100;
        document.getElementById('trial-progress-bar').style.width = `${progress}%`;
        document.getElementById('trial-progress-text').textContent = 
            `${trial.progress.current_generation} / ${trial.progress.total_generations} generations`;
        
        // Update metrics
        document.getElementById('trial-best-fitness').textContent = 
            (trial.performance.best_fitness || 0).toFixed(2);
        document.getElementById('trial-diversity').textContent = 
            (trial.performance.diversity_index || 0).toFixed(2);
        document.getElementById('trial-token-usage').textContent = 
            (trial.resource_usage.tokens_used || 0).toLocaleString();
        document.getElementById('trial-token-budget').textContent = 
            `of ${(trial.resource_usage.tokens_budget || 0).toLocaleString()}`;
        
        // Update button state
        const cancelBtn = document.getElementById('cancel-trial-btn');
        cancelBtn.disabled = trial.status !== 'running';
    }

    // Update trial progress from WebSocket
    updateTrialProgress(data) {
        if (data.trial_id !== this.currentTrialId) {
            return;
        }

        // Update active trials list
        const trialCard = document.querySelector(`[data-trial-id="${data.trial_id}"]`);
        if (trialCard) {
            const progress = (data.current_generation / 50) * 100; // Assuming 50 generations
            trialCard.querySelector('.progress-fill').style.width = `${progress}%`;
            trialCard.querySelector('.progress-text').textContent = 
                `${data.current_generation} / 50 generations`;
        }

        // Update modal if open
        if (document.getElementById('trial-detail-modal').classList.contains('active')) {
            document.getElementById('trial-progress-bar').style.width = 
                `${(data.current_generation / 50) * 100}%`;
            document.getElementById('trial-progress-text').textContent = 
                `${data.current_generation} / 50 generations`;
            document.getElementById('trial-best-fitness').textContent = 
                (data.best_fitness_score || 0).toFixed(2);
            document.getElementById('trial-token-usage').textContent = 
                (data.total_tokens_used || 0).toLocaleString();
        }
    }

    // Handle trial completion
    async handleTrialComplete(trialId) {
        if (trialId === this.currentTrialId) {
            // Refresh trial details
            await this.showTrialDetails(trialId);
        }
        
        // Reload active trials
        await this.loadActiveTrials();
    }

    // Cancel trial
    async cancelTrial() {
        if (!this.currentTrialId) return;

        if (!confirm('Are you sure you want to cancel this trial?')) {
            return;
        }

        try {
            await apiClient.cancelEvolutionTrial(this.currentTrialId);
            showToast('Trial cancelled successfully', 'info');
            closeTrialDetail();
            await this.loadActiveTrials();
        } catch (error) {
            showToast('Failed to cancel trial: ' + error.message, 'error');
        }
    }

    // Load trial history
    async loadTrialHistory() {
        const filter = document.getElementById('history-filter').value;
        
        try {
            const response = await apiClient.listEvolutionTrials(filter || null);
            this.displayTrialHistory(response.trials || []);
        } catch (error) {
            showToast('Failed to load trial history: ' + error.message, 'error');
        }
    }

    // Display trial history
    displayTrialHistory(trials) {
        const tbody = document.getElementById('history-tbody');
        
        if (trials.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No trials found</td></tr>';
            return;
        }

        tbody.innerHTML = trials.map(trial => `
            <tr>
                <td style="font-family: monospace;">${trial.trial_id.substring(0, 8)}...</td>
                <td>${new Date(trial.started_at).toLocaleString()}</td>
                <td>${this.formatDuration(trial.started_at, trial.completed_at)}</td>
                <td>${trial.population_size}</td>
                <td>${trial.current_generation}/${trial.generations}</td>
                <td>${(trial.best_fitness || 0).toFixed(2)}</td>
                <td><span class="trial-status ${trial.status}">${trial.status}</span></td>
                <td>
                    <button class="btn btn-secondary" onclick="trialManager.showTrialDetails('${trial.trial_id}')">
                        View
                    </button>
                </td>
            </tr>
        `).join('');
    }

    // Load and display patterns
    async loadPatterns() {
        try {
            const response = await apiClient.getPatterns();
            this.displayPatterns(response.patterns || []);
        } catch (error) {
            showToast('Failed to load patterns: ' + error.message, 'error');
        }
    }

    // Display patterns
    displayPatterns(patterns) {
        const container = document.getElementById('patterns-container');
        
        if (patterns.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>No patterns discovered yet</p></div>';
            return;
        }

        container.innerHTML = patterns.map(pattern => `
            <div class="pattern-card">
                <span class="pattern-type">${pattern.type}</span>
                <p class="pattern-effectiveness">${(pattern.effectiveness * 100).toFixed(0)}%</p>
                <p>${pattern.description}</p>
                <small>Discovered ${new Date(pattern.discovered_at).toLocaleDateString()}</small>
            </div>
        `).join('');
    }

    // Format duration
    formatDuration(start, end) {
        if (!end) return 'In progress';
        
        const duration = new Date(end) - new Date(start);
        const hours = Math.floor(duration / 3600000);
        const minutes = Math.floor((duration % 3600000) / 60000);
        
        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        }
        return `${minutes}m`;
    }

    // Start auto-refresh
    startAutoRefresh() {
        this.stopAutoRefresh();
        this.refreshInterval = setInterval(() => {
            this.loadActiveTrials();
        }, this.refreshRate);
    }

    // Stop auto-refresh
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    // Clear UI
    clearUI() {
        document.getElementById('active-trials').innerHTML = '';
        document.getElementById('no-trials').style.display = 'block';
        document.getElementById('history-tbody').innerHTML = '';
        document.getElementById('patterns-container').innerHTML = '';
    }
}

// Create global trial manager instance
const trialManager = new TrialManager();

// Helper functions
function showPage(pageId) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    
    // Show selected page
    const page = document.getElementById(`${pageId}-page`);
    if (page) {
        page.classList.add('active');
    }
    
    // Update nav
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('data-page') === pageId) {
            link.classList.add('active');
        }
    });
    
    // Load page-specific data
    switch (pageId) {
        case 'overview':
            trialManager.loadActiveTrials();
            break;
        case 'history':
            trialManager.loadTrialHistory();
            break;
        case 'patterns':
            trialManager.loadPatterns();
            break;
    }
}

function showAuthModal() {
    document.getElementById('auth-modal').classList.add('active');
}

function closeAuthModal() {
    document.getElementById('auth-modal').classList.remove('active');
    document.getElementById('auth-token').value = '';
}

function closeTrialDetail() {
    document.getElementById('trial-detail-modal').classList.remove('active');
    wsClient.disconnect();
    chartManager.destroyCharts();
    trialManager.currentTrialId = null;
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${getToastIcon(type)}</span>
        <span class="toast-message">${message}</span>
    `;
    
    container.appendChild(toast);
    
    // Remove after 5 seconds
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

function getToastIcon(type) {
    switch (type) {
        case 'success': return '✓';
        case 'error': return '✗';
        case 'warning': return '⚠';
        case 'info': return 'ℹ';
        default: return '';
    }
}

// Initialize app
function initializeApp() {
    // Set up trial manager
    window.trialManager = trialManager;
    window.chartManager = chartManager;
    window.wsClient = wsClient;
    
    // Initialize
    trialManager.initialize();
}

// Export functions for inline handlers
window.showPage = showPage;
window.showAuthModal = showAuthModal;
window.closeAuthModal = closeAuthModal;
window.closeTrialDetail = closeTrialDetail;
window.cancelTrial = () => trialManager.cancelTrial();
window.showToast = showToast;