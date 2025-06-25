# DEAN System Centralized Logging Configuration

## Overview

The DEAN system implements centralized logging using the EFK (Elasticsearch, Fluentd, Kibana) stack to aggregate, store, and visualize logs from all services.

## Architecture

```
Services → JSON Logs → Fluentd → Elasticsearch → Kibana
                           ↓
                    Backup Files (compressed)
```

## Components

### 1. Log Generation (Services)

All DEAN services are configured to output structured JSON logs:

- **DEAN Orchestrator**: Logs to `/app/logs/dean-orchestrator.log`
- **IndexAgent**: Logs to `/app/logs/indexagent.log`
- **Evolution API**: Logs to `/app/logs/evolution-api.log`
- **Airflow**: Logs to `/opt/airflow/logs/`

### 2. Log Collection (Fluentd)

Fluentd collects logs from all services and:
- Parses JSON structure
- Adds common fields (hostname, environment, timestamp)
- Routes logs to appropriate indices in Elasticsearch
- Creates compressed backups

### 3. Log Storage (Elasticsearch)

Elasticsearch stores logs in daily indices:
- `dean-orchestrator-YYYY.MM.DD`
- `dean-indexagent-YYYY.MM.DD`
- `dean-evolution-YYYY.MM.DD`
- `dean-airflow-YYYY.MM.DD`

### 4. Log Visualization (Kibana)

Kibana provides web interface for:
- Log search and filtering
- Real-time log streaming
- Dashboard creation
- Alert configuration

## Usage

### Starting the Logging Stack

```bash
# Start all services with logging
docker-compose -f docker-compose.dean-complete.yml \
                -f docker-compose.dean-logging.yml up -d

# Verify logging services are healthy
docker-compose -f docker-compose.dean-logging.yml ps
```

### Accessing Kibana

1. Open http://localhost:5601 in your browser
2. Wait for Kibana to initialize (may take 1-2 minutes)
3. Go to Stack Management → Index Patterns
4. Create index pattern: `dean-*`
5. Select `@timestamp` as time field

### Common Queries

#### View all error logs:
```
level: "ERROR" OR level: "CRITICAL"
```

#### View logs from specific service:
```
@log_name: "dean.orchestrator"
```

#### Search for pattern discoveries:
```
message: "pattern" AND type: "discovered"
```

#### Monitor token usage:
```
message: "token" AND (allocated OR consumed)
```

#### Track evolution cycles:
```
@log_name: "dean.airflow" AND dag_id: "dean_agent_evolution"
```

## Log Format

### Standard JSON Log Entry

```json
{
  "@timestamp": "2024-01-25T10:30:45.123Z",
  "level": "INFO",
  "service": "dean-orchestrator",
  "component": "agent_manager",
  "message": "Agent spawned successfully",
  "context": {
    "agent_id": "agent_001",
    "genome_template": "default",
    "token_budget": 1000
  },
  "correlation_id": "req_12345",
  "hostname": "dean-orchestrator-abc123",
  "environment": "production"
}
```

### Log Levels

- **DEBUG**: Detailed debugging information
- **INFO**: General informational messages
- **WARNING**: Warning messages for unusual conditions
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical failures requiring immediate attention

## Configuration

### Service-Level Configuration

Each service accepts logging environment variables:

```yaml
environment:
  LOG_FORMAT: "json"        # Output format (json or text)
  LOG_LEVEL: "INFO"         # Minimum log level
  LOG_OUTPUT: "/app/logs/service.log"  # Log file path
```

### Fluentd Configuration

Located at `infra/fluentd/fluent.conf`:
- Input sources configuration
- Parsing rules for each service
- Routing to Elasticsearch indices
- Backup file settings

### Log Rotation

Logs are automatically rotated:
- Service logs: Daily rotation, keep 5 files, max 20MB per file
- Backup logs: Daily rotation, compressed with gzip, keep 7 days
- Elasticsearch indices: Can be configured with ILM policies

## Monitoring

### Key Metrics to Track

1. **Log Volume**: Monitor log ingestion rate
2. **Error Rate**: Track ERROR and CRITICAL log frequency
3. **Service Health**: Monitor service-specific patterns
4. **Performance**: Track response times and resource usage

### Creating Dashboards

1. In Kibana, go to Dashboard → Create Dashboard
2. Add visualizations:
   - Log volume over time (line chart)
   - Error distribution by service (pie chart)
   - Recent errors (data table)
   - Token usage trends (area chart)

### Setting Up Alerts

1. Go to Stack Management → Watcher
2. Create threshold alert for error rates
3. Configure email/webhook notifications

## Troubleshooting

### No logs appearing in Kibana

1. Check Fluentd is running:
   ```bash
   docker logs dean-fluentd
   ```

2. Verify Elasticsearch is healthy:
   ```bash
   curl http://localhost:9200/_cluster/health
   ```

3. Check service logs are being generated:
   ```bash
   docker exec dean-orchestrator ls -la /app/logs/
   ```

### High log volume

1. Adjust log levels in services
2. Filter unnecessary debug logs in Fluentd
3. Implement log sampling for high-frequency events

### Elasticsearch disk space

1. Set up index lifecycle management (ILM)
2. Configure automatic deletion of old indices
3. Monitor disk usage with:
   ```bash
   curl http://localhost:9200/_cat/allocation?v
   ```

## Best Practices

1. **Structured Logging**: Always use JSON format with consistent fields
2. **Correlation IDs**: Include request IDs for tracing
3. **Context**: Include relevant context (agent_id, cycle_id, etc.)
4. **Error Details**: Include stack traces for errors
5. **Performance**: Log performance metrics for analysis
6. **Security**: Never log sensitive data (tokens, passwords)

## Example: Following an Evolution Cycle

1. Start evolution cycle and note the cycle_id
2. In Kibana, search: `cycle_id: "evolution_12345"`
3. Sort by timestamp
4. Follow the complete flow:
   - Orchestrator receives request
   - Airflow DAG triggered
   - IndexAgent creates agents
   - Evolution iterations logged
   - Patterns discovered
   - Results aggregated

This provides complete visibility into the entire evolution process.