# Service Stubs Authentication Guide

This document explains the authentication implementation in the DEAN service stubs.

## Overview

All service stubs have been updated to include authentication validation, simulating production security requirements while maintaining ease of development.

## Authentication Methods

### 1. Evolution API (Port 8083)
- **Method**: Bearer Token (JWT)
- **Header**: `Authorization: Bearer <token>`
- **Implementation**: Validates JWT tokens on all endpoints except `/health`
- **WebSocket**: Supports token via query parameter: `ws://localhost:8083/ws?token=<token>`

### 2. IndexAgent API (Port 8081)
- **Method**: Bearer Token (JWT)
- **Header**: `Authorization: Bearer <token>`
- **Implementation**: Validates JWT tokens on all endpoints except `/health`
- **Shared Secret**: Uses same JWT secret as main orchestrator

### 3. Airflow API (Port 8080)
- **Method**: HTTP Basic Authentication
- **Credentials**: 
  - Username: `airflow` (or env var `AIRFLOW_USERNAME`)
  - Password: `airflow` (or env var `AIRFLOW_PASSWORD`)
- **Note**: Maintains compatibility with standard Airflow authentication

## JWT Token Structure

Expected JWT payload for Evolution and IndexAgent APIs:
```json
{
  "sub": "user-id",
  "username": "username",
  "roles": ["user", "admin", "service"],
  "type": "access",
  "exp": 1234567890,
  "iat": 1234567890
}
```

## Testing Authentication

### 1. Get a Token
```bash
# Login to get a token from the main orchestrator
curl -X POST https://localhost:8082/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

### 2. Use Token with Evolution API
```bash
# Start an evolution trial
curl -X POST http://localhost:8083/evolution/start \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "test-repo",
    "generations": 10,
    "population_size": 20
  }'
```

### 3. Use Token with IndexAgent API
```bash
# Create an agent
curl -X POST http://localhost:8081/agents \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-agent",
    "language": "python",
    "capabilities": ["search", "analyze"]
  }'
```

### 4. Use Basic Auth with Airflow
```bash
# List DAGs
curl -X GET http://localhost:8080/api/v1/dags \
  -u airflow:airflow
```

## Service-to-Service Authentication

When the orchestrator calls other services, it should:
1. Use a service token with `"type": "service"` claim
2. Include appropriate role (e.g., `"roles": ["service"]`)
3. Have longer expiration for service tokens

## Development Tips

### Disable Authentication (Development Only)
To disable authentication for local development:
```bash
# Set environment variable
export DISABLE_AUTH=true
```
Then modify the verify_token function to check this variable.

### Generate Test Tokens
```python
import jwt
from datetime import datetime, timedelta

# Generate a test token
token = jwt.encode({
    "sub": "test-user",
    "username": "testuser",
    "roles": ["user"],
    "type": "access",
    "exp": datetime.utcnow() + timedelta(hours=1),
    "iat": datetime.utcnow()
}, "test-secret-key", algorithm="HS256")

print(f"Test token: {token}")
```

## Security Notes

1. **JWT Secret**: All services use the same JWT secret (`JWT_SECRET_KEY` env var)
2. **Token Expiration**: Tokens are validated for expiration
3. **Role Validation**: Services can check roles but currently accept any authenticated user
4. **Audit Logging**: All authenticated actions are logged with username

## Future Enhancements

1. **Role-Based Access**: Implement role checking for specific operations
2. **API Key Support**: Add API key authentication as alternative
3. **Token Refresh**: Implement refresh token endpoint in stubs
4. **Rate Limiting**: Add rate limiting to prevent abuse
5. **CORS Configuration**: Tighten CORS policy for production