# DEAN PKI Operations Guide

## Overview

This guide covers the Public Key Infrastructure (PKI) operations for the DEAN system, including certificate management, mTLS configuration, and troubleshooting procedures.

## PKI Hierarchy

```
DEAN Root CA (10 years)
├── Validity: 2025-2035
├── Key: RSA 4096-bit
├── Usage: Certificate signing only
└── Storage: Infisical /dean/pki/ca/ROOT_CA_*

    └── DEAN Services CA (5 years)
        ├── Validity: 2025-2030
        ├── Key: RSA 4096-bit
        ├── Usage: Issue service certificates
        └── Storage: Infisical /dean/pki/ca/INTERMEDIATE_CA_*

            ├── dean-orchestration.dean.local (1 year, auto-renew)
            ├── indexagent.dean.local (1 year, auto-renew)
            ├── evolution-api.dean.local (1 year, auto-renew)
            ├── airflow-webserver.dean.local (1 year, auto-renew)
            ├── prometheus.dean.local (1 year, auto-renew)
            └── grafana.dean.local (1 year, auto-renew)
```

## Certificate Management

### Viewing Certificates

#### Check Certificate Details

```bash
# View certificate information
openssl x509 -in dean-ca-bundle.pem -text -noout

# Check certificate validity
openssl x509 -in dean-ca-bundle.pem -noout -dates

# Verify certificate chain
openssl verify -CAfile dean-ca-bundle.pem service-cert.pem
```

#### List All Certificates

```bash
# Using Infisical CLI
infisical secrets --env=production --path=/dean/pki/services

# Check expiration dates
for service in dean-orchestration indexagent evolution-api; do
    echo "=== $service ==="
    infisical secrets get TLS_CERT --env=production --path=/dean/pki/services/$service | \
    openssl x509 -noout -dates
done
```

### Certificate Renewal

#### Automatic Renewal

Certificates are automatically renewed 30 days before expiration:

```python
# Renewal check runs daily via cron
0 2 * * * /usr/local/bin/dean-cert-renewal.sh
```

#### Manual Renewal

```bash
# 1. Generate new certificate
cd /path/to/dean/scripts
python3 renew_service_certificate.py --service dean-orchestration

# 2. Update in Infisical
infisical secrets set TLS_CERT="$(cat new-cert.pem)" \
  --env=production \
  --path=/dean/pki/services/dean-orchestration \
  --override

infisical secrets set TLS_KEY="$(cat new-key.pem)" \
  --env=production \
  --path=/dean/pki/services/dean-orchestration \
  --override

# 3. Restart service
docker-compose restart dean-orchestration

# 4. Verify
openssl s_client -connect localhost:8082 -servername dean-orchestration.dean.local
```

### Certificate Revocation

#### Revoke Compromised Certificate

```bash
# 1. Generate revocation entry
cat > revoke.conf << EOF
[ ca ]
default_ca = CA_default

[ CA_default ]
database = /etc/pki/index.txt
serial = /etc/pki/serial
crlnumber = /etc/pki/crlnumber
crl = /etc/pki/crl.pem
EOF

# 2. Revoke certificate
openssl ca -config revoke.conf -revoke compromised-cert.pem -crl_reason keyCompromise

# 3. Generate new CRL
openssl ca -config revoke.conf -gencrl -out crl.pem

# 4. Distribute CRL to all services
# Update in Infisical
infisical secrets set CRL="$(cat crl.pem)" \
  --env=production \
  --path=/dean/pki/ca \
  --override

# 5. Issue new certificate immediately
```

## mTLS Configuration

### Enabling mTLS

#### Service Configuration

```python
# Python service with mTLS
import ssl
import requests

# Create SSL context
context = ssl.create_default_context()
context.load_cert_chain(
    certfile="/run/secrets/service-cert.pem",
    keyfile="/run/secrets/service-key.pem"
)
context.load_verify_locations("/run/secrets/ca-bundle.pem")
context.verify_mode = ssl.CERT_REQUIRED

# Make mTLS request
session = requests.Session()
session.mount('https://', requests.adapters.HTTPAdapter())
session.verify = "/run/secrets/ca-bundle.pem"
session.cert = ("/run/secrets/service-cert.pem", "/run/secrets/service-key.pem")

response = session.get("https://other-service.dean.local:8443/api/data")
```

#### Nginx Configuration

```nginx
# nginx.conf for mTLS
server {
    listen 443 ssl;
    server_name dean-orchestration.dean.local;
    
    # Server certificate
    ssl_certificate /etc/nginx/certs/server-cert.pem;
    ssl_certificate_key /etc/nginx/certs/server-key.pem;
    
    # Client certificate verification
    ssl_client_certificate /etc/nginx/certs/ca-bundle.pem;
    ssl_verify_client on;
    ssl_verify_depth 2;
    
    # TLS configuration
    ssl_protocols TLSv1.3;
    ssl_ciphers 'TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256';
    ssl_prefer_server_ciphers off;
    
    location / {
        # Pass client certificate info to backend
        proxy_set_header X-SSL-Client-Cert $ssl_client_cert;
        proxy_set_header X-SSL-Client-DN $ssl_client_s_dn;
        proxy_set_header X-SSL-Client-Verify $ssl_client_verify;
        proxy_pass http://backend;
    }
}
```

### Verifying mTLS

#### Test mTLS Connection

```bash
# Test with client certificate
curl --cert client-cert.pem \
     --key client-key.pem \
     --cacert ca-bundle.pem \
     https://dean-orchestration.dean.local:8443/health

# Test without client certificate (should fail)
curl --cacert ca-bundle.pem \
     https://dean-orchestration.dean.local:8443/health
# Expected: SSL peer certificate or SSH remote key was not OK

# Verify with openssl
openssl s_client -connect dean-orchestration.dean.local:8443 \
    -cert client-cert.pem \
    -key client-key.pem \
    -CAfile ca-bundle.pem \
    -servername dean-orchestration.dean.local
```

#### Debug mTLS Issues

```bash
# Enable verbose SSL debugging
export PYTHONHTTPSVERIFY=0
export REQUESTS_CA_BUNDLE=/path/to/ca-bundle.pem
export SSL_CERT_FILE=/path/to/ca-bundle.pem

# Test with openssl debug
openssl s_client -connect service:443 -debug -state -CAfile ca-bundle.pem

# Check certificate chain
openssl s_client -connect service:443 -showcerts

# Verify certificate matches private key
openssl x509 -noout -modulus -in cert.pem | openssl md5
openssl rsa -noout -modulus -in key.pem | openssl md5
# Both should output the same hash
```

## Operations Procedures

### Daily Operations

#### Certificate Health Check

```bash
#!/bin/bash
# dean-cert-health.sh

SERVICES="dean-orchestration indexagent evolution-api airflow prometheus grafana"
WARNING_DAYS=30
CRITICAL_DAYS=7

for service in $SERVICES; do
    cert=$(infisical secrets get TLS_CERT --env=production --path=/dean/pki/services/$service)
    expiry=$(echo "$cert" | openssl x509 -noout -enddate | cut -d= -f2)
    expiry_epoch=$(date -d "$expiry" +%s)
    current_epoch=$(date +%s)
    days_left=$(( ($expiry_epoch - $current_epoch) / 86400 ))
    
    if [ $days_left -lt $CRITICAL_DAYS ]; then
        echo "CRITICAL: $service certificate expires in $days_left days!"
        # Send alert
    elif [ $days_left -lt $WARNING_DAYS ]; then
        echo "WARNING: $service certificate expires in $days_left days"
        # Log warning
    else
        echo "OK: $service certificate valid for $days_left days"
    fi
done
```

### Certificate Rotation Procedure

#### Planned Rotation

```bash
# 1. Generate new certificates
cd /opt/dean/pki
./generate_service_certs.sh

# 2. Stage in Infisical (test environment first)
for service in $SERVICES; do
    infisical secrets set NEW_TLS_CERT="$(cat $service-cert.pem)" \
        --env=staging \
        --path=/dean/pki/services/$service
    
    infisical secrets set NEW_TLS_KEY="$(cat $service-key.pem)" \
        --env=staging \
        --path=/dean/pki/services/$service
done

# 3. Test in staging
docker-compose -f docker-compose.staging.yml up -d
./test_mtls_connections.sh

# 4. If successful, promote to production
for service in $SERVICES; do
    # Backup current certificates
    infisical secrets get TLS_CERT --env=production --path=/dean/pki/services/$service > backup/$service-cert.bak
    infisical secrets get TLS_KEY --env=production --path=/dean/pki/services/$service > backup/$service-key.bak
    
    # Update production
    infisical secrets set TLS_CERT="$(cat $service-cert.pem)" \
        --env=production \
        --path=/dean/pki/services/$service \
        --override
    
    infisical secrets set TLS_KEY="$(cat $service-key.pem)" \
        --env=production \
        --path=/dean/pki/services/$service \
        --override
done

# 5. Rolling restart
for service in $SERVICES; do
    docker-compose restart $service
    sleep 30
    ./health_check.sh $service
done
```

#### Emergency Rotation

```bash
# EMERGENCY: Compromised private key detected

# 1. Immediately revoke compromised certificate
./revoke_certificate.sh $COMPROMISED_SERVICE

# 2. Generate new certificate with different key
openssl genrsa -out emergency-key.pem 4096
./generate_emergency_cert.sh $COMPROMISED_SERVICE emergency-key.pem

# 3. Update Infisical immediately
infisical secrets set TLS_CERT="$(cat emergency-cert.pem)" \
    --env=production \
    --path=/dean/pki/services/$COMPROMISED_SERVICE \
    --override \
    --comment="EMERGENCY: Compromised key rotation"

infisical secrets set TLS_KEY="$(cat emergency-key.pem)" \
    --env=production \
    --path=/dean/pki/services/$COMPROMISED_SERVICE \
    --override \
    --comment="EMERGENCY: Compromised key rotation"

# 4. Force restart service
docker-compose stop $COMPROMISED_SERVICE
docker-compose rm -f $COMPROMISED_SERVICE
docker-compose up -d $COMPROMISED_SERVICE

# 5. Verify new certificate
openssl s_client -connect $COMPROMISED_SERVICE:443 -showcerts

# 6. Update CRL and distribute
./update_crl.sh
./distribute_crl.sh
```

### Troubleshooting

#### Common Certificate Issues

**Issue: Certificate verification failed**
```bash
# Debug steps
1. Check certificate dates:
   openssl x509 -in cert.pem -noout -dates

2. Verify certificate chain:
   openssl verify -CAfile ca-bundle.pem cert.pem

3. Check certificate CN/SAN:
   openssl x509 -in cert.pem -noout -text | grep -A1 "Subject Alternative Name"

4. Ensure CA bundle is complete:
   cat root-ca.pem intermediate-ca.pem > ca-bundle.pem
```

**Issue: Private key doesn't match certificate**
```bash
# Verify key/cert match
diff <(openssl x509 -in cert.pem -pubkey -noout) \
     <(openssl rsa -in key.pem -pubout 2>/dev/null)

# If different, regenerate certificate with correct key
```

**Issue: mTLS handshake failure**
```bash
# Enable TLS debugging
export SSLKEYLOGFILE=/tmp/ssl-keys.log
curl -v --cert client.pem --key client.key --cacert ca.pem https://service

# Analyze with Wireshark
tcpdump -i any -s 0 -w tls-debug.pcap 'port 443'

# Check cipher compatibility
openssl s_client -connect service:443 -tls1_3 -cipher 'TLS_AES_256_GCM_SHA384'
```

## Monitoring and Alerts

### Prometheus Metrics

```yaml
# prometheus.yml
- job_name: 'certificate_monitor'
  static_configs:
    - targets: ['cert-monitor:9090']
  metric_relabel_configs:
    - source_labels: [__name__]
      regex: 'cert_.*'
      action: keep
```

### Grafana Dashboards

Create alerts for:
- Certificate expiration < 30 days (warning)
- Certificate expiration < 7 days (critical)
- Failed mTLS handshakes > 5% (warning)
- Certificate validation errors (critical)

### Alert Rules

```yaml
# cert-alerts.yml
groups:
  - name: certificate_alerts
    rules:
      - alert: CertificateExpiringSoon
        expr: cert_expiry_days < 30
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Certificate expiring soon"
          description: "{{ $labels.service }} certificate expires in {{ $value }} days"
      
      - alert: CertificateExpiryCritical
        expr: cert_expiry_days < 7
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Certificate expiring critically soon"
          description: "{{ $labels.service }} certificate expires in {{ $value }} days!"
```

## Backup and Recovery

### Certificate Backup

```bash
#!/bin/bash
# backup-pki.sh

BACKUP_DIR="/secure/backup/pki/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup from Infisical
infisical export --env=production --path=/dean/pki \
    --format=json > $BACKUP_DIR/pki-secrets.json

# Encrypt backup
gpg --encrypt --recipient security@dean-system.local \
    $BACKUP_DIR/pki-secrets.json

# Remove unencrypted file
shred -vfz -n 3 $BACKUP_DIR/pki-secrets.json

# Store encrypted backup
aws s3 cp $BACKUP_DIR/pki-secrets.json.gpg \
    s3://dean-backups/pki/$(date +%Y%m%d)/
```

### Recovery Procedure

```bash
# 1. Restore from backup
aws s3 cp s3://dean-backups/pki/latest/pki-secrets.json.gpg /tmp/
gpg --decrypt /tmp/pki-secrets.json.gpg > /tmp/pki-secrets.json

# 2. Import to Infisical
infisical import --env=production --path=/dean/pki \
    --format=json --file=/tmp/pki-secrets.json

# 3. Regenerate service certificates if needed
./regenerate_all_certs.sh

# 4. Restart all services
docker-compose down
docker-compose up -d

# 5. Verify
./test_all_mtls.sh
```

## Compliance and Auditing

### Certificate Inventory

Maintain an inventory of all certificates:

```csv
service,common_name,issuer,serial,not_before,not_after,key_size,signature_algorithm
dean-orchestration,dean-orchestration.dean.local,DEAN Services CA,1234567890,2025-01-01,2026-01-01,2048,sha256WithRSAEncryption
indexagent,indexagent.dean.local,DEAN Services CA,1234567891,2025-01-01,2026-01-01,2048,sha256WithRSAEncryption
```

### Audit Log Review

```bash
# Review certificate access logs
infisical audit --filter="path:/dean/pki/*" \
    --start="7 days ago" \
    --format=json | jq '.[] | select(.action=="read")'

# Check for unauthorized access attempts
infisical audit --filter="path:/dean/pki/*" \
    --filter="success:false" \
    --start="30 days ago"
```

### Compliance Checklist

- [ ] All certificates use approved algorithms (RSA 2048+ or ECDSA P-256+)
- [ ] Certificate validity does not exceed 1 year
- [ ] All private keys are encrypted at rest
- [ ] Certificate access is logged and audited
- [ ] CRL is updated and distributed regularly
- [ ] Backup procedures are tested quarterly
- [ ] Recovery procedures are documented and tested

## Appendices

### A. OpenSSL Commands Reference

```bash
# Generate private key
openssl genrsa -out private.key 2048

# Generate CSR
openssl req -new -key private.key -out request.csr

# View CSR
openssl req -in request.csr -noout -text

# Sign certificate
openssl x509 -req -in request.csr -CA ca.pem -CAkey ca.key -CAcreateserial -out cert.pem -days 365

# Convert formats
openssl x509 -in cert.pem -out cert.der -outform DER
openssl pkcs12 -export -in cert.pem -inkey private.key -out cert.p12

# Verify certificate
openssl verify -CAfile ca.pem cert.pem

# Check SSL connection
openssl s_client -connect host:port -servername hostname
```

### B. Emergency Contacts

- PKI Administrator: pki-admin@dean-system.local
- Security Team: security@dean-system.local
- On-Call: +1-XXX-XXX-XXXX
- Vendor Support: support@infisical.com