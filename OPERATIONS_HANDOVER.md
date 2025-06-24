# DEAN System Operations Handover Package

**Date**: January 19, 2025  
**Version**: 1.0  
**System**: DEAN (Distributed Evolutionary Agent Network)

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Summary](#architecture-summary)
3. [Operational Procedures](#operational-procedures)
4. [Monitoring & Alerting](#monitoring--alerting)
5. [Incident Response](#incident-response)
6. [Maintenance Windows](#maintenance-windows)
7. [Security Considerations](#security-considerations)
8. [Contact Information](#contact-information)

---

## System Overview

### Purpose
DEAN is an orchestration system that coordinates multiple services including IndexAgent, Apache Airflow, and Evolution API. It provides unified authentication, service health monitoring, and workflow management.

### Current State
- **Production Status**: Ready for deployment
- **Services Enabled**: Orchestrator only (other services disabled by default)
- **Infrastructure**: Docker-based deployment on Windows Server
- **Database**: PostgreSQL 13 with dean_production schema
- **Cache**: Redis 7 with authentication

### Key Features
- Graceful degradation when services unavailable
- Feature flags for progressive service enablement
- JWT-based authentication
- Comprehensive health monitoring
- Prometheus metrics exposure

## Architecture Summary

### Service Map
```
┌─────────────────┐
│   Nginx Proxy   │ (Port 80/443)
└────────┬────────┘
         │
┌────────▼────────┐
│ DEAN Orchestrator│ (Port 8082)
└────────┬────────┘
         │
    ┌────┴────┬─────────┬──────────┐
    │         │         │          │
┌───▼──┐ ┌───▼──┐ ┌────▼────┐ ┌───▼──┐
│PostgreSQL│ │Redis│ │IndexAgent│ │Airflow│
└──────┘ └──────┘ └─────────┘ └──────┘
         (Disabled by default)
```

### Port Allocation
| Service | Internal Port | External Port | Purpose |
|---------|--------------|---------------|---------|
| Nginx | 80, 443 | 80, 443 | Reverse proxy |
| Orchestrator | 8082 | - | Main API |
| PostgreSQL | 5432 | - | Database |
| Redis | 6379 | - | Cache |
| Prometheus | 9090 | 9090 | Metrics |
| Grafana | 3000 | 3000 | Dashboards |

## Operational Procedures

### Daily Operations

#### 1. Morning Health Check (9 AM)
```powershell
# Check system status
.\scripts\verify_deployment.ps1 -OutputFormat Console

# Review overnight logs
docker logs dean-orchestrator --since 12h | Select-String "ERROR"

# Check resource usage
docker stats --no-stream
```

#### 2. Service Monitoring
- Access Grafana: http://localhost:3000
- Review DEAN System Overview dashboard
- Check for any triggered alerts
- Verify all services show "UP" status

#### 3. End of Day Review
- Check error rates in Grafana
- Review any incidents from the day
- Ensure backups completed successfully
- Update operational log

### Deployment Procedures

#### Standard Deployment
```powershell
# 1. Backup current state
.\scripts\backup_production.ps1

# 2. Deploy new version
.\deploy_windows.ps1 -Environment production

# 3. Verify deployment
.\scripts\verify_deployment.ps1

# 4. Monitor for 30 minutes
```

#### Emergency Rollback
```powershell
# Stop current deployment
docker-compose -f docker-compose.prod.yml down

# Restore previous version
docker-compose -f docker-compose.prod.yml.backup up -d

# Verify services
.\scripts\health_check.ps1
```

### Backup Procedures

#### Daily Backups (Automated at 2 AM)
- PostgreSQL: Full database dump
- Redis: RDB snapshot
- Configuration: Git commit
- Logs: Compressed archive

#### Manual Backup
```powershell
# Full system backup
.\scripts\backup_production.ps1 -Type Full

# Database only
docker exec dean-postgres pg_dump -U dean_prod dean_production > backup_$(date +%Y%m%d).sql

# Configuration backup
git add -A && git commit -m "Config backup $(date)"
```

### Restore Procedures
```powershell
# Database restore
cat backup_20250119.sql | docker exec -i dean-postgres psql -U dean_prod dean_production

# Redis restore
docker cp redis_backup.rdb dean-redis:/data/dump.rdb
docker restart dean-redis
```

## Monitoring & Alerting

### Key Metrics to Monitor

#### System Health
- **Uptime**: Target 99.9%
- **Response Time**: < 500ms p95
- **Error Rate**: < 0.1%
- **CPU Usage**: < 70%
- **Memory Usage**: < 80%
- **Disk Space**: > 20% free

#### Application Metrics
- Request rate (requests/second)
- Error rate by endpoint
- Database connection pool usage
- Redis hit rate
- Feature flag states

### Alert Response

#### Critical Alerts (Immediate Response)
1. **OrchestratorDown**
   - Check Docker status
   - Review logs for crash reason
   - Restart if necessary
   - Escalate if repeated

2. **DatabaseDown**
   - Verify PostgreSQL container
   - Check disk space
   - Review connection limits
   - Restart with increased resources

3. **RedisDown**
   - Check authentication
   - Verify memory limits
   - Clear cache if corrupted
   - Restart service

#### Warning Alerts (Within 2 hours)
- High CPU/Memory usage
- Slow response times
- High error rates
- Low disk space

### Dashboard Access
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093

## Incident Response

### Incident Classification
- **P1 (Critical)**: System down, data loss risk
- **P2 (High)**: Degraded performance, partial outage
- **P3 (Medium)**: Minor issues, single feature affected
- **P4 (Low)**: Cosmetic issues, no user impact

### Response Procedures

#### P1 Incident Response
1. **Acknowledge** alert within 5 minutes
2. **Assess** impact and scope
3. **Communicate** to stakeholders
4. **Execute** emergency procedures
5. **Monitor** recovery
6. **Document** root cause

#### Investigation Tools
```powershell
# System logs
docker logs dean-orchestrator --tail 1000 > incident_logs.txt

# Database queries
docker exec dean-postgres psql -U dean_prod -c "\
  SELECT * FROM pg_stat_activity WHERE state != 'idle';"

# Redis status
docker exec dean-redis redis-cli -a $REDIS_PASSWORD INFO

# Network diagnostics
docker network inspect dean_dean-net
```

### Common Issues & Solutions

#### 1. High Memory Usage
**Symptoms**: Slow responses, OOM errors
**Solution**:
```powershell
# Increase container memory
docker update --memory 4g dean-orchestrator
# Clear Redis cache if needed
docker exec dean-redis redis-cli -a $REDIS_PASSWORD FLUSHDB
```

#### 2. Database Connection Exhaustion
**Symptoms**: "too many connections" errors
**Solution**:
```powershell
# Kill idle connections
docker exec dean-postgres psql -U dean_prod -c "\
  SELECT pg_terminate_backend(pid) 
  FROM pg_stat_activity 
  WHERE state = 'idle' AND state_change < now() - interval '10 minutes';"
```

#### 3. Service Not Responding
**Symptoms**: Health check failures
**Solution**:
```powershell
# Restart specific service
docker restart dean-orchestrator
# If persistent, check logs
docker logs dean-orchestrator --tail 500
```

## Maintenance Windows

### Scheduled Maintenance
- **Weekly**: Sunday 2-4 AM (logs rotation, cache cleanup)
- **Monthly**: First Sunday 1-5 AM (updates, patches)
- **Quarterly**: Announced 2 weeks prior (major upgrades)

### Maintenance Procedures

#### Pre-Maintenance Checklist
- [ ] Notify users 24 hours in advance
- [ ] Prepare rollback plan
- [ ] Test changes in staging
- [ ] Backup production data
- [ ] Update status page

#### During Maintenance
```powershell
# 1. Enable maintenance mode
.\scripts\enable_maintenance_mode.ps1

# 2. Perform updates
.\scripts\apply_updates.ps1

# 3. Verify changes
.\scripts\verify_deployment.ps1

# 4. Disable maintenance mode
.\scripts\disable_maintenance_mode.ps1
```

#### Post-Maintenance
- [ ] Verify all services operational
- [ ] Run smoke tests
- [ ] Monitor for 30 minutes
- [ ] Update documentation
- [ ] Send completion notice

## Security Considerations

### Access Control
- **SSH Access**: Key-based only, MFA required
- **Database**: Restricted to Docker network
- **API Keys**: Rotate every 90 days
- **Monitoring**: Read-only access

### Security Checklist
- [ ] SSL certificates valid (check monthly)
- [ ] Passwords meet complexity requirements
- [ ] No default credentials in use
- [ ] Firewall rules up to date
- [ ] Security patches applied

### Credential Management
```powershell
# Rotate database password
.\scripts\rotate_db_password.ps1

# Update API keys
.\scripts\update_api_keys.ps1

# Generate new JWT secret
.\scripts\generate_jwt_secret.ps1
```

## Contact Information

### Escalation Path

#### Level 1: Operations Team
- **On-Call**: +1-XXX-XXX-XXXX
- **Email**: ops@company.com
- **Slack**: #dean-ops

#### Level 2: Platform Team
- **Lead**: platform-lead@company.com
- **Slack**: #platform-team

#### Level 3: Engineering Management
- **CTO**: cto@company.com
- **VP Engineering**: vp-eng@company.com

### External Contacts
- **Docker Support**: support-ticket-XXX
- **Cloud Provider**: account-manager@provider.com
- **Security Team**: security@company.com

### Documentation Links
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- [API Documentation](docs/api/API.md)
- [Security Guide](docs/security/SECURITY_GUIDE.md)

---

## Appendix A: Quick Reference Commands

### Health Checks
```powershell
# Service health
curl http://localhost:8082/health

# Database check
docker exec dean-postgres pg_isready

# Redis ping
docker exec dean-redis redis-cli -a $REDIS_PASSWORD ping
```

### Log Analysis
```powershell
# Error summary
docker logs dean-orchestrator 2>&1 | Select-String "ERROR" | Group-Object -Property Line | Sort-Object Count -Descending

# Request patterns
docker logs dean-nginx | awk '{print $7}' | sort | uniq -c | sort -rn | head -20
```

### Performance Tuning
```powershell
# Database vacuum
docker exec dean-postgres vacuumdb -U dean_prod -d dean_production -z

# Redis memory optimization
docker exec dean-redis redis-cli -a $REDIS_PASSWORD MEMORY DOCTOR
```

## Appendix B: Runbooks

### Runbook Index
1. [Service Restart Procedures](runbooks/service-restart.md)
2. [Database Maintenance](runbooks/database-maintenance.md)
3. [Certificate Renewal](runbooks/certificate-renewal.md)
4. [Disaster Recovery](runbooks/disaster-recovery.md)
5. [Scaling Procedures](runbooks/scaling.md)

---

**Document Version**: 1.0  
**Last Updated**: January 19, 2025  
**Next Review**: February 19, 2025