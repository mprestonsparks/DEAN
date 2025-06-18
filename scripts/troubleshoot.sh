#!/bin/bash
# scripts/troubleshoot.sh

echo "DEAN System Troubleshooting"
echo "=========================="

# Check Docker
echo -e "\n1. Docker Status:"
docker version &>/dev/null && echo "✓ Docker is running" || echo "✗ Docker is not running"

# Check services
echo -e "\n2. Service Status:"
docker-compose -f docker-compose.prod.yml ps

# Check logs for errors
echo -e "\n3. Recent Errors:"
docker-compose -f docker-compose.prod.yml logs --tail=50 | grep -i error | tail -10

# Check disk space
echo -e "\n4. Disk Space:"
df -h | grep -E "^/|Filesystem"

# Check memory
echo -e "\n5. Memory Usage:"
free -h

# Check ports
echo -e "\n6. Port Usage:"
netstat -tlnp 2>/dev/null | grep -E ":(80|443|8080|8081|8082|5432|6379)" || \
    lsof -iTCP -sTCP:LISTEN -P | grep -E ":(80|443|8080|8081|8082|5432|6379)"

# Check certificates
echo -e "\n7. SSL Certificates:"
if [[ -f ./certs/server.crt ]]; then
    openssl x509 -in ./certs/server.crt -noout -dates
else
    echo "✗ No certificates found"
fi

# Database connectivity
echo -e "\n8. Database Connectivity:"
docker-compose -f docker-compose.prod.yml exec -T postgres-prod pg_isready -U ${POSTGRES_USER:-dean_prod} &>/dev/null && \
    echo "✓ PostgreSQL is accessible" || echo "✗ PostgreSQL is not accessible"

# API health
echo -e "\n9. API Health:"
curl -s http://localhost:8082/health | jq . 2>/dev/null || echo "✗ API is not responding"

echo -e "\n10. Common Issues and Solutions:"
echo "- Nginx fails: Check certificates in ./certs/"
echo "- Port conflicts: Change ports in .env file"
echo "- Database errors: Check POSTGRES_* variables in .env"
echo "- Memory issues: Increase Docker memory allocation"