# DEAN Quick Reference Card

## Emergency Procedures

### 🚨 System Down
```bash
# 1. Check service status
docker compose -f docker-compose.prod.yml ps

# 2. Restart all services
docker compose -f docker-compose.prod.yml restart

# 3. Check logs for errors
docker compose -f docker-compose.prod.yml logs --tail=100
```

### 🔐 Security Incident
```bash
# 1. Isolate system
sudo ufw deny 80
sudo ufw deny 443

# 2. Preserve logs
tar -czf /secure/incident_$(date +%Y%m%d_%H%M%S).tar.gz /var/log/dean/

# 3. Reset all secrets
./scripts/security/rotate_all_secrets.sh
```

### 💾 Database Issues
```bash
# Check connections
docker exec postgres-prod psql -U dean -c "SELECT count(*) FROM pg_stat_activity;"

# Kill idle connections
docker exec postgres-prod psql -U dean -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < now() - interval '10 minutes';"

# Emergency restore
./scripts/utilities/restore_database.sh /backups/dean/latest.sql.gz
```

## Most Common Commands

### Service Management
```bash
# Start services
docker compose -f docker-compose.prod.yml up -d

# Stop services  
docker compose -f docker-compose.prod.yml down

# Restart specific service
docker compose -f docker-compose.prod.yml restart orchestrator

# View logs
docker compose -f docker-compose.prod.yml logs -f [service-name]

# Check resource usage
docker stats
```

### Health Checks
```bash
# Quick health check
curl -k https://localhost/health

# Full validation
./scripts/final_validation.sh --production

# Check all endpoints
for port in 8081 8082 8083; do
  echo "Port $port: $(curl -s localhost:$port/health | jq -r .status)"
done
```

### User Management
```bash
# Create admin user
docker exec -it dean-orchestrator python scripts/create_admin.py

# Reset user password
docker exec -it dean-orchestrator python scripts/reset_password.py [username]

# List active sessions
docker exec redis-prod redis-cli keys "session:*" | wc -l
```

### Backup & Restore
```bash
# Manual backup
./scripts/utilities/backup_restore.sh backup

# List backups
ls -la /backups/dean/

# Restore specific backup
./scripts/utilities/backup_restore.sh restore /backups/dean/backup_20240120.tar.gz
```

## Key URLs and Endpoints

| Service | URL | Purpose |
|---------|-----|---------|
| Dashboard | https://your-domain.com | Main interface |
| API Docs | https://your-domain.com/docs | API reference |
| Health Monitor | https://your-domain.com/health.html | System status |
| Metrics | http://localhost:9090 | Prometheus |
| Monitoring | http://localhost:3000 | Grafana |

### API Endpoints
- Authentication: `POST /auth/login`
- List Agents: `GET /api/agents`
- Start Evolution: `POST /api/evolution/start`
- Get Patterns: `GET /api/patterns`
- System Metrics: `GET /api/metrics`

## Troubleshooting Flowchart

```
Service Down?
├─ Yes → Check Docker status
│   ├─ Docker running? → Check specific container logs
│   └─ Docker stopped? → Start Docker service
└─ No → Check specific issue
    ├─ Auth failing? → Check Redis connection
    ├─ Slow response? → Check resource usage
    └─ Errors in app? → Check application logs

Cannot connect to service?
├─ Check firewall: sudo ufw status
├─ Check ports: lsof -i :PORT
├─ Check nginx: docker logs nginx
└─ Check SSL cert: openssl s_client -connect domain:443

High resource usage?
├─ CPU high? → Check active evolution trials
├─ Memory high? → Restart affected service
├─ Disk full? → Clean logs and old backups
└─ Database slow? → Run VACUUM ANALYZE
```

## Contact Information Template

### 🚨 Emergency Contacts

| Priority | Contact | Phone | Available |
|----------|---------|-------|-----------|
| On-Call Engineer | __________ | __________ | 24/7 |
| System Admin | __________ | __________ | 24/7 |
| Database Admin | __________ | __________ | Business |
| Security Team | __________ | __________ | 24/7 |

### 📧 Escalation

1. **Immediate** (System Down): Call on-call engineer
2. **Urgent** (Degraded): Slack #dean-alerts + email
3. **Normal** (Issues): Create ticket + email team

### 🏢 Vendor Support

| Service | Number | Account |
|---------|--------|---------|
| Hosting | _______ | _______ |
| DNS | _______ | _______ |
| SSL | _______ | _______ |

## Quick Diagnostics

### Check Everything Script
```bash
#!/bin/bash
echo "=== DEAN Quick Diagnostics ==="
echo "Services:" && docker compose -f docker-compose.prod.yml ps
echo -e "\nHealth:" && curl -s localhost:8082/health | jq .
echo -e "\nResources:" && docker stats --no-stream
echo -e "\nDisk:" && df -h | grep -E "/$|/var"
echo -e "\nDatabase:" && docker exec postgres-prod psql -U dean -c "SELECT count(*) as connections FROM pg_stat_activity;"
echo -e "\nErrors (last hour):" && grep ERROR /var/log/dean/*.log | grep "$(date +%Y-%m-%d-%H)" | wc -l
```

### Performance Check
```bash
# API response time
time curl -s https://localhost/api/agents > /dev/null

# Database query time
docker exec postgres-prod psql -U dean -c "\timing" -c "SELECT COUNT(*) FROM agents;"

# Redis latency
docker exec redis-prod redis-cli --latency
```

## Critical Files

```
/opt/dean/
├── .env                    # Main configuration
├── docker-compose.prod.yml # Production setup
├── logs/                   # Application logs
├── certs/                  # SSL certificates
├── backups/                # Database backups
└── scripts/
    ├── health_check.sh     # Health verification
    ├── backup_restore.sh   # Backup management
    └── security_audit.py   # Security check
```

## Log Locations

- Application: `/var/log/dean/*.log`
- Docker: `docker logs [container-name]`
- System: `/var/log/syslog`
- Auth: `/var/log/auth.log`
- Nginx: `/var/log/nginx/`

## Quick Fixes

### Reset Everything
```bash
# WARNING: This will delete all data!
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d
```

### Clear Cache
```bash
docker exec redis-prod redis-cli FLUSHDB
```

### Restart After Config Change
```bash
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

### Emergency Maintenance Mode
```bash
# Create maintenance.html in nginx root
echo "<h1>System Maintenance - Back Soon</h1>" > /var/www/maintenance.html

# Update nginx to serve maintenance page
# Then restart nginx
```

---

**Remember**: 
- Always backup before major changes
- Test commands in dev first when possible  
- Document any permanent fixes
- Update contacts when personnel change

**Keep this card handy for quick reference during operations!**