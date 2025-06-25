# Infisical Server Dockerfile for Air-Gapped Operation
FROM infisical/infisical:latest

# Install additional tools for air-gapped operation
USER root
RUN apk add --no-cache \
    curl \
    openssl \
    ca-certificates \
    postgresql-client \
    bash

# Create directories for certificates and configuration
RUN mkdir -p /app/certs /app/config /app/data && \
    chown -R infisical:infisical /app

# Copy air-gapped configuration
COPY --chown=infisical:infisical config/infisical.json /app/config/
COPY --chown=infisical:infisical scripts/init-infisical.sh /app/scripts/
RUN chmod +x /app/scripts/init-infisical.sh

# Switch back to infisical user
USER infisical

# Set environment for air-gapped mode
ENV INFISICAL_TELEMETRY_ENABLED=false
ENV INFISICAL_AIR_GAPPED=true
ENV INFISICAL_DB_CONNECTION_URI=postgresql://infisical_user:PLACEHOLDER@postgres-infisical:5432/infisical
ENV INFISICAL_REDIS_URL=redis://:PLACEHOLDER@redis-infisical:6379
ENV INFISICAL_ENCRYPTION_KEY=PLACEHOLDER
ENV INFISICAL_AUTH_SECRET=PLACEHOLDER
ENV INFISICAL_JWT_SECRET=PLACEHOLDER
ENV INFISICAL_PUBLIC_URL=http://10.7.0.2:8090
ENV INFISICAL_PORT=8090
ENV INFISICAL_LOG_LEVEL=info
ENV INFISICAL_AUDIT_LOG_RETENTION_DAYS=90

# Expose Infisical port
EXPOSE 8090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8090/api/status || exit 1

# Start Infisical with initialization script
ENTRYPOINT ["/app/scripts/init-infisical.sh"]