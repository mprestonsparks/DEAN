# DEAN - Distributed Evolutionary Agent Network

**Version**: 1.0.0-beta  
**Status**: Operational (Beta Release)  
**Last Updated**: 2025-06-25

![CI](https://github.com/mprestonsparks/DEAN/workflows/CI/badge.svg)
![CD](https://github.com/mprestonsparks/DEAN/workflows/CD/badge.svg)
![Security](https://github.com/mprestonsparks/DEAN/workflows/Security/badge.svg)

A groundbreaking platform where AI agents evolve to discover code optimizations through distributed collaboration and economic governance.

## What is DEAN?

DEAN (Distributed Evolutionary Agent Network) is an innovative system that creates autonomous AI agents capable of evolving and improving code through genetic algorithms and cellular automata rules. These agents collaborate in a distributed environment, discovering optimization patterns while maintaining genetic diversity through an economic token system.

Unlike traditional static analysis tools, DEAN's agents actively evolve their strategies, learning from successful patterns and propagating improvements across the population. The system uses a token economy to ensure efficient resource usage, rewarding agents that discover valuable optimizations while constraining those that consume resources without contributing.

The platform consists of four interconnected microservices working in harmony: the DEAN Orchestrator coordinates agent activities, IndexAgent manages individual agent logic and evolution, the Evolution API governs the token economy, and Airflow orchestrates complex workflows. All services communicate via REST APIs, ensuring clean separation of concerns and enabling independent scaling.

## System Status

🟢 **System Operational** (as of June 2025)
- 11 active agents running and evolving
- Token economy tracking 55,000/1,000,000 allocated tokens
- All core services healthy
- Pattern discovery and evolution cycles functional

⚠️ **Beta Limitations**
- JWT authentication not yet implemented
- Some orchestration endpoints pending
- Airflow DAGs require manual deployment
- See [DELIVERY_REPORT.md](DELIVERY_REPORT.md) for complete status

## 🚀 Quick Start Guide

### Prerequisites
- Docker Desktop 20.10+ installed and running
- 8GB RAM minimum (16GB recommended)
- Git installed

### Quick Start (5 Steps)

#### 1. Clone Repositories
```bash
# Create workspace and clone all required repositories
mkdir dean-workspace && cd dean-workspace
git clone https://github.com/your-org/DEAN.git
git clone https://github.com/your-org/IndexAgent.git
git clone https://github.com/your-org/infra.git
git clone https://github.com/your-org/airflow-hub.git
```

#### 2. Configure Environment
```bash
cd infra
cp .env.template .env
# Edit .env with your settings (or use defaults for testing)
```

#### 3. Start All Services
```bash
# Start the complete DEAN system
docker-compose -f docker-compose.dean-complete.yml up -d

# Wait for services to initialize (30-60 seconds)
sleep 30
```

#### 4. Create Your First Agent
```bash
curl -X POST http://localhost:8081/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Optimize recursive algorithms",
    "token_budget": 5000
  }'
```

#### 5. Verify System Health
```bash
# Check all services are running
curl http://localhost:8082/health  # DEAN Orchestrator
curl http://localhost:8081/health  # IndexAgent
curl http://localhost:8091/health  # Evolution API

# View token budget status
curl http://localhost:8091/api/v1/economy/budget
```

Access monitoring dashboards:
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

## Core Concepts

### Agents
Autonomous entities with unique genomes that determine their behavior. Each agent has:
- **Goal**: Primary objective (e.g., "Optimize recursive algorithms")
- **Genome**: Traits like efficiency, creativity, exploration
- **Token Budget**: Resources available for operations
- **Fitness Score**: Performance metric based on discoveries

### Evolution
Agents evolve using cellular automata rules:
- **Rule 30**: Introduces randomness and chaos
- **Rule 90**: Creates fractal patterns
- **Rule 110**: Generates complex, Turing-complete behavior
- **Rule 184**: Models traffic flow and optimization

### Token Economy
A finite resource system that:
- **Enforces Efficiency**: Agents must produce value to receive tokens
- **Rewards Discovery**: Pattern discoveries earn token bonuses
- **Prevents Waste**: Inefficient agents are naturally selected out
- **Maintains Balance**: Global budget of 1,000,000 tokens

### Diversity Maintenance
The system maintains genetic diversity above 0.3 to prevent:
- Premature convergence on local optima
- Loss of innovative potential
- Monoculture vulnerabilities

## API Examples

### Create an Agent
```bash
POST http://localhost:8081/api/v1/agents
{
  "goal": "Detect parallelization opportunities",
  "token_budget": 3000,
  "diversity_weight": 0.35,
  "specialized_domain": "parallel_computing"
}
```

### Trigger Evolution
```bash
POST http://localhost:8081/api/v1/agents/{agent_id}/evolve
{
  "generations": 5,
  "mutation_rate": 0.15,
  "ca_rules": [110, 30]
}
```

### Check Token Budget
```bash
GET http://localhost:8091/api/v1/economy/budget

Response:
{
  "global_budget": 1000000,
  "allocated": 55000,
  "available": 945000,
  "agents_count": 11
}
```

### Discover Patterns
```bash
GET http://localhost:8081/api/v1/patterns/discovered

Response:
{
  "patterns": [...],
  "total": 15
}
```

## 📚 Documentation

- **[Delivery Report](DELIVERY_REPORT.md)**: Comprehensive project status and metrics
- **[Specifications](specifications/)**: Detailed system design documents
- **[API Reference](docs/api/)**: OpenAPI specifications for all services
- **[Operations Guide](docs/operations/runbook.md)**: Deployment and maintenance procedures
- **[Architecture](specifications/3-architectural-design-document.md)**: System architecture details
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)**: Solutions for common issues

## Troubleshooting

### Services Not Starting
```bash
# Check Docker is running
docker info

# View service logs
docker-compose -f docker-compose.dean-complete.yml logs service-name

# Common issue: Ports already in use
lsof -i :8082  # Check if port is free
```

### Database Connection Issues
```bash
# Verify PostgreSQL is running
docker-compose -f docker-compose.dean-complete.yml exec postgres pg_isready

# Check schema initialization
docker-compose -f docker-compose.dean-complete.yml exec postgres \
  psql -U postgres -d agent_evolution -c "\dt agent_evolution.*"
```

### Agent Creation Failures
```bash
# Verify IndexAgent health
curl http://localhost:8081/health

# Check token budget availability
curl http://localhost:8091/api/v1/economy/budget

# View IndexAgent logs
docker-compose -f docker-compose.dean-complete.yml logs indexagent
```

### Evolution Not Working
```bash
# Check Evolution API health
curl http://localhost:8091/health

# Verify agent exists
curl http://localhost:8081/api/v1/agents/{agent_id}

# Check for error in logs
docker-compose -f docker-compose.dean-complete.yml logs dean-api
```

## Support and Contribution

### Getting Help
- **Issues**: [GitHub Issues](https://github.com/your-org/DEAN/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/DEAN/discussions)
- **Documentation**: See links above
- **Security**: security@your-org.com (for vulnerabilities)

### Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
```bash
# Install Python dependencies for development
cd DEAN
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v --cov

# Format code
black src/ tests/
```

## License

This project is proprietary software. See [LICENSE](LICENSE) for details.

## Acknowledgments

- Inspired by genetic algorithms and cellular automata research
- Built with FastAPI, Docker, and PostgreSQL
- Token economy concepts from distributed systems research

---

**Note**: This is a beta release. Some features are still under development. See [DELIVERY_REPORT.md](DELIVERY_REPORT.md) for complete feature status.