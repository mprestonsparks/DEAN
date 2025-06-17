# DEAN Production Launch Checklist

This comprehensive checklist ensures your DEAN deployment is production-ready, secure, and properly configured.

## Pre-Deployment Requirements

### Hardware Verification
- [ ] **CPU**: Intel i7 or equivalent (8+ cores verified)
- [ ] **RAM**: 32GB available (16GB minimum)
- [ ] **Storage**: 100GB+ free space on SSD
- [ ] **GPU**: NVIDIA RTX 3080 or equivalent (if using GPU acceleration)
- [ ] **Network**: Stable internet connection with static IP

### Software Prerequisites
- [ ] **Docker**: Version 20.10+ installed and running
- [ ] **Docker Compose**: Version 2.0+ installed
- [ ] **Python**: Version 3.10+ installed
- [ ] **Git**: Latest version (for updates)
- [ ] **SSL Certificates**: Valid certificates for HTTPS

### System Preparation
- [ ] All system updates applied
- [ ] Firewall configured (see Security section)
- [ ] Backup solution in place
- [ ] Monitoring tools ready
- [ ] DNS records configured (if using custom domain)

## Security Configuration

### Authentication & Access
- [ ] **Change ALL default passwords**
  ```bash
  # Critical passwords to change:
  - Admin user password (default: admin123)
  - Database password (in .env)
  - Redis password (in .env)
  - Airflow password (in .env)
  ```

- [ ] **Generate new JWT secret**
  ```bash
  openssl rand -base64 64
  # Update JWT_SECRET_KEY in .env
  ```

- [ ] **Configure allowed origins**
  ```bash
  # Update ALLOWED_ORIGINS in .env
  # Only include your actual domains
  ```

- [ ] **Create production admin account**
  ```bash
  # Delete default admin after creating new one
  ./scripts/manage_users.sh create-admin
  ```

### Network Security
- [ ] **Configure firewall rules**
  ```bash
  # Allow only necessary ports
  sudo ufw allow 22/tcp    # SSH
  sudo ufw allow 443/tcp   # HTTPS
  sudo ufw allow 80/tcp    # HTTP (redirect only)
  sudo ufw enable
  ```

- [ ] **Enable HTTPS**
  - [ ] Install SSL certificates
  - [ ] Configure Nginx reverse proxy
  - [ ] Set ENFORCE_HTTPS=true in .env
  - [ ] Test SSL configuration

- [ ] **Restrict service exposure**
  ```bash
  # Ensure services only bind to localhost
  # Check docker-compose.yml port bindings
  ```

### Data Protection
- [ ] **Secure file permissions**
  ```bash
  chmod 600 .env
  chmod 600 certs/*
  chmod 700 backups/
  ```

- [ ] **Enable database encryption**
  - [ ] Configure PostgreSQL SSL
  - [ ] Enable Redis password auth
  - [ ] Set up encrypted backups

- [ ] **Configure secure cookies**
  ```bash
  # In .env:
  SESSION_COOKIE_SECURE=true
  SESSION_COOKIE_HTTPONLY=true
  SESSION_COOKIE_SAMESITE=strict
  ```

## Performance Tuning

### Resource Allocation
- [ ] **Docker resource limits**
  ```yaml
  # In docker-compose.yml:
  services:
    orchestrator:
      deploy:
        resources:
          limits:
            cpus: '4'
            memory: 8G
  ```

- [ ] **Database optimization**
  ```bash
  # PostgreSQL tuning
  - shared_buffers = 4GB
  - effective_cache_size = 12GB
  - maintenance_work_mem = 1GB
  ```

- [ ] **Configure worker processes**
  ```bash
  # In .env:
  MAX_WORKERS=8  # Based on CPU cores
  UVICORN_WORKERS=4
  ```

### Caching Configuration
- [ ] **Redis memory limit**
  ```bash
  # redis.conf:
  maxmemory 4gb
  maxmemory-policy allkeys-lru
  ```

- [ ] **API response caching**
  - [ ] Enable caching headers
  - [ ] Configure CDN if applicable

## Monitoring Setup

### System Monitoring
- [ ] **Install Prometheus**
  ```bash
  docker run -d --name prometheus \
    -p 9090:9090 \
    -v /path/to/prometheus.yml:/etc/prometheus/prometheus.yml \
    prom/prometheus
  ```

- [ ] **Configure Grafana dashboards**
  - [ ] Import DEAN dashboard templates
  - [ ] Set up alerts for critical metrics
  - [ ] Configure notification channels

### Application Monitoring
- [ ] **Enable detailed logging**
  ```bash
  # In .env:
  LOG_LEVEL=INFO
  ENABLE_ACCESS_LOGS=true
  ```

- [ ] **Set up log aggregation**
  - [ ] Configure log rotation
  - [ ] Set up ELK stack or similar
  - [ ] Create log parsing rules

- [ ] **Configure health checks**
  ```bash
  # Add to monitoring system:
  - http://your-domain/health
  - http://your-domain/api/metrics
  ```

### Alerting Rules
- [ ] **Critical alerts configured**
  - [ ] Service down > 1 minute
  - [ ] API response time > 2 seconds
  - [ ] Memory usage > 80%
  - [ ] Disk space < 20%
  - [ ] Failed login attempts > 10/minute

## Backup Configuration

### Automated Backups
- [ ] **Database backups**
  ```bash
  # Create backup script
  0 2 * * * /opt/dean/scripts/backup_database.sh
  ```

- [ ] **Configuration backups**
  - [ ] Version control for configs
  - [ ] Backup .env file securely
  - [ ] Document all customizations

- [ ] **Data retention policy**
  - [ ] Daily backups: Keep 7 days
  - [ ] Weekly backups: Keep 4 weeks
  - [ ] Monthly backups: Keep 12 months

### Disaster Recovery
- [ ] **Test restore procedure**
  ```bash
  ./scripts/utilities/backup_restore.sh test-restore
  ```

- [ ] **Document recovery steps**
  - [ ] Create runbook for failures
  - [ ] Test failover procedures
  - [ ] Verify backup integrity

## Post-Deployment Verification

### Functional Testing
- [ ] **Run validation script**
  ```bash
  ./scripts/final_validation.sh
  # All checks should pass
  ```

- [ ] **Test core workflows**
  - [ ] User authentication
  - [ ] Agent creation
  - [ ] Evolution trial execution
  - [ ] Pattern discovery
  - [ ] API endpoints

- [ ] **Performance validation**
  ```bash
  ./scripts/performance_test.py
  # Verify meets requirements
  ```

### Security Validation
- [ ] **Run security audit**
  ```bash
  ./scripts/security_audit.py
  # Address all critical issues
  ```

- [ ] **Penetration testing**
  - [ ] Test authentication bypass
  - [ ] Check for SQL injection
  - [ ] Verify CSRF protection
  - [ ] Test rate limiting

### User Acceptance
- [ ] **Documentation review**
  - [ ] User guides updated
  - [ ] API documentation current
  - [ ] Admin procedures documented

- [ ] **Training completed**
  - [ ] Admin users trained
  - [ ] Support team briefed
  - [ ] Runbooks created

## Production Launch

### Go-Live Steps
1. [ ] **Final backup before launch**
2. [ ] **Enable production mode**
   ```bash
   # In .env:
   DEAN_ENV=production
   DEBUG=false
   ```

3. [ ] **Start services**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. [ ] **Verify all services healthy**
   ```bash
   ./scripts/health_check.sh --production
   ```

5. [ ] **Enable monitoring alerts**
6. [ ] **Update DNS records** (if applicable)
7. [ ] **Announce go-live** to stakeholders

### Post-Launch Monitoring (First 24 Hours)
- [ ] Check system metrics every hour
- [ ] Review error logs
- [ ] Monitor user activity
- [ ] Check backup completion
- [ ] Verify no security alerts

## Rollback Procedures

### If Issues Occur
1. [ ] **Assess severity** (Critical/High/Medium/Low)
2. [ ] **Capture diagnostics**
   ```bash
   ./scripts/capture_diagnostics.sh
   ```

3. [ ] **Execute rollback if needed**
   ```bash
   ./scripts/deploy/rollback.sh
   ```

4. [ ] **Notify stakeholders**
5. [ ] **Document issues** for post-mortem

### Post-Incident
- [ ] Root cause analysis
- [ ] Update procedures
- [ ] Test fixes in staging
- [ ] Schedule maintenance window

## Sign-Off

### Launch Approval
- [ ] **Technical Lead**: _________________ Date: _______
- [ ] **Security Lead**: _________________ Date: _______
- [ ] **Operations Lead**: _______________ Date: _______
- [ ] **Project Manager**: _______________ Date: _______

### Notes
_Use this space for any deployment-specific notes or concerns:_

---

**Remember**: A successful launch is not about speed, but about thoroughness. Take time to verify each step.

**Emergency Contacts**:
- Technical Support: _______________
- Security Team: __________________
- Database Admin: _________________
- Network Admin: __________________