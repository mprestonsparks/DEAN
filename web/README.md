# DEAN Web Dashboard

This directory contains the web dashboard for the DEAN Evolution System.

## Quick Start

### Option 1: Access via Main Server
Visit http://localhost:8082/dashboard when the orchestration server is running.

### Option 2: Run Standalone Web Server
```bash
# From DEAN directory
python -m src.interfaces.web_server
```
Then visit http://localhost:8083/

## Directory Structure

```
web/
├── index.html           # Main dashboard page
├── css/
│   └── dashboard.css    # Styling and theme
└── js/
    ├── api-client.js       # REST API integration
    ├── websocket-client.js # Real-time updates
    ├── charts.js           # Chart.js visualization
    └── trial-manager.js    # Main dashboard logic
```

## Authentication

You'll need a JWT token to access the dashboard. Get one via:

```bash
# Using DEAN CLI
dean-cli auth create-token --user admin --expiry 24h

# Or via API
curl -X POST http://localhost:8082/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'
```

## Features

- **Real-time Monitoring**: WebSocket updates for active trials
- **Interactive Charts**: Fitness, diversity, token usage, and pattern discoveries
- **Trial Management**: Create, monitor, and cancel evolution trials
- **History Tracking**: Review completed trials and their results
- **Pattern Discovery**: Explore optimization patterns found during evolution

## Browser Requirements

- Modern browser with JavaScript enabled
- WebSocket support
- localStorage support

Tested on Chrome 90+, Firefox 88+, Safari 14+, Edge 90+

## Documentation

See the full guide at: [docs/web_dashboard_guide.md](../docs/web_dashboard_guide.md)