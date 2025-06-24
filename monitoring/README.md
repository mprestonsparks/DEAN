# DEAN Monitoring Stack

This directory contains the monitoring infrastructure for the DEAN system, including Prometheus for metrics collection, Grafana for visualization, Alertmanager for notifications, and Loki for log aggregation.

## Components

### Metrics & Monitoring
- **Prometheus**: Time-series database for metrics collection
- **Grafana**: Visualization and dashboards
- **Alertmanager**: Alert routing and notifications
- **Node Exporter**: Host-level metrics
- **cAdvisor**: Container metrics
- **PostgreSQL Exporter**: Database metrics
- **Redis Exporter**: Cache metrics

### Logging
- **Loki**: Log aggregation system
- **Promtail**: Log collection agent

## Quick Start

### Deploy Monitoring Stack

```powershell
# Deploy all monitoring services
./deploy_monitoring.ps1 -Action deploy

# Check status
./deploy_monitoring.ps1 -Action status

# View logs
./deploy_monitoring.ps1 -Action logs

# Stop monitoring
./deploy_monitoring.ps1 -Action stop
```

### Access Points

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (default: admin/admin)
- **Alertmanager**: http://localhost:9093
- **Loki**: http://localhost:3100

## Configuration Files

### Core Configuration
- `docker-compose.monitoring.yml`: Service definitions
- `prometheus.yml`: Prometheus scrape configuration
- `alerts.yml`: Alert rules
- `alertmanager.yml`: Alert routing configuration

### Logging Configuration
- `loki-config.yml`: Loki storage and retention settings
- `promtail-config.yml`: Log collection patterns

### Grafana Configuration
- `grafana/provisioning/datasources/`: Data source definitions
- `grafana/provisioning/dashboards/`: Dashboard provisioning
- `grafana/dashboards/`: JSON dashboard definitions

## Alert Rules

### Critical Alerts
- `OrchestratorDown`: DEAN Orchestrator unavailable
- `PostgreSQLDown`: Database unavailable
- `RedisDown`: Cache unavailable

### Warning Alerts
- `HighCPUUsage`: CPU > 80% for 10 minutes
- `HighMemoryUsage`: Memory > 85% for 10 minutes
- `DiskSpaceLow`: Disk space < 15%
- `HighErrorRate`: Error rate > 5%
- `SlowResponseTime`: 95th percentile > 1 second

## Grafana Dashboards

### Pre-configured Dashboards
1. **DEAN System Overview**: Overall system health and performance
2. **Service Health**: Individual service status and metrics
3. **Resource Usage**: CPU, memory, disk, and network metrics
4. **Database Performance**: PostgreSQL metrics and slow queries
5. **Application Metrics**: Request rates, error rates, and latencies

### Adding Custom Dashboards
1. Create dashboard in Grafana UI
2. Export as JSON
3. Save to `grafana/dashboards/`
4. Restart Grafana container

## Prometheus Queries

### Useful Queries
```promql
# Service availability
up{job=~"dean-orchestrator|postgres|redis"}

# Request rate
rate(dean_orchestrator_requests_total[5m])

# Error rate
rate(dean_orchestrator_errors_total[5m]) / rate(dean_orchestrator_requests_total[5m])

# Response time (95th percentile)
histogram_quantile(0.95, rate(dean_orchestrator_request_duration_seconds_bucket[5m]))

# Database connections
pg_stat_database_numbackends{datname="dean_production"}

# Redis memory usage
redis_memory_used_bytes / redis_memory_max_bytes
```

## Log Queries (Loki)

### Example Queries
```logql
# All DEAN orchestrator logs
{job="dean"}

# Error logs only
{job="dean"} |= "ERROR"

# Specific module logs
{job="dean", module="auth"}

# Rate of errors
rate({job="dean"} |= "ERROR" [5m])
```

## Alerting Configuration

### Email Configuration
Update `alertmanager.yml` with your SMTP settings:
```yaml
global:
  smtp_smarthost: 'smtp.example.com:587'
  smtp_auth_username: 'alerts@example.com'
  smtp_auth_password: 'your-password'
```

### Webhook Integration
Add webhook receivers for PagerDuty, Slack, etc.:
```yaml
receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts'
```

## Maintenance

### Retention Policies
- **Prometheus**: 30 days (configurable in docker-compose)
- **Loki**: 14 days (configurable in loki-config.yml)
- **Grafana**: Unlimited (database backed)

### Backup Recommendations
1. Prometheus data: `/prometheus` volume
2. Grafana data: `/var/lib/grafana` volume
3. Configuration files: This directory

### Resource Requirements
- **Minimum**: 2GB RAM, 10GB disk
- **Recommended**: 4GB RAM, 50GB disk
- **Production**: 8GB RAM, 100GB+ disk

## Troubleshooting

### Common Issues

1. **Prometheus targets down**
   - Check service connectivity
   - Verify network configuration
   - Check firewall rules

2. **No data in Grafana**
   - Verify Prometheus is running
   - Check data source configuration
   - Confirm metrics are being scraped

3. **Alerts not firing**
   - Check alert rules syntax
   - Verify Alertmanager configuration
   - Test webhook endpoints

4. **High memory usage**
   - Adjust retention policies
   - Increase scrape intervals
   - Add memory limits to containers

### Debug Commands
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Test Alertmanager
curl -X POST http://localhost:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{"labels":{"alertname":"test"}}]'

# Query Loki
curl "http://localhost:3100/loki/api/v1/query?query={job=\"dean\"}"
```

## Integration with DEAN

The DEAN Orchestrator exposes metrics at `/metrics` endpoint in Prometheus format. These metrics include:

- Request counts and latencies
- Error rates by endpoint
- Service health status
- Feature flag states
- Database connection pool metrics
- Cache hit/miss rates

To add custom metrics, use the monitoring client in your code:
```python
from src.integration.monitoring_client import MonitoringClient

monitoring = MonitoringClient()
monitoring.increment_counter("custom_operation_total")
monitoring.observe_histogram("custom_duration_seconds", duration)
```