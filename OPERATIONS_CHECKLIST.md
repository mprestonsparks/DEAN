# DEAN Operations Daily Checklist

**Date**: ________________  
**Operator**: ________________  
**Shift**: ☐ Morning ☐ Afternoon ☐ Night

## 🌅 Start of Shift (First 30 minutes)

### System Health
- [ ] Check Grafana dashboard for overnight alerts
- [ ] Verify all core services are running:
  - [ ] DEAN Orchestrator (`docker ps | grep orchestrator`)
  - [ ] PostgreSQL (`docker ps | grep postgres`)
  - [ ] Redis (`docker ps | grep redis`)
  - [ ] Nginx (`docker ps | grep nginx`)
- [ ] Review error logs from last 12 hours
- [ ] Check disk space > 20% free (`df -h`)
- [ ] Verify backup completed successfully

### Performance Metrics
- [ ] CPU usage < 70% (`docker stats`)
- [ ] Memory usage < 80%
- [ ] Response time < 500ms (Grafana)
- [ ] Error rate < 0.1%
- [ ] Database connections < 80%

### Communication
- [ ] Check email for alerts/issues
- [ ] Review Slack channels
- [ ] Update team on any overnight incidents

## 📊 Hourly Checks

### Hour: _____ 
- [ ] Health endpoint responding (`curl http://localhost:8082/health`)
- [ ] No critical alerts in Alertmanager
- [ ] Request rate normal (compare to baseline)
- [ ] No stuck database queries
- [ ] Log errors < 5 in last hour

### Hour: _____
- [ ] Health endpoint responding
- [ ] No critical alerts in Alertmanager
- [ ] Request rate normal
- [ ] No stuck database queries
- [ ] Log errors < 5 in last hour

### Hour: _____
- [ ] Health endpoint responding
- [ ] No critical alerts in Alertmanager
- [ ] Request rate normal
- [ ] No stuck database queries
- [ ] Log errors < 5 in last hour

## 🔧 Daily Maintenance Tasks

### Morning Shift (9 AM - 5 PM)
- [ ] Review and acknowledge all alerts
- [ ] Check for security updates
- [ ] Verify SSL certificate expiry > 30 days
- [ ] Test failover procedures (staging only)
- [ ] Update operational documentation if needed

### Afternoon Shift (5 PM - 1 AM)
- [ ] Monitor peak traffic performance
- [ ] Check database slow query log
- [ ] Verify Redis memory usage
- [ ] Review user-reported issues
- [ ] Prepare for overnight batch jobs

### Night Shift (1 AM - 9 AM)
- [ ] Monitor backup execution (2 AM)
- [ ] Check log rotation (3 AM)
- [ ] Verify maintenance scripts
- [ ] Database vacuum if scheduled
- [ ] Prepare morning handover report

## 🚨 Incident Response

### If Alert Triggered
- [ ] Acknowledge within 5 minutes
- [ ] Assess severity (P1/P2/P3/P4)
- [ ] Start incident log
- [ ] Follow runbook for specific alert
- [ ] Notify on-call if P1/P2
- [ ] Update status page

### If Service Down
- [ ] Check container status
- [ ] Review recent changes
- [ ] Attempt restart
- [ ] Check resource limits
- [ ] Escalate if not resolved in 15 min
- [ ] Document actions taken

## 🔄 End of Shift Handover

### System Status Summary
- [ ] All services: ☐ Healthy ☐ Degraded ☐ Down
- [ ] Active incidents: ________________
- [ ] Pending maintenance: ________________
- [ ] Resource usage trends: ________________

### Issues to Monitor
- [ ] List any concerning patterns:
  - _________________________________
  - _________________________________
  - _________________________________

### Actions Taken
- [ ] Document any changes made:
  - _________________________________
  - _________________________________
  - _________________________________

### For Next Shift
- [ ] Priority tasks:
  - _________________________________
  - _________________________________
- [ ] Special instructions:
  - _________________________________
  - _________________________________

## 📝 Quick Reference

### Key Commands
```bash
# Service health
docker ps --format "table {{.Names}}\t{{.Status}}"
curl http://localhost:8082/health

# Logs
docker logs dean-orchestrator --tail 100
docker logs dean-orchestrator --since 1h | grep ERROR

# Database
docker exec dean-postgres psql -U dean_prod -c "SELECT count(*) FROM pg_stat_activity;"

# Redis
docker exec dean-redis redis-cli -a $REDIS_PASSWORD INFO stats

# Restart service
docker restart dean-orchestrator
```

### Emergency Contacts
- On-Call: +1-XXX-XXX-XXXX
- Platform Lead: platform@company.com
- Escalation: cto@company.com

### Key URLs
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Health: http://localhost:8082/health
- Metrics: http://localhost:8082/metrics

---

**Signature**: ________________  
**Time Completed**: ________________  
**Next Operator**: ________________