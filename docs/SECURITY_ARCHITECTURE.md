# DEAN Security Architecture

## Overview

The DEAN system implements a zero-trust security architecture with Infisical as the central secrets management platform. This document outlines the security layers, PKI infrastructure, and operational security procedures.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DEAN Security Architecture                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────┐        ┌─────────────────┐                      │
│  │   Infisical     │        │   DEAN Root CA  │                      │
│  │  (Port 8090)    │        │   (10 years)    │                      │
│  └────────┬────────┘        └────────┬────────┘                      │
│           │                           │                               │
│           ├──── Secret Storage        └──── PKI Infrastructure       │
│           │                                        │                  │
│  ┌────────▼────────┐        ┌────────────────────▼─────────┐        │
│  │ Service Tokens  │        │ DEAN Intermediate CA (5 years)│        │
│  │ & API Keys      │        └────────────────────┬─────────┘        │
│  └─────────────────┘                             │                   │
│                                     ┌─────────────┴───────────┐      │
│                                     │ Service Certificates    │      │
│                                     │ (1 year auto-renewal)  │      │
│                                     └─────────────────────────┘      │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    mTLS Communication Layer                  │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │  Service A  ←──── mTLS ────→  Service B  ←──── mTLS ────→  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Audit & Compliance Layer                  │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │  • All secret access logged    • 90-day retention           │    │
│  │  • Certificate usage tracked   • Compliance reports         │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

## Security Layers

### 1. Secret Management Layer (Infisical)

**Purpose**: Centralized, encrypted storage and distribution of all secrets

**Implementation**:
- Infisical server deployed on port 8090
- Air-gapped configuration (no external calls)
- PostgreSQL backend with encrypted storage
- Redis caching for performance

**Key Features**:
- AES-256-GCM encryption for secrets at rest
- TLS 1.3 for secrets in transit
- Role-based access control (RBAC)
- Audit logging for all secret access
- Secret versioning and rotation
- Dynamic secret generation

### 2. PKI Infrastructure Layer

**Purpose**: Certificate-based authentication for all services

**Certificate Hierarchy**:
```
DEAN Root CA (Self-signed, 10 years)
    └── DEAN Services CA (Intermediate, 5 years)
        ├── dean-orchestration.dean.local (1 year)
        ├── indexagent.dean.local (1 year)
        ├── evolution-api.dean.local (1 year)
        ├── airflow-webserver.dean.local (1 year)
        ├── prometheus.dean.local (1 year)
        └── grafana.dean.local (1 year)
```

**Key Management**:
- RSA 4096-bit keys for CAs
- RSA 2048-bit keys for service certificates
- Automatic renewal 30 days before expiration
- Private keys stored encrypted in Infisical

### 3. Service Authentication Layer

**Purpose**: Ensure only authenticated services can communicate

**Implementation**:
- Service tokens for Infisical access
- mTLS for service-to-service communication
- JWT tokens for user authentication
- API key validation for external access

**Authentication Flow**:
1. Service starts with Infisical service token
2. Service retrieves secrets and certificates
3. Service establishes mTLS connections
4. All API calls require valid authentication

### 4. Network Security Layer

**Purpose**: Isolate and protect service communications

**Implementation**:
- Dedicated `dean-network` for internal services
- `infisical-network` for secret management
- No direct internet access for internal services
- Firewall rules restricting port access

**Network Policies**:
- Deny all by default
- Allow only required service-to-service communication
- Separate management network for operations

## Security Controls

### Access Control

**User Authentication**:
- Multi-factor authentication for admin access
- JWT tokens with 15-minute expiration
- Refresh tokens with 7-day lifetime
- Account lockout after 5 failed attempts

**Service Authentication**:
- Unique service tokens per container
- Certificate-based mutual authentication
- No shared credentials between services
- Automatic token rotation

### Encryption

**Data at Rest**:
- AES-256-GCM for secret storage
- Encrypted PostgreSQL databases
- Encrypted Redis persistence
- Encrypted backup storage

**Data in Transit**:
- TLS 1.3 minimum for all connections
- mTLS for service-to-service
- Certificate pinning for critical services
- No unencrypted communication allowed

### Audit and Compliance

**Audit Logging**:
- All secret access logged with:
  - Timestamp
  - Service/User ID
  - Secret path accessed
  - IP address
  - Success/failure status
- 90-day retention period
- Immutable audit trail
- Regular audit reports

**Compliance Features**:
- GDPR-compliant data handling
- SOC 2 Type II controls
- Secret scanning in CI/CD
- Regular security assessments

## Operational Security

### Secret Rotation

**Automated Rotation**:
- Database passwords: 90 days
- API keys: 180 days
- Service tokens: 365 days
- Certificates: 30 days before expiry

**Manual Rotation Process**:
1. Generate new secret in Infisical
2. Update service configuration
3. Deploy with zero downtime
4. Verify service health
5. Mark old secret for deletion

### Incident Response

**Security Incident Procedure**:
1. **Detection**: Automated alerts for anomalies
2. **Containment**: Isolate affected services
3. **Investigation**: Review audit logs
4. **Remediation**: Rotate compromised credentials
5. **Recovery**: Restore normal operations
6. **Post-mortem**: Document and improve

### Backup and Recovery

**Backup Strategy**:
- Daily encrypted backups of Infisical
- Geographically distributed storage
- Automated backup verification
- 30-day retention period

**Recovery Procedures**:
1. Restore Infisical from backup
2. Verify secret integrity
3. Re-issue service certificates
4. Restart services with new credentials
5. Validate system functionality

## Security Hardening

### Container Security

**Base Image Hardening**:
- Minimal Alpine Linux base
- No root user execution
- Read-only root filesystem
- No shell access in production

**Runtime Security**:
- Seccomp profiles enabled
- AppArmor/SELinux policies
- Resource limits enforced
- No privileged containers

### Application Security

**Code Security**:
- No hardcoded secrets
- Input validation on all endpoints
- SQL injection prevention
- XSS protection enabled

**Dependency Management**:
- Regular vulnerability scanning
- Automated dependency updates
- License compliance checking
- Supply chain verification

## Monitoring and Alerting

### Security Metrics

**Key Metrics Monitored**:
- Failed authentication attempts
- Unusual secret access patterns
- Certificate expiration status
- Service communication anomalies
- Resource utilization spikes

**Alert Thresholds**:
- 5+ failed auth attempts: Warning
- 10+ failed auth attempts: Critical
- Certificate < 7 days: Warning
- Certificate < 1 day: Critical
- Unusual access pattern: Immediate

### Security Dashboards

**Grafana Dashboards**:
- Authentication metrics
- Secret access patterns
- Certificate status
- Network traffic analysis
- Compliance reporting

## Compliance and Governance

### Security Policies

**Access Control Policy**:
- Principle of least privilege
- Regular access reviews
- Automated de-provisioning
- Segregation of duties

**Data Protection Policy**:
- Encryption requirements
- Data classification
- Retention periods
- Secure disposal

### Regular Assessments

**Security Reviews**:
- Quarterly security audits
- Annual penetration testing
- Continuous vulnerability scanning
- Regular security training

## Emergency Procedures

### Lost Access Recovery

**Infisical Admin Recovery**:
1. Access PostgreSQL directly
2. Reset admin password hash
3. Re-enable admin account
4. Update credentials
5. Review audit logs

### Complete System Compromise

**Full Recovery Process**:
1. Isolate all systems
2. Preserve evidence
3. Deploy fresh infrastructure
4. Generate all new credentials
5. Restore from clean backups
6. Implement additional controls

## Security Best Practices

### For Developers

1. Never commit secrets to code
2. Use Infisical CLI for local development
3. Implement proper error handling
4. Follow secure coding standards
5. Regular security training

### For Operations

1. Regular security updates
2. Monitor security alerts
3. Practice incident response
4. Maintain security documentation
5. Conduct security reviews

### For Management

1. Enforce security policies
2. Allocate security resources
3. Support security initiatives
4. Regular risk assessments
5. Security-first culture

## Appendices

### A. Security Checklist

- [ ] Infisical deployed and healthy
- [ ] All secrets migrated to Infisical
- [ ] PKI infrastructure configured
- [ ] mTLS enabled for all services
- [ ] Audit logging operational
- [ ] Monitoring dashboards active
- [ ] Incident response plan tested
- [ ] Backup procedures verified
- [ ] Security training completed
- [ ] Compliance requirements met

### B. Tool Reference

**Security Tools Used**:
- Infisical: Secret management
- OpenSSL: Certificate generation
- Prometheus: Security monitoring
- Grafana: Security dashboards
- Docker: Container security

### C. Contact Information

**Security Team**:
- Security Lead: security@dean-system.local
- Incident Response: incident@dean-system.local
- Compliance: compliance@dean-system.local

**Emergency Contacts**:
- On-call: +1-XXX-XXX-XXXX
- Escalation: management@dean-system.local