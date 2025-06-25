# DEAN Web Dashboard Guide

## Overview

The DEAN Web Dashboard provides a real-time interface for monitoring and managing evolution trials. It features live WebSocket updates, interactive metric visualization, and comprehensive trial management capabilities.

## Architecture

The web dashboard consists of:

- **Static Web Interface**: HTML/CSS/JavaScript served on port 8083
- **REST API Integration**: Communicates with DEAN orchestration server on port 8082
- **WebSocket Monitoring**: Real-time updates for active trials
- **Chart.js Visualization**: Interactive charts for evolution metrics

## Getting Started

### Prerequisites

1. DEAN orchestration server running on port 8082
2. Valid JWT authentication token
3. Modern web browser with JavaScript enabled

### Starting the Dashboard

#### Option 1: Integrated with Main Server

The dashboard is available at `http://localhost:8082/dashboard` when running the main orchestration server.

#### Option 2: Standalone Web Server

Run the dedicated web server on port 8083:

```bash
# From DEAN directory
python -m src.interfaces.web_server
```

Access the dashboard at `http://localhost:8083/`

### Docker Deployment

```yaml
# Add to docker-compose.yml
dean-web:
  build:
    context: ../DEAN
    dockerfile: Dockerfile
  container_name: dean-web-dashboard
  ports:
    - "8083:8083"
  command: python -m src.interfaces.web_server
  depends_on:
    - dean-server
  networks:
    - agent-network
```

## Features

### 1. Overview Page

The main dashboard displays:
- Active evolution trials with real-time progress
- Key metrics: population size, fitness, diversity, token usage
- Quick access to trial details

### 2. Create Trial

Start new evolution trials with:
- **Population Size**: Number of agents (1-100)
- **Generations**: Evolution iterations (1-1000)
- **Token Budget**: Total tokens available
- **Diversity Threshold**: Minimum genetic diversity (0.1-1.0)

### 3. Trial Details

Detailed view includes:
- Real-time progress tracking
- Four interactive charts:
  - **Fitness Over Time**: Average, max, and min fitness trends
  - **Diversity Trend**: Population diversity with threshold line
  - **Token Consumption**: Per-generation token usage
  - **Pattern Discoveries**: Novel patterns found over time
- Trial control (cancel running trials)

### 4. History

Browse completed trials with:
- Filterable list (all/completed/failed/cancelled)
- Summary statistics
- Quick access to detailed results

### 5. Patterns

View discovered optimization patterns:
- Pattern type and effectiveness
- Discovery timestamp
- Pattern description

## Authentication

### Getting a JWT Token

1. Click the "Login" button in the header
2. Paste your JWT token in the modal
3. Click "Authenticate"

The token is stored in localStorage for persistent sessions.

### Token Generation

Generate tokens using the DEAN CLI:

```bash
dean-cli auth create-token --user admin --expiry 24h
```

Or via API:

```bash
curl -X POST http://localhost:8082/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'
```

## Real-time Monitoring

### WebSocket Connection

The dashboard automatically establishes WebSocket connections for active trials:

```javascript
// Connection URL format
ws://localhost:8082/ws/evolution/{trial_id}
```

### Update Types

1. **Status Message**: Initial trial state
2. **Update Message**: Generation progress and metrics
3. **Complete Message**: Trial completion notification

### Connection Management

- Automatic reconnection with exponential backoff
- Visual connection status indicator
- Graceful degradation if WebSocket unavailable

## Chart Interactions

### Fitness Chart
- Shows average, maximum, and minimum fitness per generation
- Helps identify convergence and improvement trends

### Diversity Chart
- Displays population diversity index
- Red dashed line indicates minimum threshold (0.3)
- Alerts when diversity drops below threshold

### Token Chart
- Bar chart of tokens consumed per generation
- Helps identify efficiency improvements

### Pattern Chart
- Scatter plot of pattern discoveries
- Size indicates pattern count per generation

## API Integration

### Configuration

The API client is configured in `js/api-client.js`:

```javascript
class APIClient {
    constructor() {
        this.baseURL = 'http://localhost:8082/api/v1';
        this.authToken = localStorage.getItem('dean_auth_token');
    }
}
```

### Endpoints Used

- `POST /orchestration/evolution/start` - Start new trial
- `GET /orchestration/evolution/{trial_id}/status` - Get trial details
- `GET /orchestration/evolution/list` - List trials
- `POST /orchestration/evolution/{trial_id}/cancel` - Cancel trial

## Customization

### Theme Customization

Edit CSS variables in `css/dashboard.css`:

```css
:root {
    --bg-primary: #0a0e27;     /* Main background */
    --bg-secondary: #151932;    /* Card background */
    --accent-primary: #64ffda;  /* Primary accent */
    --accent-secondary: #57cbff; /* Secondary accent */
}
```

### Chart Configuration

Modify chart settings in `js/charts.js`:

```javascript
chartConfigs: {
    fitness: {
        type: 'line',
        options: {
            // Chart.js options
        }
    }
}
```

## Troubleshooting

### Connection Issues

1. **"Disconnected" Status**
   - Verify DEAN server is running on port 8082
   - Check browser console for errors
   - Ensure CORS is enabled on server

2. **Authentication Failures**
   - Verify token is valid and not expired
   - Check token format (should be JWT)
   - Ensure user has proper permissions

3. **Charts Not Updating**
   - Check WebSocket connection status
   - Verify trial is actively running
   - Check browser console for JavaScript errors

### Performance

For large trials (100+ agents, 1000+ generations):
- Charts display last 50 data points
- Consider increasing update intervals
- Monitor browser memory usage

## Security Considerations

1. **Token Storage**: Tokens are stored in localStorage
   - Clear on logout: `localStorage.removeItem('dean_auth_token')`
   - Tokens expire based on server configuration

2. **CORS Configuration**: Production deployments should restrict origins

3. **HTTPS**: Use HTTPS in production for secure token transmission

## Browser Compatibility

Tested on:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

Requirements:
- JavaScript enabled
- WebSocket support
- localStorage support

## Development

### Local Development

```bash
# Start services
python -m src.orchestration.orchestration_server  # Port 8082
python -m src.interfaces.web_server              # Port 8083

# Open dashboard
open http://localhost:8083
```

### Adding New Features

1. **New API Endpoint**: Update `api-client.js`
2. **New Chart Type**: Extend `charts.js`
3. **New Page**: Add to `index.html` and `trial-manager.js`

### Debugging

Enable debug logging:

```javascript
// In browser console
localStorage.setItem('dean_debug', 'true');
```

View WebSocket messages:

```javascript
// In browser console
wsClient.subscribe('update', (data) => console.log(data));
```

## Best Practices

1. **Regular Monitoring**: Keep dashboard open during long trials
2. **Resource Planning**: Set appropriate token budgets
3. **Diversity Monitoring**: Watch for convergence warnings
4. **Pattern Analysis**: Review discovered patterns regularly
5. **Trial Cleanup**: Cancel stuck or unnecessary trials

## Future Enhancements

Planned features:
- Export trial results to CSV/JSON
- Comparative analysis between trials
- Advanced filtering and search
- Mobile-responsive design improvements
- Dark/light theme toggle
- Collaborative features (comments, sharing)