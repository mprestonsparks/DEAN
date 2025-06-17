# DEAN Quick Start Guide

Welcome to DEAN (Distributed Evolutionary Agent Network)! This guide will get you up and running in under 30 minutes.

## What is DEAN?

DEAN is an orchestration system that manages evolutionary AI agents to discover optimization patterns and improve code performance through automated evolution trials.

## Prerequisites

- **Hardware**: 4+ CPU cores, 16GB RAM minimum
- **Software**: Docker 20.10+, Python 3.10+, Git
- **Ports**: 8080-8083, 5432, 6379 must be available

## 🚀 5-Minute Quick Start

### 1. Clone and Enter the Repository

```bash
git clone https://github.com/your-org/dean-orchestration.git
cd dean-orchestration/DEAN
```

### 2. Run the Quick Setup

```bash
# One command to start everything
./scripts/dev_environment.sh
```

This script will:
- ✅ Check port availability
- ✅ Start all required services
- ✅ Create SSL certificates
- ✅ Initialize the database
- ✅ Launch the orchestration server
- ✅ Open the dashboard in your browser

### 3. Login to the Dashboard

When the browser opens to `http://localhost:8082`:

**Default Credentials:**
- Username: `admin`
- Password: `admin123`

⚠️ **Security Note**: Change these credentials before production use!

### 4. Run Your First Evolution Trial

#### Option A: Using the Dashboard (Easy)

1. Click **"Evolution Trials"** in the navigation
2. Click **"New Trial"**
3. Use these settings for a quick demo:
   - Repository: `demo-project`
   - Generations: `5`
   - Population Size: `10`
4. Click **"Start Trial"**
5. Watch the real-time progress!

#### Option B: Using the API (For Developers)

```bash
# Get authentication token
TOKEN=$(curl -s -X POST http://localhost:8082/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' \
  | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Create an agent
curl -X POST http://localhost:8081/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-first-agent",
    "language": "python",
    "capabilities": ["search", "optimize"]
  }'

# Start evolution trial
curl -X POST http://localhost:8083/evolution/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "my-project",
    "generations": 5,
    "population_size": 10
  }'
```

### 5. Monitor Progress

- **Dashboard**: Real-time updates at http://localhost:8082
- **Logs**: `docker-compose -f service_stubs/docker-compose.stubs.yml logs -f`
- **Metrics**: http://localhost:8082/api/metrics

## 📊 Understanding the Results

After your trial completes:

1. **Fitness Score**: Shows how well agents performed (0.0 to 1.0)
2. **Patterns Discovered**: Optimization patterns found during evolution
3. **Generation Progress**: How fitness improved over time

Example output:
```
Generation 1/5 | Fitness: 0.523 | Patterns: 0
Generation 2/5 | Fitness: 0.641 | Patterns: 1
Generation 3/5 | Fitness: 0.758 | Patterns: 2
Generation 4/5 | Fitness: 0.832 | Patterns: 3
Generation 5/5 | Fitness: 0.891 | Patterns: 4
✓ Evolution completed!
```

## 🛠️ Common Tasks

### View All Agents
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8081/agents | jq .
```

### Check Evolution Status
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8083/evolution/TRIAL_ID/status | jq .
```

### Discover Patterns
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8083/patterns?min_confidence=0.8" | jq .
```

### Stop All Services
```bash
./scripts/stop_dev_environment.sh
```

## 🔧 Troubleshooting

### Services Won't Start

**Problem**: Port already in use
```bash
# Check what's using the ports
lsof -i :8082
```
**Solution**: Stop conflicting services or change DEAN ports in configuration

### Authentication Errors

**Problem**: 401 Unauthorized errors
```bash
# Get a fresh token
./scripts/quick_auth_test.sh
```

### Evolution Trial Stuck

**Problem**: Trial not progressing
```bash
# Check service health
curl http://localhost:8083/health
curl http://localhost:8081/health
```

### Can't Access Dashboard

**Problem**: Browser can't connect
- Check firewall settings
- Verify services are running: `docker ps`
- Try: `curl http://localhost:8082/health`

## 📚 Next Steps

### 1. Explore the Dashboard
- **Agents**: View and manage AI agents
- **Evolution**: Run and monitor trials  
- **Patterns**: Explore discovered optimizations
- **Metrics**: System performance data

### 2. Read the Documentation
- [Architecture Overview](./architecture/README.md)
- [API Reference](./development/API_CONTRACTS.md)
- [Security Guide](./security/SECURITY_GUIDE.md)

### 3. Try Advanced Features
- Create custom agent types
- Configure evolution parameters
- Set up monitoring alerts
- Integrate with your CI/CD pipeline

### 4. Join the Community
- Report issues: https://github.com/your-org/dean/issues
- Contribute: See [CONTRIBUTING.md](../CONTRIBUTING.md)
- Get help: https://dean-community.slack.com

## 🎯 Example Use Cases

### Code Optimization
```python
# DEAN can discover patterns to optimize this:
def slow_function(data):
    result = []
    for item in data:
        if complex_check(item):
            result.append(transform(item))
    return result

# Into this optimized version:
def fast_function(data):
    return [transform(item) for item in data if complex_check(item)]
```

### Performance Tuning
DEAN agents can identify:
- Bottlenecks in code execution
- Memory usage patterns
- Optimal algorithm parameters
- Caching opportunities

### Pattern Discovery
Common patterns DEAN finds:
- Loop optimizations
- Async operation improvements
- Resource cleanup patterns
- Error handling strategies

## 🎉 Congratulations!

You've successfully:
- ✅ Started the DEAN system
- ✅ Authenticated as a user
- ✅ Created AI agents
- ✅ Run an evolution trial
- ✅ Discovered optimization patterns

**Time to first evolution**: < 5 minutes! 🚀

---

Need help? Check the [Troubleshooting Guide](./TROUBLESHOOTING.md) or run:
```bash
./scripts/health_check.sh --verbose
```

Happy evolving! 🧬