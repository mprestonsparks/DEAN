#!/bin/bash

# DEAN Production Hardening Script
# Implements security best practices for production deployment

set -e

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DEAN_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/dean/hardening_$(date +%Y%m%d_%H%M%S).log"
BACKUP_DIR="/backups/dean/pre-hardening"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Ensure running as root
if [ "$EUID" -ne 0 ]; then 
    echo "This script must be run as root for system hardening"
    exit 1
fi

# Start logging
mkdir -p "$(dirname "$LOG_FILE")"
exec > >(tee -a "$LOG_FILE")
exec 2>&1

echo "================================================"
echo "DEAN Production Hardening Script"
echo "================================================"
echo "Date: $(date)"
echo "System: $(uname -a)"
echo ""

# Function to log actions
log_action() {
    echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1"
}

# Function to log success
log_success() {
    echo -e "${GREEN}[$(date +%H:%M:%S)] ✓${NC} $1"
}

# Function to log warning
log_warning() {
    echo -e "${YELLOW}[$(date +%H:%M:%S)] ⚠${NC} $1"
}

# Function to log error
log_error() {
    echo -e "${RED}[$(date +%H:%M:%S)] ✗${NC} $1"
}

# Backup current configuration
log_action "Creating backup of current configuration..."
mkdir -p "$BACKUP_DIR"
cp -r "$DEAN_ROOT/.env" "$BACKUP_DIR/.env.backup" 2>/dev/null || true
cp -r "$DEAN_ROOT/configs" "$BACKUP_DIR/configs.backup" 2>/dev/null || true
log_success "Backup created at $BACKUP_DIR"

# 1. Remove Default Accounts
log_action "Removing default accounts..."

# Check for default admin account
if docker exec postgres-prod psql -U dean -d dean_production -t -c "SELECT 1 FROM users WHERE username='admin' AND password_hash='\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewYpfQeUjrktKBJ2'" | grep -q 1; then
    log_warning "Default admin account detected - will be disabled"
    docker exec postgres-prod psql -U dean -d dean_production -c "UPDATE users SET is_active=false WHERE username='admin';"
    log_success "Default admin account disabled"
else
    log_success "No default admin account found"
fi

# Remove test users
docker exec postgres-prod psql -U dean -d dean_production -c "DELETE FROM users WHERE username LIKE 'test%' OR username LIKE 'demo%';"
log_success "Test accounts removed"

# 2. Enforce Strong Password Policies
log_action "Configuring password policies..."

# Create password policy configuration
cat > "$DEAN_ROOT/configs/password_policy.json" << EOF
{
  "min_length": 12,
  "require_uppercase": true,
  "require_lowercase": true,
  "require_numbers": true,
  "require_special": true,
  "password_history": 5,
  "max_age_days": 90,
  "min_age_days": 1,
  "max_failed_attempts": 5,
  "lockout_duration_minutes": 30
}
EOF

log_success "Password policy configured"

# 3. Configure Fail2ban
log_action "Setting up Fail2ban..."

# Install fail2ban if not present
if ! command -v fail2ban-client &> /dev/null; then
    apt-get update && apt-get install -y fail2ban
fi

# Create DEAN filter
cat > /etc/fail2ban/filter.d/dean.conf << EOF
[Definition]
failregex = ^.*Failed login attempt.*from <HOST>.*$
            ^.*Invalid token.*from <HOST>.*$
            ^.*Unauthorized access.*from <HOST>.*$
            ^.*Rate limit exceeded.*from <HOST>.*$
ignoreregex =
EOF

# Create DEAN jail
cat > /etc/fail2ban/jail.d/dean.local << EOF
[dean-auth]
enabled = true
port = 80,443,8082
filter = dean
logpath = /var/log/dean/auth.log
maxretry = 5
findtime = 600
bantime = 3600
action = iptables-multiport[name=dean, port="80,443,8082", protocol=tcp]

[dean-api]
enabled = true
port = 80,443,8082
filter = dean
logpath = /var/log/dean/api.log
maxretry = 50
findtime = 60
bantime = 600
action = iptables-multiport[name=dean-api, port="80,443,8082", protocol=tcp]
EOF

# Restart fail2ban
systemctl restart fail2ban
log_success "Fail2ban configured and started"

# 4. Set Up Audit Logging
log_action "Configuring audit logging..."

# Install auditd if not present
if ! command -v auditctl &> /dev/null; then
    apt-get install -y auditd audispd-plugins
fi

# Configure audit rules
cat > /etc/audit/rules.d/dean.rules << EOF
# Monitor DEAN configuration changes
-w /opt/dean -p wa -k dean_changes
-w /opt/dean/.env -p wa -k dean_config
-w /opt/dean/configs -p wa -k dean_config

# Monitor authentication
-w /var/log/dean/auth.log -p wa -k dean_auth

# Monitor database access
-w /var/lib/postgresql -p wa -k dean_database

# Monitor Docker actions
-w /usr/bin/docker -p x -k docker_commands
-w /var/lib/docker -p wa -k docker_changes

# System calls
-a always,exit -F arch=b64 -S execve -F uid=dean -k dean_commands
EOF

# Restart auditd
service auditd restart
log_success "Audit logging configured"

# 5. Harden Docker Configuration
log_action "Hardening Docker configuration..."

# Create Docker daemon configuration
cat > /etc/docker/daemon.json << EOF
{
  "icc": false,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "userland-proxy": false,
  "no-new-privileges": true,
  "seccomp-profile": "/etc/docker/seccomp/default.json",
  "userns-remap": "default"
}
EOF

# Set Docker socket permissions
chmod 660 /var/run/docker.sock

# Create Docker seccomp profile
mkdir -p /etc/docker/seccomp
cp /usr/share/docker/seccomp/default.json /etc/docker/seccomp/default.json

# Restart Docker
systemctl restart docker
log_success "Docker hardened"

# 6. Network Segmentation
log_action "Implementing network segmentation..."

# Create isolated Docker networks
docker network create --driver bridge --opt encrypted dean-frontend 2>/dev/null || true
docker network create --driver bridge --opt encrypted dean-backend 2>/dev/null || true
docker network create --driver bridge --opt encrypted dean-data 2>/dev/null || true

log_success "Docker networks created"

# Configure iptables rules
iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -j DROP

# Save iptables rules
iptables-save > /etc/iptables/rules.v4
log_success "Firewall rules configured"

# 7. File System Hardening
log_action "Hardening file system..."

# Set secure permissions
chmod 700 "$DEAN_ROOT"
chmod 600 "$DEAN_ROOT/.env"
chmod 700 "$DEAN_ROOT/certs"
chmod 600 "$DEAN_ROOT/certs/*" 2>/dev/null || true
chmod 700 "$DEAN_ROOT/backups"
chmod 700 /var/log/dean

# Set ownership
chown -R dean:dean "$DEAN_ROOT"
chown -R dean:dean /var/log/dean

# Enable file integrity monitoring
cat > /etc/aide/aide.conf.d/dean << EOF
/opt/dean/configs R
/opt/dean/.env R
/opt/dean/certs R
/opt/dean/scripts R
EOF

# Initialize AIDE database
aideinit
cp /var/lib/aide/aide.db.new /var/lib/aide/aide.db
log_success "File system hardened"

# 8. SSL/TLS Configuration
log_action "Hardening SSL/TLS configuration..."

# Generate strong DH parameters
openssl dhparam -out "$DEAN_ROOT/certs/dhparam.pem" 2048

# Update Nginx SSL configuration
cat > "$DEAN_ROOT/nginx/ssl-hardened.conf" << 'EOF'
# SSL Configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
ssl_dhparam /etc/nginx/dhparam.pem;

# SSL Session
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_session_tickets off;

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;

# Security Headers
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self' https:; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' https: wss:; media-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none';" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
EOF

log_success "SSL/TLS configuration hardened"

# 9. Secrets Management
log_action "Securing secrets management..."

# Rotate all secrets
JWT_SECRET=$(openssl rand -base64 64)
DB_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 24)
AIRFLOW_PASSWORD=$(openssl rand -base64 24)

# Update .env with new secrets
sed -i.bak "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_SECRET/" "$DEAN_ROOT/.env"
sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$DB_PASSWORD/" "$DEAN_ROOT/.env"
sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=$REDIS_PASSWORD/" "$DEAN_ROOT/.env"
sed -i "s/AIRFLOW_PASSWORD=.*/AIRFLOW_PASSWORD=$AIRFLOW_PASSWORD/" "$DEAN_ROOT/.env"

log_warning "All secrets have been rotated - services will need to be restarted"

# 10. Kernel Hardening
log_action "Applying kernel hardening..."

# Kernel parameters for security
cat > /etc/sysctl.d/99-dean-security.conf << EOF
# IP Spoofing protection
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Ignore ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0

# Ignore send redirects
net.ipv4.conf.all.send_redirects = 0

# Disable source packet routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0

# Log Martians
net.ipv4.conf.all.log_martians = 1

# Ignore ICMP ping requests
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Ignore Directed pings
net.ipv4.icmp_ignore_bogus_error_responses = 1

# Enable TCP/IP SYN cookies
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2
net.ipv4.tcp_syn_retries = 5

# Disable IPv6 if not needed
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
net.ipv6.conf.lo.disable_ipv6 = 1

# File system hardening
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
fs.suid_dumpable = 0

# Process hardening
kernel.randomize_va_space = 2
kernel.yama.ptrace_scope = 1
EOF

# Apply sysctl settings
sysctl -p /etc/sysctl.d/99-dean-security.conf
log_success "Kernel parameters hardened"

# 11. Service Hardening
log_action "Hardening system services..."

# Disable unnecessary services
systemctl disable avahi-daemon 2>/dev/null || true
systemctl disable cups 2>/dev/null || true
systemctl disable rpcbind 2>/dev/null || true

# Configure systemd security for DEAN
cat > /etc/systemd/system/dean-orchestrator.service << EOF
[Unit]
Description=DEAN Orchestrator Service
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=dean
Group=dean
WorkingDirectory=/opt/dean
ExecStart=/usr/bin/docker-compose -f docker-compose.prod.yml up
ExecStop=/usr/bin/docker-compose -f docker-compose.prod.yml down
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/dean /var/log/dean
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictRealtime=true
RestrictNamespaces=true
RestrictSUIDSGID=true
MemoryDenyWriteExecute=true
LockPersonality=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
log_success "System services hardened"

# 12. Monitoring and Alerting
log_action "Setting up security monitoring..."

# Create security monitoring script
cat > "$DEAN_ROOT/scripts/security_monitor.sh" << 'EOF'
#!/bin/bash

# Security monitoring script
LOG_FILE="/var/log/dean/security_monitor.log"

# Check for suspicious activity
check_failed_logins() {
    FAILED_COUNT=$(grep "Failed login" /var/log/dean/auth.log | grep "$(date +%Y-%m-%d)" | wc -l)
    if [ $FAILED_COUNT -gt 100 ]; then
        echo "[ALERT] High number of failed logins: $FAILED_COUNT" >> "$LOG_FILE"
    fi
}

# Check for unauthorized file changes
check_file_integrity() {
    aide --check | grep -E "Added|Removed|Changed" >> "$LOG_FILE"
}

# Check for unusual processes
check_processes() {
    ps aux | grep -E "nc |ncat |netcat |socat " >> "$LOG_FILE"
}

# Run checks
check_failed_logins
check_file_integrity
check_processes
EOF

chmod +x "$DEAN_ROOT/scripts/security_monitor.sh"

# Add to crontab
echo "*/15 * * * * $DEAN_ROOT/scripts/security_monitor.sh" | crontab -

log_success "Security monitoring configured"

# Final Report
echo ""
echo "================================================"
echo "Production Hardening Complete"
echo "================================================"
echo ""
echo -e "${GREEN}Completed Tasks:${NC}"
echo "✓ Default accounts removed/disabled"
echo "✓ Password policies enforced"
echo "✓ Fail2ban configured"
echo "✓ Audit logging enabled"
echo "✓ Docker hardened"
echo "✓ Network segmentation implemented"
echo "✓ File system permissions secured"
echo "✓ SSL/TLS configuration hardened"
echo "✓ Secrets rotated"
echo "✓ Kernel parameters hardened"
echo "✓ System services hardened"
echo "✓ Security monitoring enabled"
echo ""
echo -e "${YELLOW}Required Actions:${NC}"
echo "1. Restart all DEAN services to apply new secrets"
echo "2. Create new admin account to replace default"
echo "3. Update application configuration with new passwords"
echo "4. Test all functionality after restart"
echo "5. Review security monitoring logs daily"
echo ""
echo -e "${BLUE}Security Recommendations:${NC}"
echo "- Enable SELinux or AppArmor for additional protection"
echo "- Implement regular security scanning"
echo "- Configure centralized logging"
echo "- Set up intrusion detection system (IDS)"
echo "- Schedule regular security audits"
echo ""
echo "Hardening log saved to: $LOG_FILE"
echo ""

# Create summary report
cat > "$DEAN_ROOT/HARDENING_SUMMARY.md" << EOF
# DEAN Production Hardening Summary

**Date**: $(date)
**Script Version**: 1.0.0

## Applied Security Measures

### Account Security
- Default admin account disabled
- Test/demo accounts removed
- Strong password policy enforced (12+ chars, complexity requirements)
- Account lockout after 5 failed attempts

### Network Security
- Fail2ban configured with custom DEAN rules
- Firewall rules implemented (iptables)
- Docker network isolation enabled
- SSL/TLS hardened (TLS 1.2+ only)

### System Security
- Audit logging enabled (auditd)
- File integrity monitoring (AIDE)
- Kernel parameters hardened
- Unnecessary services disabled

### Application Security
- All secrets rotated
- Docker daemon hardened
- File permissions secured
- Security monitoring enabled

## New Credentials

**IMPORTANT**: New secrets have been generated and stored in .env file.
You must restart all services and update any external configurations.

## Post-Hardening Checklist

- [ ] Restart all DEAN services
- [ ] Create new admin account
- [ ] Test authentication with new credentials
- [ ] Verify all services are operational
- [ ] Review security logs
- [ ] Document any custom configurations

## Monitoring

Security monitoring script runs every 15 minutes.
Check logs at: /var/log/dean/security_monitor.log

## Support

For issues related to hardening, check:
1. Hardening log: $LOG_FILE
2. Backup configuration: $BACKUP_DIR
3. Security monitor: /var/log/dean/security_monitor.log
EOF

exit 0