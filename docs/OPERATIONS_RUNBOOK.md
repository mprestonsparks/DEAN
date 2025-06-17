# DEAN Operations Runbook

This runbook provides step-by-step procedures for operating and maintaining the DEAN Orchestration System in production.

## Table of Contents

1. [Daily Operational Tasks](#daily-operational-tasks)
2. [Common Troubleshooting](#common-troubleshooting)
3. [Performance Tuning](#performance-tuning)
4. [Security Incident Response](#security-incident-response)
5. [Upgrade Procedures](#upgrade-procedures)
6. [Rollback Procedures](#rollback-procedures)
7. [Emergency Contacts](#emergency-contacts)

---

## Daily Operational Tasks

### Morning Health Check (Start of Day)

**Time Required**: 15 minutes

1. **Check System Status**
   ```bash
   # Run comprehensive health check
   ./scripts/health_check.sh --production
   
   # Expected output: All services GREEN
   ```

2. **Review Overnight Metrics**
   ```bash
   # Check overnight activity
   docker exec postgres-prod psql -U dean -d dean_production -c "
   SELECT 
     COUNT(*) as overnight_trials,
     AVG(fitness_score) as avg_fitness,
     COUNT(DISTINCT pattern_id) as patterns_discovered
   FROM evolution_trials 
   WHERE created_at > NOW() - INTERVAL '12 hours';"
   ```

3. **Check Error Logs**
   ```bash
   # Review error logs from last 12 hours
   grep -i error /var/log/dean/*.log | grep "$(date +%Y-%m-%d)" | tail -50
   
   # Check for failed authentication attempts
   grep "401\|403" /var/log/dean/access.log | wc -l
   ```

4. **Verify Backup Completion**
   ```bash
   # Check last backup timestamp
   ls -la /backups/dean/ | tail -5
   
   # Verify backup integrity
   ./scripts/utilities/verify_backup.sh
   ```

5. **Resource Usage Review**
   ```bash
   # Check disk space
   df -h | grep -E "/$|/var|/backups"
   
   # Check container resources
   docker stats --no-stream
   ```

### Midday Performance Check

**Time Required**: 10 minutes

1. **API Response Times**
   ```bash
   # Test key endpoints
   ./scripts/api_performance_test.sh
   
   # Expected: < 200ms average response time
   ```

2. **Active Connections**
   ```bash
   # Database connections
   docker exec postgres-prod psql -U dean -c "
   SELECT count(*) as active_connections 
   FROM pg_stat_activity 
   WHERE state = 'active';"
   
   # Redis connections
   docker exec redis-prod redis-cli info clients
   ```

3. **Evolution Trial Status**
   ```bash
   # Check running trials
   curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
     https://localhost/api/evolution/trials?status=running | jq '.total'
   ```

### End of Day Tasks

**Time Required**: 20 minutes

1. **Generate Daily Report**
   ```bash
   # Run daily report script
   ./scripts/reports/daily_summary.sh > /reports/daily_$(date +%Y%m%d).txt
   ```

2. **Archive Logs**
   ```bash
   # Rotate and compress logs
   ./scripts/utilities/rotate_logs.sh
   ```

3. **Update Metrics Dashboard**
   ```bash
   # Push metrics to monitoring system
   ./scripts/metrics/push_daily_metrics.sh
   ```

4. **Security Scan**
   ```bash
   # Quick security audit
   ./scripts/security_audit.py --quick
   ```

---

## Common Troubleshooting

### Service Won't Start

**Symptoms**: Service fails to start or crashes immediately

**Resolution Steps**:

1. **Check logs**
   ```bash
   docker logs dean-orchestrator --tail=100
   docker logs postgres-prod --tail=50
   ```

2. **Verify configuration**
   ```bash
   # Check environment variables
   docker-compose -f docker-compose.prod.yml config
   
   # Validate .env file
   ./scripts/validate_config.sh
   ```

3. **Check port conflicts**
   ```bash
   lsof -i :8082
   lsof -i :5432
   ```

4. **Restart with cleanup**
   ```bash
   docker-compose -f docker-compose.prod.yml down -v
   docker-compose -f docker-compose.prod.yml up -d
   ```

### High Memory Usage

**Symptoms**: Container using excessive memory, OOM errors

**Resolution Steps**:

1. **Identify memory consumer**
   ```bash
   docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}"
   ```

2. **Check for memory leaks**
   ```bash
   # For orchestrator service
   docker exec dean-orchestrator ps aux | sort -nrk 4 | head
   
   # Check Redis memory
   docker exec redis-prod redis-cli info memory | grep used_memory_human
   ```

3. **Clear caches if needed**
   ```bash
   # Clear Redis cache
   docker exec redis-prod redis-cli FLUSHDB
   
   # Restart service
   docker-compose -f docker-compose.prod.yml restart orchestrator
   ```

4. **Adjust memory limits**
   ```yaml
   # In docker-compose.prod.yml
   deploy:
     resources:
       limits:
         memory: 8G  # Increase if needed
   ```

### Database Connection Issues

**Symptoms**: "Connection refused" or "too many connections" errors

**Resolution Steps**:

1. **Check connection count**
   ```bash
   docker exec postgres-prod psql -U dean -c "
   SELECT count(*), state 
   FROM pg_stat_activity 
   GROUP BY state;"
   ```

2. **Kill idle connections**
   ```bash
   docker exec postgres-prod psql -U dean -c "
   SELECT pg_terminate_backend(pid) 
   FROM pg_stat_activity 
   WHERE state = 'idle' 
   AND state_change < now() - interval '10 minutes';"
   ```

3. **Restart connection pool**
   ```bash
   docker-compose -f docker-compose.prod.yml restart orchestrator
   ```

4. **Increase connection limit if needed**
   ```sql
   -- In PostgreSQL
   ALTER SYSTEM SET max_connections = 200;
   -- Restart required
   ```

### API Performance Degradation

**Symptoms**: Slow response times, timeouts

**Resolution Steps**:

1. **Check current load**
   ```bash
   # API request rate
   tail -1000 /var/log/dean/access.log | \
     awk '{print $4}' | sort | uniq -c | sort -nr | head
   ```

2. **Identify slow queries**
   ```sql
   -- In PostgreSQL
   SELECT query, mean_exec_time, calls 
   FROM pg_stat_statements 
   ORDER BY mean_exec_time DESC 
   LIMIT 10;
   ```

3. **Clear stuck evolution trials**
   ```bash
   # Find stuck trials
   curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
     "https://localhost/api/evolution/trials?status=running" | \
     jq '.trials[] | select(.updated_at < (now - 3600))'
   ```

4. **Scale horizontally if needed**
   ```bash
   # Increase worker processes
   docker-compose -f docker-compose.prod.yml scale orchestrator=3
   ```

### Authentication Failures

**Symptoms**: Users unable to login, token errors

**Resolution Steps**:

1. **Check Redis connectivity**
   ```bash
   docker exec redis-prod redis-cli ping
   ```

2. **Verify JWT secret**
   ```bash
   # Ensure JWT_SECRET_KEY is set correctly
   grep JWT_SECRET .env
   ```

3. **Clear auth cache**
   ```bash
   docker exec redis-prod redis-cli --scan --pattern "auth:*" | \
     xargs docker exec redis-prod redis-cli del
   ```

4. **Reset user password if needed**
   ```bash
   ./scripts/utilities/reset_user_password.sh username
   ```

---

## Performance Tuning

### Database Optimization

1. **Update table statistics**
   ```sql
   -- Run weekly
   ANALYZE;
   
   -- Reindex if needed (during maintenance window)
   REINDEX DATABASE dean_production;
   ```

2. **Query optimization**
   ```sql
   -- Add missing indexes
   CREATE INDEX CONCURRENTLY idx_trials_status_created 
   ON evolution_trials(status, created_at);
   
   -- Monitor slow queries
   SELECT * FROM pg_stat_statements 
   WHERE mean_exec_time > 100 
   ORDER BY mean_exec_time DESC;
   ```

3. **Connection pooling**
   ```python
   # In application config
   DATABASE_POOL_SIZE = 20
   DATABASE_MAX_OVERFLOW = 40
   DATABASE_POOL_TIMEOUT = 30
   ```

### Redis Optimization

1. **Memory management**
   ```bash
   # Set eviction policy
   docker exec redis-prod redis-cli CONFIG SET maxmemory-policy allkeys-lru
   
   # Monitor memory usage
   docker exec redis-prod redis-cli INFO memory
   ```

2. **Key expiration**
   ```bash
   # Set TTL for cache keys
   docker exec redis-prod redis-cli CONFIG SET \
     notify-keyspace-events Ex
   ```

### Application Optimization

1. **Increase workers**
   ```bash
   # Edit .env
   UVICORN_WORKERS=8  # Based on CPU cores
   MAX_WORKERS=16
   ```

2. **Enable caching**
   ```bash
   # In .env
   ENABLE_CACHE=true
   CACHE_TTL=300
   ```

3. **Optimize container resources**
   ```yaml
   # docker-compose.prod.yml
   deploy:
     resources:
       limits:
         cpus: '4'
         memory: 8G
       reservations:
         cpus: '2'
         memory: 4G
   ```

---

## Security Incident Response

### Suspected Breach

**Immediate Actions**:

1. **Isolate the system**
   ```bash
   # Block external access
   sudo ufw deny 443
   sudo ufw deny 80
   ```

2. **Preserve evidence**
   ```bash
   # Snapshot logs
   tar -czf /secure/incident_$(date +%Y%m%d_%H%M%S).tar.gz \
     /var/log/dean/ /var/log/auth.log /var/log/syslog
   ```

3. **Check for unauthorized access**
   ```bash
   # Recent logins
   grep "Successful login" /var/log/dean/auth.log | tail -50
   
   # Failed attempts
   grep "Failed login" /var/log/dean/auth.log | \
     awk '{print $5}' | sort | uniq -c | sort -nr
   ```

4. **Rotate credentials**
   ```bash
   # Generate new secrets
   ./scripts/security/rotate_all_secrets.sh
   
   # Force logout all users
   docker exec redis-prod redis-cli FLUSHDB
   ```

### DDoS Attack

**Immediate Actions**:

1. **Enable rate limiting**
   ```nginx
   # In nginx.conf
   limit_req_zone $binary_remote_addr zone=api:10m rate=1r/s;
   limit_req zone=api burst=5 nodelay;
   ```

2. **Block suspicious IPs**
   ```bash
   # Analyze access logs
   tail -10000 /var/log/nginx/access.log | \
     awk '{print $1}' | sort | uniq -c | sort -nr | head -20
   
   # Block IPs
   sudo ufw deny from <suspicious_ip>
   ```

3. **Enable Cloudflare/CDN protection**
   ```bash
   # Update DNS to route through CDN
   # Enable DDoS protection in CDN settings
   ```

### Data Breach

**Immediate Actions**:

1. **Disable affected accounts**
   ```sql
   -- Disable compromised users
   UPDATE users SET is_active = false 
   WHERE username IN ('user1', 'user2');
   ```

2. **Audit data access**
   ```sql
   -- Check recent data access
   SELECT user_id, action, timestamp 
   FROM audit_log 
   WHERE timestamp > NOW() - INTERVAL '24 hours'
   ORDER BY timestamp DESC;
   ```

3. **Notify stakeholders**
   - Security team
   - Legal department
   - Affected users (if required)

---

## Upgrade Procedures

### Minor Version Update (e.g., 1.0.0 → 1.0.1)

**Duration**: 30 minutes

1. **Pre-upgrade backup**
   ```bash
   ./scripts/utilities/full_backup.sh pre-upgrade-1.0.1
   ```

2. **Pull new images**
   ```bash
   docker-compose -f docker-compose.prod.yml pull
   ```

3. **Rolling update**
   ```bash
   # Update one service at a time
   docker-compose -f docker-compose.prod.yml up -d --no-deps orchestrator
   sleep 30
   ./scripts/health_check.sh --service orchestrator
   ```

4. **Run migrations**
   ```bash
   docker-compose -f docker-compose.prod.yml run --rm \
     orchestrator python -m alembic upgrade head
   ```

5. **Verify upgrade**
   ```bash
   ./scripts/final_validation.sh --production
   ```

### Major Version Update (e.g., 1.0.0 → 2.0.0)

**Duration**: 2-4 hours (maintenance window required)

1. **Announcement**
   ```bash
   # Send maintenance notification
   ./scripts/notifications/send_maintenance_notice.sh \
     --start "2024-01-20 02:00" \
     --duration "4 hours"
   ```

2. **Complete backup**
   ```bash
   # Full system backup
   ./scripts/utilities/full_system_backup.sh major-upgrade-2.0.0
   ```

3. **Stop services**
   ```bash
   docker-compose -f docker-compose.prod.yml down
   ```

4. **Update configuration**
   ```bash
   # Backup current config
   cp .env .env.backup
   
   # Apply new config template
   ./scripts/upgrade/apply_config_changes.sh 2.0.0
   ```

5. **Deploy new version**
   ```bash
   # Deploy new version
   docker-compose -f docker-compose.prod.yml.v2 up -d
   ```

6. **Run upgrade scripts**
   ```bash
   ./scripts/upgrade/upgrade_to_2.0.0.sh
   ```

7. **Validation**
   ```bash
   ./scripts/upgrade/validate_major_upgrade.sh
   ```

---

## Rollback Procedures

### Quick Rollback (< 5 minutes)

**When to use**: Immediate issues after deployment

1. **Switch to previous version**
   ```bash
   # Tag current as bad
   docker tag dean/orchestrator:latest dean/orchestrator:bad
   
   # Restore previous
   docker tag dean/orchestrator:previous dean/orchestrator:latest
   ```

2. **Restart services**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Verify rollback**
   ```bash
   ./scripts/health_check.sh --production
   ```

### Full Rollback (30 minutes)

**When to use**: Database changes need reverting

1. **Stop services**
   ```bash
   docker-compose -f docker-compose.prod.yml down
   ```

2. **Restore database**
   ```bash
   # Restore from backup
   ./scripts/utilities/restore_database.sh /backups/dean/pre-upgrade-backup.sql.gz
   ```

3. **Restore application**
   ```bash
   # Restore previous images
   docker-compose -f docker-compose.prod.yml.backup up -d
   ```

4. **Restore configuration**
   ```bash
   cp .env.backup .env
   ```

5. **Verify system**
   ```bash
   ./scripts/final_validation.sh --production
   ```

### Emergency Rollback

**When to use**: Critical system failure

1. **Activate emergency mode**
   ```bash
   # Enable maintenance page
   docker run -d --name maintenance \
     -p 80:80 -p 443:443 \
     -v /opt/dean/maintenance:/usr/share/nginx/html \
     nginx:alpine
   ```

2. **Stop all DEAN services**
   ```bash
   docker-compose -f docker-compose.prod.yml down -v
   ```

3. **Restore from snapshot**
   ```bash
   # Restore complete system snapshot
   ./scripts/emergency/restore_snapshot.sh latest
   ```

4. **Restart services**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

5. **Post-recovery validation**
   ```bash
   ./scripts/emergency/post_recovery_check.sh
   ```

---

## Emergency Contacts

### Escalation Matrix

| Level | Issue Type | Contact | Response Time |
|-------|-----------|---------|---------------|
| 1 | Service Down | On-Call Engineer | 15 minutes |
| 2 | Security Incident | Security Team | Immediate |
| 3 | Data Loss | Database Admin | 30 minutes |
| 4 | Performance Critical | Platform Team | 1 hour |

### Contact Template

```yaml
# Update with your organization's contacts
on_call_engineer:
  primary: "+1-XXX-XXX-XXXX"
  secondary: "+1-XXX-XXX-XXXX"
  email: "oncall@company.com"

security_team:
  hotline: "+1-XXX-XXX-XXXX"
  email: "security@company.com"
  slack: "#security-incidents"

database_admin:
  primary: "+1-XXX-XXX-XXXX"
  email: "dba@company.com"

platform_team:
  email: "platform@company.com"
  slack: "#platform-support"

management:
  cto: "cto@company.com"
  vp_engineering: "vp-eng@company.com"

external:
  hosting_support: "+1-XXX-XXX-XXXX"
  cdn_support: "+1-XXX-XXX-XXXX"
```

### Incident Communication Template

```
Subject: [SEVERITY] DEAN System Incident - [BRIEF DESCRIPTION]

Current Status: [Investigating/Identified/Monitoring/Resolved]
Start Time: [ISO 8601 timestamp]
Services Affected: [List services]
User Impact: [None/Partial/Full]

Description:
[Brief description of the issue]

Actions Taken:
- [Action 1 with timestamp]
- [Action 2 with timestamp]

Next Steps:
- [Planned action 1]
- [Planned action 2]

ETA for Resolution: [Time estimate]

Contact: [On-call engineer name] - [Phone]
```

---

## Appendix: Quick Reference Scripts

### Health Check One-Liner
```bash
curl -s http://localhost:8082/health | jq '.status'
```

### Quick Metrics
```bash
docker exec postgres-prod psql -U dean -c "SELECT 'Agents:' as metric, COUNT(*) as value FROM agents UNION SELECT 'Trials Today:', COUNT(*) FROM evolution_trials WHERE created_at > CURRENT_DATE UNION SELECT 'Active Users:', COUNT(DISTINCT user_id) FROM audit_log WHERE timestamp > NOW() - INTERVAL '1 hour';"
```

### Emergency Service Restart
```bash
docker-compose -f docker-compose.prod.yml restart && sleep 10 && ./scripts/health_check.sh --production
```

### Log Analysis
```bash
# Error summary
grep -E "ERROR|CRITICAL" /var/log/dean/*.log | awk '{print $5}' | sort | uniq -c | sort -nr

# Response time analysis
awk '{print $10}' /var/log/nginx/access.log | sort -n | awk '{a[NR]=$1} END {print "P50:", a[int(NR*0.5)], "P95:", a[int(NR*0.95)], "P99:", a[int(NR*0.99)]}'
```

---

**Last Updated**: 2025-06-15
**Version**: 1.0.0