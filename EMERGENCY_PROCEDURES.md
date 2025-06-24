# DEAN Emergency Response Procedures

**⚠️ FOR CRITICAL INCIDENTS ONLY ⚠️**

## 🚨 System Complete Outage

### Immediate Actions (First 5 minutes)
1. **VERIFY** the outage
   ```powershell
   curl http://localhost:8082/health
   curl http://localhost/health
   ping localhost
   ```

2. **ASSESS** scope
   - Check all containers: `docker ps -a`
   - Check host resources: `Get-Process | Sort-Object CPU -Descending | Select-Object -First 10`
   - Check disk space: `Get-PSDrive`

3. **COMMUNICATE**
   - Update status page: "Investigating issues with DEAN system"
   - Notify on-call: +1-XXX-XXX-XXXX
   - Post in #incidents channel

### Recovery Actions (5-15 minutes)
```powershell
# 1. Try graceful restart
docker-compose -f docker-compose.prod.yml restart

# 2. If failed, force restart
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# 3. If still failed, check Docker daemon
Restart-Service docker
Start-Sleep -Seconds 30
docker-compose -f docker-compose.prod.yml up -d

# 4. Verify recovery
.\scripts\verify_deployment.ps1
```

### If Not Recovered (15+ minutes)
1. **ESCALATE** to Platform Lead
2. **PREPARE** for rollback
3. **GATHER** diagnostics:
   ```powershell
   # Save all logs
   docker logs dean-orchestrator > outage_orchestrator.log 2>&1
   docker logs dean-postgres > outage_postgres.log 2>&1
   docker logs dean-redis > outage_redis.log 2>&1
   docker logs dean-nginx > outage_nginx.log 2>&1
   
   # System state
   docker ps -a > outage_containers.txt
   docker network ls > outage_networks.txt
   Get-EventLog -LogName Application -Newest 100 > outage_events.txt
   ```

## 💾 Database Emergency

### Connection Pool Exhausted
```powershell
# 1. Check active connections
docker exec dean-postgres psql -U dean_prod -d dean_production -c "
SELECT count(*), state 
FROM pg_stat_activity 
GROUP BY state;"

# 2. Kill idle connections
docker exec dean-postgres psql -U dean_prod -d dean_production -c "
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' 
AND state_change < now() - interval '5 minutes';"

# 3. Increase connection limit (temporary)
docker exec dean-postgres psql -U dean_prod -c "
ALTER SYSTEM SET max_connections = 200;"
docker restart dean-postgres
```

### Database Corruption
```powershell
# 1. Stop application
docker stop dean-orchestrator

# 2. Backup current state
docker exec dean-postgres pg_dump -U dean_prod dean_production > emergency_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql

# 3. Check database
docker exec dean-postgres psql -U dean_prod -d dean_production -c "VACUUM FULL ANALYZE;"

# 4. If corruption persists, restore from backup
$latestBackup = Get-ChildItem -Path backups -Filter "*.sql" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
cat $latestBackup.FullName | docker exec -i dean-postgres psql -U dean_prod dean_production
```

## 🔴 Redis Failure

### Memory Exhaustion
```powershell
# 1. Check memory usage
docker exec dean-redis redis-cli -a $env:REDIS_PASSWORD INFO memory

# 2. Clear cache (DATA LOSS WARNING)
docker exec dean-redis redis-cli -a $env:REDIS_PASSWORD FLUSHDB

# 3. Restart with increased memory
docker update --memory 2g dean-redis
docker restart dean-redis
```

### Authentication Failure
```powershell
# 1. Verify password
$redisPass = (Get-Content .env | Select-String "REDIS_PASSWORD" | ForEach-Object { $_.ToString().Split('=')[1] })

# 2. Test connection
docker exec dean-redis redis-cli -a $redisPass ping

# 3. If failed, restart without auth (TEMPORARY)
docker exec dean-redis redis-cli CONFIG SET requirepass ""
# Update orchestrator to connect without password
# Fix and re-enable auth ASAP
```

## 🌐 Network Issues

### Container Network Lost
```powershell
# 1. Check network
docker network inspect dean_dean-net

# 2. Reconnect containers
$containers = @("dean-orchestrator", "dean-postgres", "dean-redis", "dean-nginx")
foreach ($container in $containers) {
    docker network disconnect dean_dean-net $container
    docker network connect dean_dean-net $container
}

# 3. If network corrupted, recreate
docker-compose -f docker-compose.prod.yml down
docker network prune -f
docker-compose -f docker-compose.prod.yml up -d
```

## 🔥 Disk Space Emergency

### Immediate Space Recovery
```powershell
# 1. Check what's using space
Get-ChildItem -Path C:\ -Recurse -ErrorAction SilentlyContinue | 
    Where-Object { $_.Length -gt 100MB } | 
    Sort-Object Length -Descending | 
    Select-Object FullName, @{Name="SizeMB";Expression={[Math]::Round($_.Length / 1MB, 2)}} -First 20

# 2. Clean Docker
docker system prune -a -f --volumes

# 3. Truncate logs
docker exec dean-orchestrator sh -c "echo '' > /var/log/dean.log"

# 4. Remove old backups (keep last 3)
Get-ChildItem -Path backups -Filter "*.sql" | 
    Sort-Object LastWriteTime -Descending | 
    Select-Object -Skip 3 | 
    Remove-Item -Force
```

## 🔐 Security Breach

### Suspected Compromise
1. **ISOLATE** immediately
   ```powershell
   # Block external access
   netsh advfirewall firewall add rule name="EMERGENCY_BLOCK" dir=in action=block protocol=TCP localport=80,443
   ```

2. **PRESERVE** evidence
   ```powershell
   # Snapshot logs
   $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
   mkdir "security_incident_$timestamp"
   docker logs dean-orchestrator > "security_incident_$timestamp/orchestrator.log" 2>&1
   docker logs dean-nginx > "security_incident_$timestamp/nginx.log" 2>&1
   ```

3. **NOTIFY**
   - Security team: security@company.com
   - CTO immediately
   - Legal if data breach suspected

4. **CONTAIN**
   ```powershell
   # Rotate all credentials
   .\scripts\emergency_credential_rotation.ps1
   
   # Revoke all active sessions
   docker exec dean-redis redis-cli -a $env:REDIS_PASSWORD FLUSHALL
   ```

## 📋 Post-Incident

### Required Actions
1. **Document timeline** in incident report
2. **Conduct RCA** within 24 hours
3. **Update runbooks** with lessons learned
4. **Test fixes** in staging
5. **Schedule retrospective** within 1 week

### Incident Report Template
```
Incident ID: INC-YYYYMMDD-XXX
Date/Time: 
Duration: 
Severity: P1/P2/P3/P4
Impact: 

Timeline:
- HH:MM - Event description
- HH:MM - Action taken
- HH:MM - Result

Root Cause:

Resolution:

Prevention:

Action Items:
- [ ] Task 1 - Owner - Due date
- [ ] Task 2 - Owner - Due date
```

## 📞 Emergency Contacts

### Immediate Escalation
1. **On-Call Engineer**: +1-XXX-XXX-XXXX
2. **Platform Lead**: +1-XXX-XXX-XXXX (after hours)
3. **CTO**: +1-XXX-XXX-XXXX (P1 only)

### Vendor Support
- **Cloud Provider**: 1-800-XXX-XXXX (Account: XXX)
- **Docker Support**: support@docker.com (Ticket: XXX)
- **Security Team**: soc@company.com (24/7)

### Communication Channels
- **Status Page**: https://status.company.com
- **Incident Slack**: #incidents
- **War Room**: #war-room-dean
- **Customer Comms**: customer-success@company.com

---

**Remember**: 
- Stay calm
- Communicate frequently
- Document everything
- Ask for help early
- Learn from incidents

**Last Updated**: January 19, 2025  
**Next Review**: Monthly