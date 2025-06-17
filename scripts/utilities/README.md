# DEAN Operational Utilities

This directory contains operational tools for maintaining and monitoring the DEAN orchestration system.

## Available Tools

### monitor_system.py
Real-time monitoring dashboard for DEAN services.

**Features:**
- Interactive terminal dashboard
- Service health monitoring
- Performance metrics collection
- Alert detection and reporting
- JSON output for automation

**Usage:**
```bash
# Interactive dashboard (default)
./monitor_system.py

# JSON output for scripting
./monitor_system.py --output json

# Custom refresh interval
./monitor_system.py --interval 10

# Monitor specific services
./monitor_system.py \
  --orchestration-url http://dean.example.com:8082 \
  --indexagent-url http://dean.example.com:8081
```

**Dashboard View:**
- System health percentage
- Service status indicators
- Response time metrics
- Active alerts
- Real-time updates via WebSocket

### backup_restore.sh
Comprehensive backup and restore utility for DEAN data.

**Features:**
- Full system backups
- Component-specific backups
- Compressed archives with metadata
- Backup verification
- Automated cleanup

**Commands:**
```bash
# Create full backup
./backup_restore.sh backup

# Backup with custom name
./backup_restore.sh backup -n production-backup

# Component-specific backups
./backup_restore.sh backup --postgres-only
./backup_restore.sh backup --redis-only
./backup_restore.sh backup --config-only

# Restore from backup
./backup_restore.sh restore -f backup-20240101.tar.gz

# List available backups
./backup_restore.sh list

# Verify backup integrity
./backup_restore.sh verify -f backup-20240101.tar.gz

# Clean old backups (keep last 30 days)
./backup_restore.sh cleanup --keep 30
```

**Backup Contents:**
- PostgreSQL database dump
- Redis data snapshot
- Configuration files
- Docker Compose files
- Environment files
- Metadata with timestamps

### db_migrate.py
Database schema migration management tool.

**Features:**
- Version-controlled migrations
- Automatic rollback support
- Migration checksums for integrity
- Dry-run mode
- Migration history tracking

**Commands:**
```bash
# Check current status
./db_migrate.py status

# Apply all pending migrations
./db_migrate.py migrate

# Dry run (show what would be done)
./db_migrate.py migrate --dry-run

# Create new migration
./db_migrate.py create add_performance_indexes

# Rollback specific migration
./db_migrate.py rollback 20240101000001_initial_schema
```

**Migration Files:**
- Located in `migrations/` directory
- Format: `YYYYMMDDHHMMSS_description.sql`
- Rollback: `YYYYMMDDHHMMSS_description.rollback.sql`
- Checksums prevent modification after application

### analyze_logs.py
Advanced log analysis and pattern detection tool.

**Features:**
- Error pattern identification
- API performance metrics
- Timeline analysis
- Support for compressed logs (.gz)
- Rich terminal output
- JSON export capability

**Usage:**
```bash
# Analyze recent logs
./analyze_logs.py /var/log/dean/*.log

# Focus on errors
./analyze_logs.py logs/*.log --errors-only

# API performance analysis
./analyze_logs.py logs/*.log --api-only

# Include timeline analysis
./analyze_logs.py logs/*.log --timeline

# Export as JSON
./analyze_logs.py logs/*.log --output json > analysis.json

# Analyze compressed logs
./analyze_logs.py logs/*.log.gz
```

**Analysis Output:**
- Error summary by service
- Top error messages
- API endpoint performance
- Response time statistics
- Memory usage patterns
- Timeline visualization

### dean-completion.bash
Bash completion script for the dean CLI.

**Installation:**
```bash
# For current session
source scripts/utilities/dean-completion.bash

# Permanent installation (user)
echo "source $(pwd)/scripts/utilities/dean-completion.bash" >> ~/.bashrc

# System-wide installation
sudo cp dean-completion.bash /etc/bash_completion.d/dean
```

**Features:**
- Command completion
- Subcommand suggestions
- Option hints
- Repository name completion

## Configuration

### Environment Variables

All utilities respect these environment variables:

```bash
# Database
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=secure_password
export POSTGRES_DB=dean_orchestration

# Redis
export REDIS_HOST=localhost
export REDIS_PORT=6379

# Services
export ORCHESTRATION_URL=http://localhost:8082
export INDEXAGENT_URL=http://localhost:8081
export AIRFLOW_URL=http://localhost:8080
export EVOLUTION_URL=http://localhost:8083

# Backup
export BACKUP_DIR=$HOME/dean-backups

# Logging
export LOG_LEVEL=INFO
```

### Configuration Files

Some utilities support configuration files:

```yaml
# ~/.dean/monitor.yaml
services:
  orchestration:
    url: http://localhost:8082
    timeout: 5
  indexagent:
    url: http://localhost:8081
    timeout: 10
    
alerts:
  response_time_threshold: 2.0
  error_rate_threshold: 0.1
```

## Integration Examples

### Automated Monitoring
```bash
#!/bin/bash
# Monitor and alert on issues

while true; do
    OUTPUT=$(./monitor_system.py --output json)
    
    if echo "$OUTPUT" | jq -e '.alerts | length > 0' >/dev/null; then
        # Send alert
        echo "$OUTPUT" | jq '.alerts' | mail -s "DEAN Alert" ops@example.com
    fi
    
    sleep 300  # Check every 5 minutes
done
```

### Backup Automation
```bash
#!/bin/bash
# Daily backup with rotation

# Create backup
./backup_restore.sh backup -n "daily-$(date +%Y%m%d)"

# Upload to S3
aws s3 cp ~/dean-backups/daily-*.tar.gz s3://dean-backups/

# Clean local backups older than 7 days
./backup_restore.sh cleanup --keep 7
```

### Log Analysis Pipeline
```bash
#!/bin/bash
# Analyze logs and generate report

# Collect logs
kubectl logs -n dean-system deployment/dean-orchestration > today.log

# Analyze
./analyze_logs.py today.log --output json > analysis.json

# Generate metrics
cat analysis.json | jq '{
    error_rate: .errors.error_rate,
    api_success_rate: .api_performance.overall_success_rate,
    total_errors: .errors.total
}' > metrics.json

# Send to monitoring system
curl -X POST http://prometheus-pushgateway:9091/metrics/job/log_analysis \
    -H "Content-Type: application/json" \
    -d @metrics.json
```

## Development Guidelines

When creating new utilities:

1. **Error Handling**: Always handle errors gracefully
2. **Help Text**: Include comprehensive --help
3. **Exit Codes**: Use standard exit codes (0=success, 1=error)
4. **Logging**: Use structured logging where appropriate
5. **Progress**: Show progress for long operations
6. **Dry Run**: Add --dry-run for destructive operations
7. **Colors**: Use colors for better readability
8. **JSON Output**: Support JSON for automation

## Troubleshooting

### Permission Issues
```bash
# Make scripts executable
chmod +x *.py *.sh

# Fix Python shebang if needed
sed -i '1s|.*|#!/usr/bin/env python3|' *.py
```

### Missing Dependencies
```bash
# Python dependencies
pip install -r requirements/base.txt

# System dependencies (Ubuntu/Debian)
sudo apt-get install postgresql-client redis-tools jq

# System dependencies (macOS)
brew install postgresql redis jq
```

### Connection Problems
```bash
# Test database connection
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1"

# Test Redis connection
redis-cli -h $REDIS_HOST ping

# Test service endpoints
curl -f http://localhost:8082/health
```

### Debug Mode
```bash
# Bash scripts
DEBUG=1 ./backup_restore.sh backup

# Python scripts
LOG_LEVEL=DEBUG ./monitor_system.py
```

## Security Notes

1. **Credentials**: Never hardcode credentials in scripts
2. **Backups**: Encrypt sensitive backups before storage
3. **Logs**: Sanitize logs before analysis to remove secrets
4. **Network**: Use TLS for remote connections
5. **Permissions**: Restrict script permissions appropriately

## Contributing

When adding new utilities:
1. Follow existing naming conventions
2. Add comprehensive documentation
3. Include error handling and validation
4. Write unit tests where applicable
5. Update this README
6. Test on multiple platforms