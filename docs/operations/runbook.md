# DEAN System Operational Runbook

## Table of Contents

1. [System Overview](#system-overview)
2. [Service Startup Procedures](#service-startup-procedures)
3. [Health Check Procedures](#health-check-procedures)
4. [Common Troubleshooting](#common-troubleshooting)
5. [Backup Procedures](#backup-procedures)
6. [Monitoring Setup](#monitoring-setup)
7. [Emergency Procedures](#emergency-procedures)
8. [Maintenance Windows](#maintenance-windows)

## System Overview

The DEAN (Distributed Evolutionary Agent Network) system consists of four interconnected services:

| Service | Port | Purpose | Repository |
|---------|------|---------|------------|
| DEAN Orchestrator | 8082-8083 | Central coordination | DEAN |
| IndexAgent | 8081 | Agent logic & evolution | IndexAgent |
| Evolution API | 8090-8091 | Economic governance | infra |
| Airflow | 8080 | Workflow orchestration | airflow-hub |

### Dependencies

- PostgreSQL (5432) - Primary database
- Redis (6379) - Caching and agent registry
- Prometheus (9090) - Metrics collection
- Grafana (3000) - Metrics visualization
- Elasticsearch (9200) - Log storage
- Kibana (5601) - Log visualization

## Service Startup Procedures

### 1. Complete System Startup

```bash
# Navigate to infrastructure directory
cd infra

# Start all services
docker-compose -f docker-compose.dean-complete.yml up -d

# With logging enabled
docker-compose -f docker-compose.dean-complete.yml \
                -f docker-compose.dean-logging.yml up -d

# Monitor startup logs
docker-compose logs -f --tail=100
```

### 2. Startup Order

Services must start in this order:

1. **Infrastructure** (Parallel)
   - PostgreSQL
   - Redis
   - Elasticsearch (if logging enabled)

2. **Core Services** (Sequential)
   - Evolution API
   - IndexAgent
   - DEAN Orchestrator

3. **Orchestration** (Parallel)
   - Airflow Scheduler
   - Airflow Webserver

4. **Monitoring** (Parallel)
   - Prometheus
   - Grafana
   - Fluentd
   - Kibana

### 3. Verify Startup

```bash
# Check all services are running
docker-compose ps

# Verify health status
for service in postgres redis dean-orchestrator indexagent dean-api airflow-webserver; do
  echo "Checking $service..."
  docker-compose exec $service echo "Service is responsive"
done
```

## Health Check Procedures

### 1. Quick Health Check

```bash
#!/bin/bash
# Save as check_health.sh

echo "=== DEAN System Health Check ==="

# Check service endpoints
services=(
  "DEAN Orchestrator|http://localhost:8082/health"
  "IndexAgent|http://localhost:8081/health"
  "Evolution API|http://localhost:8090/health"
  "Airflow|http://localhost:8080/health"
  "Prometheus|http://localhost:9090/-/healthy"
  "Grafana|http://localhost:3000/api/health"
)

for service in "${services[@]}"; do
  IFS='|' read -r name url <<< "$service"
  printf "%-20s: " "$name"
  
  if curl -sf "$url" > /dev/null; then
    echo "✅ Healthy"
  else
    echo "❌ Unhealthy"
  fi
done

# Check database
printf "%-20s: " "PostgreSQL"
if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
  echo "✅ Ready"
else
  echo "❌ Not Ready"
fi

# Check Redis
printf "%-20s: " "Redis"
if docker-compose exec -T redis redis-cli ping | grep -q PONG; then
  echo "✅ Ready"
else
  echo "❌ Not Ready"
fi
```

### 2. Detailed Health Check

```bash
# Get detailed status from each service
curl -s http://localhost:8082/health | jq '.'  # DEAN Orchestrator
curl -s http://localhost:8081/health | jq '.'  # IndexAgent
curl -s http://localhost:8090/health | jq '.'  # Evolution API

# Check service dependencies
curl -s http://localhost:8082/api/v1/services/status | jq '.'
```

### 3. Database Health

```bash
# Check database connections
docker-compose exec postgres psql -U postgres -d agent_evolution -c "
SELECT 
  datname,
  numbackends as connections,
  pg_size_pretty(pg_database_size(datname)) as size
FROM pg_stat_database
WHERE datname = 'agent_evolution';"

# Check table sizes
docker-compose exec postgres psql -U postgres -d agent_evolution -c "
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

## Common Troubleshooting

### Issue: Service Won't Start

**Symptoms**: Container exits immediately or restarts continuously

**Resolution**:
```bash
# Check logs for specific service
docker-compose logs dean-orchestrator --tail=50

# Common issues:
# 1. Port already in use
lsof -i :8082  # Check if port is free

# 2. Database connection failed
docker-compose exec postgres psql -U postgres -c "\l"

# 3. Missing environment variables
docker-compose config | grep -A5 "environment:"
```

### Issue: Evolution Cycle Stuck

**Symptoms**: Evolution status remains "running" indefinitely

**Resolution**:
```bash
# Check Airflow DAG status
curl -X GET http://localhost:8080/api/v1/dags/dean_agent_evolution/dagRuns \
  --user admin:admin | jq '.'

# Check for token budget depletion
curl http://localhost:8090/api/v1/economy/budget | jq '.'

# Force stop evolution cycle
curl -X POST http://localhost:8082/api/v1/evolution/{cycle_id}/stop \
  -H "Authorization: Bearer $TOKEN"
```

### Issue: High Memory Usage

**Symptoms**: Services consuming excessive memory

**Resolution**:
```bash
# Check memory usage
docker stats --no-stream

# Restart specific service
docker-compose restart indexagent

# Clear Redis cache
docker-compose exec redis redis-cli FLUSHDB

# Vacuum PostgreSQL
docker-compose exec postgres vacuumdb -U postgres -d agent_evolution -z
```

### Issue: Patterns Not Being Discovered

**Symptoms**: No patterns found after evolution cycles

**Resolution**:
```bash
# Check pattern detection is enabled
curl http://localhost:8081/api/v1/patterns | jq '.'

# Verify evolution parameters
curl http://localhost:8090/api/v1/evolution/constraints | jq '.'

# Check agent diversity
curl -X POST http://localhost:8081/api/v1/diversity/population \
  -H "Content-Type: application/json" \
  -d '{"population_ids": ["agent_001", "agent_002"]}' | jq '.'
```

## Backup Procedures

### 1. Automated Backup Script

```bash
#!/bin/bash
# Save as backup_dean.sh

BACKUP_DIR="/backups/dean/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Starting DEAN backup to $BACKUP_DIR"

# Backup database
docker-compose exec -T postgres pg_dump -U postgres agent_evolution \
  > "$BACKUP_DIR/agent_evolution.sql"

# Backup Redis
docker-compose exec -T redis redis-cli --rdb "$BACKUP_DIR/redis.rdb"

# Backup discovered patterns
docker cp dean-api:/app/patterns "$BACKUP_DIR/patterns"

# Backup agent worktrees (selective)
docker cp indexagent:/app/worktrees "$BACKUP_DIR/worktrees"

# Backup configurations
cp -r ../*/configs "$BACKUP_DIR/configs"

# Create backup metadata
cat > "$BACKUP_DIR/metadata.json" << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "version": "$(curl -s http://localhost:8082/health | jq -r .version)",
  "services": {
    "dean": "$(docker inspect dean-orchestrator --format='{{.Image}}')",
    "indexagent": "$(docker inspect indexagent --format='{{.Image}}')",
    "evolution": "$(docker inspect dean-api --format='{{.Image}}')"
  }
}
EOF

# Compress backup
tar -czf "$BACKUP_DIR.tar.gz" -C "$(dirname $BACKUP_DIR)" "$(basename $BACKUP_DIR)"
rm -rf "$BACKUP_DIR"

echo "Backup completed: $BACKUP_DIR.tar.gz"
```

### 2. Restore Procedure

```bash
#!/bin/bash
# Save as restore_dean.sh

BACKUP_FILE="$1"
RESTORE_DIR="/tmp/dean_restore"

# Extract backup
tar -xzf "$BACKUP_FILE" -C /tmp

# Stop services
docker-compose down

# Restore database
docker-compose up -d postgres
sleep 10
docker-compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS agent_evolution;"
docker-compose exec -T postgres psql -U postgres -c "CREATE DATABASE agent_evolution;"
docker-compose exec -T postgres psql -U postgres agent_evolution < "$RESTORE_DIR/agent_evolution.sql"

# Restore Redis
docker-compose up -d redis
docker cp "$RESTORE_DIR/redis.rdb" redis:/data/dump.rdb
docker-compose restart redis

# Restore patterns and worktrees
docker-compose up -d dean-api indexagent
docker cp "$RESTORE_DIR/patterns" dean-api:/app/
docker cp "$RESTORE_DIR/worktrees" indexagent:/app/

# Start all services
docker-compose up -d

echo "Restore completed from $BACKUP_FILE"
```

## Monitoring Setup

### 1. Prometheus Metrics

Key metrics to monitor:

```yaml
# Critical metrics
- dean_agents_active_total
- dean_tokens_consumed_total
- dean_patterns_discovered_total
- dean_evolution_cycles_total
- dean_api_request_duration_seconds
- dean_api_requests_total
```

### 2. Grafana Dashboards

Import dashboards:
```bash
# Access Grafana
open http://localhost:3000  # admin/admin

# Import dashboards from
infra/modules/agent-evolution/monitoring/dashboards/
- dean_agent_details.json
- dean_economic_analysis.json
- dean_evolution_overview.json
```

### 3. Alerting Rules

```yaml
# Sample alert for token depletion
groups:
  - name: dean_alerts
    rules:
      - alert: TokenBudgetLow
        expr: dean_tokens_remaining < 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Token budget running low"
          description: "Only {{ $value }} tokens remaining"
```

## Emergency Procedures

### 1. Emergency Shutdown

```bash
# Immediate shutdown (data loss possible)
docker-compose kill

# Graceful shutdown
docker-compose stop

# Shutdown specific service
docker-compose stop dean-orchestrator
```

### 2. Resource Exhaustion

```bash
# CPU/Memory limits exceeded
# 1. Identify problematic service
docker stats

# 2. Restart with resource limits
docker-compose down indexagent
docker run -d --name indexagent \
  --memory="2g" --cpus="1.5" \
  [original docker run parameters]
```

### 3. Data Corruption Recovery

```bash
# Database corruption
docker-compose exec postgres pg_dump -U postgres -d agent_evolution -f /tmp/emergency_backup.sql
docker-compose down postgres
docker volume rm dean-postgres-data
docker-compose up -d postgres
# Restore from last known good backup
```

### 4. Security Incident

```bash
# Suspected compromise
# 1. Isolate system
docker-compose down

# 2. Rotate all secrets
./scripts/rotate_secrets.sh

# 3. Audit logs
docker-compose logs --since "2 hours ago" > incident_logs.txt

# 4. Restart with new credentials
docker-compose up -d
```

## Maintenance Windows

### Weekly Maintenance (Sundays 2-4 AM)

1. **Database Maintenance**
   ```bash
   docker-compose exec postgres vacuumdb -U postgres -d agent_evolution -z
   docker-compose exec postgres reindexdb -U postgres -d agent_evolution
   ```

2. **Log Rotation**
   ```bash
   # Elasticsearch index cleanup
   curl -X DELETE "localhost:9200/dean-*-$(date -d '30 days ago' +%Y.%m.%d)"
   ```

3. **Pattern Cleanup**
   ```bash
   # Archive unused patterns
   curl -X POST http://localhost:8082/api/v1/patterns/archive \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"older_than_days": 30, "min_usage": 5}'
   ```

### Monthly Maintenance (First Sunday)

1. **Full System Backup**
2. **Security Updates**
   ```bash
   docker-compose pull
   docker-compose up -d
   ```
3. **Performance Analysis**
4. **Capacity Planning Review**

## Contacts

- **On-Call Engineer**: +1-XXX-XXX-XXXX
- **System Architect**: architect@example.com
- **Database Admin**: dba@example.com
- **Security Team**: security@example.com

## Appendix: Quick Commands

```bash
# View recent errors
docker-compose logs --tail=100 | grep ERROR

# Check token usage
curl http://localhost:8082/api/v1/metrics/tokens | jq '.'

# List active agents
curl http://localhost:8081/api/v1/agents | jq '.agents[] | {id, status, token_budget}'

# Trigger manual evolution
curl -X POST http://localhost:8082/api/v1/evolution/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"population_ids": ["agent_001"], "generations": 5, "token_budget": 1000}'

# Emergency token allocation
curl -X POST http://localhost:8090/api/v1/economy/allocate \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "agent_001", "requested_tokens": 5000, "priority": "high"}'
```