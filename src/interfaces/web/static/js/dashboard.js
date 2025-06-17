// DEAN Dashboard JavaScript

// Global state
let ws = null;
let reconnectTimer = null;
let lastUpdate = null;

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeWebSocket();
    initializeEventHandlers();
    loadInitialData();
});

// WebSocket Management
function initializeWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        updateConnectionStatus(true);
        clearTimeout(reconnectTimer);
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected');
        updateConnectionStatus(false);
        scheduleReconnect();
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateConnectionStatus(false);
    };
    
    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
    };
    
    // Send ping every 25 seconds to keep connection alive
    setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
        }
    }, 25000);
}

function scheduleReconnect() {
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(() => {
        console.log('Attempting to reconnect...');
        initializeWebSocket();
    }, 5000);
}

function updateConnectionStatus(connected) {
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.status-text');
    
    if (connected) {
        statusDot.classList.add('connected');
        statusDot.classList.remove('disconnected');
        statusText.textContent = 'Connected';
    } else {
        statusDot.classList.remove('connected');
        statusDot.classList.add('disconnected');
        statusText.textContent = 'Disconnected';
    }
}

// WebSocket Message Handling
function handleWebSocketMessage(message) {
    switch (message.type) {
        case 'status_update':
            updateSystemStatus(message.data);
            break;
        case 'trial_started':
            showNotification('Evolution trial started', 'info');
            loadEvolutionTrials();
            break;
        case 'trial_completed':
            showNotification('Evolution trial completed', 'success');
            loadEvolutionTrials();
            break;
        case 'trial_failed':
            showNotification('Evolution trial failed', 'error');
            loadEvolutionTrials();
            break;
        default:
            console.log('Unknown message type:', message.type);
    }
}

// Event Handlers
function initializeEventHandlers() {
    // New trial button
    document.getElementById('new-trial-btn').addEventListener('click', () => {
        showModal('new-trial-modal');
    });
    
    // New trial form
    document.getElementById('new-trial-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await startNewTrial();
    });
    
    // Refresh buttons
    document.getElementById('refresh-trials-btn').addEventListener('click', loadEvolutionTrials);
    document.getElementById('refresh-agents-btn').addEventListener('click', loadAgents);
    document.getElementById('refresh-patterns-btn').addEventListener('click', loadPatterns);
    
    // Filter changes
    document.getElementById('repository-filter').addEventListener('change', loadAgents);
    document.getElementById('pattern-type-filter').addEventListener('change', loadPatterns);
}

// Data Loading Functions
async function loadInitialData() {
    await Promise.all([
        loadSystemStatus(),
        loadEvolutionTrials(),
        loadAgents(),
        loadPatterns()
    ]);
}

async function loadSystemStatus() {
    try {
        const response = await fetch('/api/system/status');
        const data = await response.json();
        updateSystemStatus(data);
    } catch (error) {
        console.error('Failed to load system status:', error);
    }
}

async function loadEvolutionTrials() {
    try {
        const response = await fetch('/api/evolution/trials');
        const data = await response.json();
        updateEvolutionTrials(data.trials);
    } catch (error) {
        console.error('Failed to load evolution trials:', error);
    }
}

async function loadAgents() {
    try {
        const repository = document.getElementById('repository-filter').value;
        const url = repository ? `/api/agents?repository=${repository}` : '/api/agents';
        const response = await fetch(url);
        const data = await response.json();
        updateAgents(data.agents);
    } catch (error) {
        console.error('Failed to load agents:', error);
    }
}

async function loadPatterns() {
    try {
        const patternType = document.getElementById('pattern-type-filter').value;
        const url = patternType ? `/api/patterns?pattern_type=${patternType}` : '/api/patterns';
        const response = await fetch(url);
        const data = await response.json();
        updatePatterns(data.patterns);
    } catch (error) {
        console.error('Failed to load patterns:', error);
    }
}

// UI Update Functions
function updateSystemStatus(status) {
    // Update metrics
    document.getElementById('overall-health').textContent = 
        status.status === 'healthy' ? '100%' : '50%';
    document.getElementById('active-agents').textContent = 
        status.metrics.active_agents || '0';
    document.getElementById('recent-trials').textContent = 
        status.metrics.recent_trials || '0';
    
    // Update services
    const serviceList = document.getElementById('service-list');
    serviceList.innerHTML = '';
    
    if (status.services) {
        Object.entries(status.services).forEach(([name, service]) => {
            const serviceEl = document.createElement('div');
            serviceEl.className = `service-item ${service.status === 'healthy' ? 'healthy' : 'unhealthy'}`;
            serviceEl.innerHTML = `
                <span>${name}</span>
                <span>${service.status === 'healthy' ? '✓' : '✗'}</span>
            `;
            serviceList.appendChild(serviceEl);
        });
    }
    
    // Update last update time
    lastUpdate = new Date();
    updateLastUpdateTime();
}

function updateEvolutionTrials(trials) {
    const tbody = document.querySelector('#trials-table tbody');
    tbody.innerHTML = '';
    
    if (!trials || trials.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No trials found</td></tr>';
        return;
    }
    
    trials.forEach(trial => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${trial.trial_id || 'N/A'}</td>
            <td>${trial.repository || 'N/A'}</td>
            <td class="status-${trial.status}">${trial.status || 'unknown'}</td>
            <td>${trial.generations || '-'}</td>
            <td>${trial.best_score ? trial.best_score.toFixed(2) : '-'}</td>
            <td>${formatDate(trial.started_at)}</td>
        `;
        tbody.appendChild(row);
    });
}

function updateAgents(agents) {
    const agentsGrid = document.getElementById('agents-grid');
    agentsGrid.innerHTML = '';
    
    if (!agents || agents.length === 0) {
        agentsGrid.innerHTML = '<p style="text-align: center;">No active agents</p>';
        return;
    }
    
    agents.forEach(agent => {
        const agentCard = document.createElement('div');
        agentCard.className = 'agent-card';
        agentCard.innerHTML = `
            <h4>${agent.name || 'Unnamed Agent'}</h4>
            <div class="agent-info">
                <p>ID: ${agent.id || 'N/A'}</p>
                <p>Repository: ${agent.repository || 'N/A'}</p>
                <p>Score: ${agent.fitness_score ? agent.fitness_score.toFixed(2) : '-'}</p>
                <p>Generation: ${agent.generation || '-'}</p>
            </div>
        `;
        agentsGrid.appendChild(agentCard);
    });
}

function updatePatterns(patterns) {
    const patternsList = document.getElementById('patterns-list');
    patternsList.innerHTML = '';
    
    if (!patterns || patterns.length === 0) {
        patternsList.innerHTML = '<p style="text-align: center;">No patterns discovered</p>';
        return;
    }
    
    patterns.forEach(pattern => {
        const patternItem = document.createElement('div');
        patternItem.className = 'pattern-item';
        patternItem.innerHTML = `
            <h4>${pattern.name || 'Unnamed Pattern'}</h4>
            <div class="pattern-description">
                <p>Type: ${pattern.type || 'unknown'}</p>
                <p>Frequency: ${pattern.frequency || '-'}</p>
                <p>Confidence: ${pattern.confidence ? (pattern.confidence * 100).toFixed(1) + '%' : '-'}</p>
                <p>${pattern.description || 'No description available'}</p>
            </div>
        `;
        patternsList.appendChild(patternItem);
    });
}

function updateLastUpdateTime() {
    if (!lastUpdate) return;
    
    const element = document.getElementById('last-update');
    const now = new Date();
    const diff = Math.floor((now - lastUpdate) / 1000);
    
    if (diff < 60) {
        element.textContent = `Last update: ${diff}s ago`;
    } else if (diff < 3600) {
        element.textContent = `Last update: ${Math.floor(diff / 60)}m ago`;
    } else {
        element.textContent = `Last update: ${formatDate(lastUpdate)}`;
    }
}

// Update last update time every second
setInterval(updateLastUpdateTime, 1000);

// Utility Functions
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString();
}

function showModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.add('show');
}

function closeModal() {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => modal.classList.remove('show'));
}

// Close modal when clicking outside
window.addEventListener('click', (event) => {
    if (event.target.classList.contains('modal')) {
        closeModal();
    }
});

async function startNewTrial() {
    const form = document.getElementById('new-trial-form');
    const formData = new FormData(form);
    
    try {
        const response = await fetch('/api/evolution/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                repository: formData.get('repository'),
                generations: parseInt(formData.get('generations')),
                population_size: parseInt(formData.get('population_size'))
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'started') {
            showNotification('Evolution trial started successfully', 'success');
            closeModal();
            form.reset();
        } else {
            showNotification('Failed to start evolution trial', 'error');
        }
    } catch (error) {
        console.error('Failed to start trial:', error);
        showNotification('Failed to start evolution trial', 'error');
    }
}

function showNotification(message, type = 'info') {
    // Simple console notification for now
    // In production, this would show a toast notification
    console.log(`[${type.toUpperCase()}] ${message}`);
}