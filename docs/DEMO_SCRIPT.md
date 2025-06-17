# DEAN Demonstration Script

## 5-Minute System Demo

This script guides you through a compelling demonstration of the DEAN orchestration system, showcasing its key capabilities in under 5 minutes.

### Pre-Demo Checklist
- [ ] All services running (`./scripts/health_check.sh`)
- [ ] Dashboard accessible at http://localhost:8082
- [ ] Terminal ready with demo script
- [ ] Browser tabs open: Dashboard, Health Monitor

---

## Demo Flow

### 1. Introduction (30 seconds)

**Script:**
"Welcome to DEAN - the Distributed Evolutionary Agent Network. DEAN uses evolutionary algorithms to automatically optimize code and discover performance patterns."

**Action:**
- Show the main dashboard at http://localhost:8082

**Key Points:**
- Autonomous agent evolution
- Pattern discovery engine
- Real-time monitoring
- Enterprise-ready security

---

### 2. Authentication & Security (30 seconds)

**Script:**
"DEAN implements enterprise-grade security with JWT authentication and role-based access control."

**Terminal Commands:**
```bash
# Show login process
curl -X POST http://localhost:8082/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

**Action:**
- Show the token response
- Highlight token expiration and refresh mechanism

**Key Points:**
- JWT-based authentication
- Role-based permissions (Admin, User, Viewer)
- Token refresh for session management

---

### 3. Agent Creation (45 seconds)

**Script:**
"Let's create intelligent agents that will participate in evolution. Each agent has specific capabilities and evolves to improve performance."

**Terminal Commands:**
```bash
# Create a search optimization agent
curl -X POST http://localhost:8081/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "search-optimizer-demo",
    "language": "python",
    "capabilities": ["search", "optimize", "analyze"]
  }'

# Create a pattern detection agent
curl -X POST http://localhost:8081/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "pattern-detector-demo",
    "language": "python",
    "capabilities": ["pattern", "analyze", "evolve"]
  }'
```

**Action:**
- Show agent creation responses
- Navigate to Agents page in dashboard

**Key Points:**
- Agents have fitness scores
- Multiple capability types
- Ready for evolution

---

### 4. Evolution Trial (90 seconds)

**Script:**
"Now we'll start an evolution trial where agents compete, mutate, and evolve to discover optimization patterns."

**Terminal Commands:**
```bash
# Start evolution trial
curl -X POST http://localhost:8083/evolution/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "demo-optimization-project",
    "generations": 5,
    "population_size": 20,
    "mutation_rate": 0.15,
    "crossover_rate": 0.7,
    "fitness_threshold": 0.9
  }'
```

**Action:**
- Show trial starting
- Switch to dashboard Evolution page
- Watch real-time progress bar
- Point out fitness improvements

**Talking Points While Waiting:**
- "Notice how fitness improves each generation"
- "The system is discovering patterns in real-time"
- "Agents that perform better survive and reproduce"
- "Mutations introduce new strategies"

---

### 5. Pattern Discovery (60 seconds)

**Script:**
"As evolution progresses, DEAN discovers optimization patterns that can be applied across your codebase."

**Terminal Commands:**
```bash
# Query discovered patterns
curl -X GET "http://localhost:8083/patterns?min_confidence=0.8" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Action:**
- Show discovered patterns
- Explain pattern types

**Example Patterns to Highlight:**
```json
{
  "name": "Async Handler Optimization",
  "confidence": 0.92,
  "impact_score": 0.85,
  "description": "Convert synchronous operations to async for 3x performance"
}
```

**Key Points:**
- Patterns have confidence scores
- Impact scores show potential improvement
- Can be applied to similar code

---

### 6. System Monitoring (45 seconds)

**Script:**
"DEAN provides comprehensive monitoring to track system health and performance."

**Action:**
- Open Health Dashboard (http://localhost:8082/health.html)
- Show real-time metrics

**Key Metrics to Highlight:**
- Service health indicators (all green)
- Active trials counter
- Resource usage graphs
- API response times

**Terminal Commands:**
```bash
# Show system metrics
curl -X GET http://localhost:8082/api/metrics \
  -H "Authorization: Bearer $TOKEN" | jq .
```

---

### 7. Results & Benefits (30 seconds)

**Script:**
"In just 5 minutes, we've seen DEAN automatically evolve agents, discover optimization patterns, and provide real-time insights."

**Summary Points:**
- ✅ Automated optimization discovery
- ✅ No manual pattern definition needed
- ✅ Continuous improvement through evolution
- ✅ Enterprise-ready with full security
- ✅ Scales to large codebases

**Call to Action:**
"DEAN can be deployed on your infrastructure today. Visit our documentation to get started."

---

## Post-Demo Questions & Answers

### Common Questions:

**Q: How long do evolution trials typically take?**
A: "Trials can run from minutes to hours depending on complexity. The system is designed to find useful patterns quickly."

**Q: What languages does DEAN support?**
A: "Currently Python, with JavaScript and Java support coming soon."

**Q: Can DEAN integrate with CI/CD pipelines?**
A: "Yes, DEAN has REST APIs that integrate easily with Jenkins, GitLab CI, and GitHub Actions."

**Q: How does DEAN ensure code quality?**
A: "Fitness functions include tests, performance metrics, and code quality checks."

---

## Demo Variations

### Quick Demo (2 minutes)
1. Login and authentication
2. Start pre-configured trial
3. Show real-time evolution
4. Display discovered patterns

### Technical Deep Dive (10 minutes)
1. Full demo flow
2. Explain fitness functions
3. Show API documentation
4. Demonstrate WebSocket monitoring
5. Explain pattern application

### Executive Overview (3 minutes)
1. Dashboard overview
2. Show ROI metrics
3. Highlight automation benefits
4. Security compliance features

---

## Troubleshooting

### If services are down:
```bash
./scripts/health_check.sh
./scripts/dev_environment.sh  # Restart
```

### If evolution seems stuck:
- Check Evolution API logs
- Verify agent creation worked
- Ensure sufficient resources

### If no patterns found:
- Let trial run longer
- Reduce confidence threshold
- Check pattern query parameters

---

## Demo Assets

### Sample Patterns for Discussion:
1. **Loop Optimization**: "Vectorized operations 10x faster"
2. **Caching Strategy**: "Reduced API calls by 75%"
3. **Async Conversion**: "Improved throughput 3x"
4. **Error Handling**: "Reduced failure rate 90%"

### Success Metrics:
- Average fitness improvement: 65%
- Patterns discovered per trial: 4-8
- Time to first pattern: < 2 minutes
- System uptime: 99.9%

---

## Closing Statement

"DEAN represents the future of automated code optimization. By combining evolutionary algorithms with pattern recognition, it discovers optimizations that human developers might miss. 

Ready to evolve your codebase? Let's get started."

**Contact:** TODO: Update
**Documentation:** TODO: Update