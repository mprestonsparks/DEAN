# DEAN Web Dashboard

The DEAN Web Dashboard provides a real-time monitoring and control interface for the Distributed Evolutionary Agent Network.

## Features

- **Real-time Updates**: WebSocket connection for live system status
- **System Monitoring**: View overall health, active agents, and service status
- **Evolution Management**: Start and monitor evolution trials
- **Agent Tracking**: View active agents across repositories
- **Pattern Discovery**: Browse discovered patterns and optimizations
- **Responsive Design**: Works on desktop and mobile devices

## Architecture

```
web/
├── app.py              # FastAPI application
├── static/             
│   ├── index.html      # Main dashboard page
│   ├── css/            
│   │   └── dashboard.css   # Styling
│   └── js/             
│       └── dashboard.js    # Client-side logic
└── README.md           # This file
```

## API Endpoints

### REST API

- `GET /` - Serve dashboard HTML
- `GET /api/system/status` - Get system status
- `GET /api/evolution/trials` - List evolution trials
- `GET /api/agents` - List active agents
- `GET /api/patterns` - List discovered patterns
- `POST /api/evolution/start` - Start new evolution trial

### WebSocket

- `WS /ws` - Real-time updates and notifications

## Running the Dashboard

### Standalone Mode

```bash
cd src/interfaces/web
python app.py
```

### Via DEAN Server

```bash
dean-server
# Dashboard available at http://localhost:8082
```

### Development Mode

```bash
# With auto-reload
DEAN_SERVER_RELOAD=true dean-server
```

## Configuration

The dashboard reads configuration from environment variables:

- `DEAN_SERVER_HOST` - Host to bind to (default: 0.0.0.0)
- `DEAN_SERVER_PORT` - Port to bind to (default: 8082)
- `DEAN_LOG_LEVEL` - Logging level (default: info)

## Security Considerations

**Note**: The current implementation has minimal security features and is intended for development/internal use.

For production deployment, implement:

1. **Authentication**: Add user authentication
2. **Authorization**: Role-based access control
3. **HTTPS**: Use TLS certificates
4. **CORS**: Configure appropriate CORS policies
5. **Rate Limiting**: Prevent abuse
6. **Input Validation**: Sanitize all user inputs

## Extending the Dashboard

### Adding New Metrics

1. Update the API endpoint in `app.py`
2. Add UI elements in `index.html`
3. Update the JavaScript in `dashboard.js`
4. Style with `dashboard.css`

### Adding New Pages

1. Create new HTML files in `static/`
2. Add routes in `app.py`
3. Update navigation in `index.html`

### Custom Visualizations

The dashboard uses vanilla JavaScript for simplicity. For advanced visualizations, consider integrating:

- Chart.js for graphs
- D3.js for complex visualizations
- React/Vue for more complex UI requirements

## WebSocket Protocol

Messages are JSON objects with a `type` field:

### Client to Server
```json
{
  "type": "ping"
}
```

### Server to Client
```json
{
  "type": "status_update",
  "data": { ... }
}
```

Message types:
- `status_update` - System status update
- `trial_started` - Evolution trial started
- `trial_completed` - Evolution trial completed
- `trial_failed` - Evolution trial failed

## Troubleshooting

### WebSocket Connection Issues

1. Check firewall settings
2. Verify WebSocket support in reverse proxy
3. Check browser console for errors

### Performance Issues

1. Reduce update frequency
2. Implement pagination for large datasets
3. Use server-side filtering

### Browser Compatibility

The dashboard uses modern JavaScript features. Supported browsers:
- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## Future Enhancements

- [ ] User authentication and sessions
- [ ] Customizable dashboards
- [ ] Export functionality for data
- [ ] Advanced filtering and search
- [ ] Real-time performance graphs
- [ ] Mobile app support
- [ ] Notification system
- [ ] Dark mode theme