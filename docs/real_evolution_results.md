# DEAN System Live Evolution Test Results

**Test Date**: 2025-06-24T21:31:52.900142
**Test Type**: Live execution with real services

## Test Execution Log

### 2025-06-24T21:31:49.755718 - Starting DEAN Live Evolution Test

### 2025-06-24T21:31:49.755729 - === Service Health Check ===

### 2025-06-24T21:31:49.764261 - DEAN Orchestrator Health

```json
{
  "status": "healthy",
  "service": "DEAN Orchestration Server",
  "version": "0.1.0",
  "port": 8082,
  "timestamp": "2025-06-25T02:31:49.764208"
}
```

### 2025-06-24T21:31:49.768424 - IndexAgent Health

```json
{
  "status": "healthy",
  "service": "IndexAgent API Service",
  "version": "1.0.0",
  "port": 8081,
  "active_agents": 4,
  "services": {
    "token_economy": true,
    "pattern_detector": true,
    "behavior_monitor": true,
    "dspy_optimizer": true,
    "worktree_manager": false
  }
}
```

### 2025-06-24T21:31:49.768460 - === Creating 3 Agents ===

### 2025-06-24T21:31:49.774775 - Created agent 1

```json
{
  "id": "eb92a5b4-0f79-4381-a11d-4f5587ba672f",
  "name": "IndexAgent_5",
  "goal": "Discover optimization patterns in recursive algorithms",
  "fitness_score": 0.0,
  "token_budget": {
    "total": 1500,
    "used": 0,
    "remaining": 1500,
    "efficiency_score": 0.0
  },
  "diversity_score": 0.35,
  "generation": 0,
  "status": "active",
  "specialized_domain": "code_optimization",
  "worktree_path": null,
  "emergent_patterns": [],
  "created_at": "2025-06-25T02:31:49.774272",
  "updated_at": "2025-06-25T02:31:49.774277"
}
```

### 2025-06-24T21:31:49.779432 - Created agent 2

```json
{
  "id": "aa6f26c0-3552-432e-96dc-a5dea307f0c7",
  "name": "IndexAgent_6",
  "goal": "Identify and extract memoization opportunities",
  "fitness_score": 0.0,
  "token_budget": {
    "total": 1500,
    "used": 0,
    "remaining": 1500,
    "efficiency_score": 0.0
  },
  "diversity_score": 0.35,
  "generation": 0,
  "status": "active",
  "specialized_domain": "code_optimization",
  "worktree_path": null,
  "emergent_patterns": [],
  "created_at": "2025-06-25T02:31:49.779017",
  "updated_at": "2025-06-25T02:31:49.779021"
}
```

### 2025-06-24T21:31:49.783817 - Created agent 3

```json
{
  "id": "f99f8d3e-945d-4822-8224-2c77008f8981",
  "name": "IndexAgent_7",
  "goal": "Detect parallelization patterns in sequential code",
  "fitness_score": 0.0,
  "token_budget": {
    "total": 1500,
    "used": 0,
    "remaining": 1500,
    "efficiency_score": 0.0
  },
  "diversity_score": 0.35,
  "generation": 0,
  "status": "active",
  "specialized_domain": "code_optimization",
  "worktree_path": null,
  "emergent_patterns": [],
  "created_at": "2025-06-25T02:31:49.783657",
  "updated_at": "2025-06-25T02:31:49.783660"
}
```

### 2025-06-24T21:31:49.783850 - === Token Budget Status ===

### 2025-06-24T21:31:49.787473 - Global Budget

```json
{
  "global_budget": 50000,
  "total_allocated": 10000,
  "total_consumed": 0,
  "total_reserved": 0,
  "available": 40000,
  "utilization_rate": 0.0,
  "allocation_rate": 0.2,
  "active_agents": 7,
  "average_efficiency": 1.0,
  "service": "IndexAgent",
  "budget_available": true
}
```

### 2025-06-24T21:31:49.787514 - === Running Evolution Cycles ===

### 2025-06-24T21:31:49.787517 - Evolving agent: eb92a5b4-0f79-4381-a11d-4f5587ba672f

### 2025-06-24T21:31:49.790097 - Evolution result for eb92a5b4-0f79-4381-a11d-4f5587ba672f

```json
{
  "rule_applied": "rule_110",
  "strategy_changes": [
    "Mutated efficiency: 0.800 -> 0.810",
    "Mutated creativity: 0.500 -> 0.510",
    "Mutated exploration: 0.500 -> 0.510"
  ],
  "performance_delta": 0.05,
  "new_patterns": [],
  "optimization_applied": {
    "optimization_applied": true,
    "new_strategies_added": 2,
    "patterns_extracted": 2,
    "original_strategy_count": 3,
    "new_strategy_count": 5,
    "optimization_timestamp": "2025-06-25T02:31:49.790582",
    "performance_before": {
      "fitness": 0.0,
      "efficiency": 0.0
    }
  }
}
```

### 2025-06-24T21:31:50.795190 - Evolving agent: aa6f26c0-3552-432e-96dc-a5dea307f0c7

### 2025-06-24T21:31:50.810016 - Evolution result for aa6f26c0-3552-432e-96dc-a5dea307f0c7

```json
{
  "rule_applied": "rule_110",
  "strategy_changes": [
    "Mutated efficiency: 0.800 -> 0.810",
    "Mutated creativity: 0.500 -> 0.510",
    "Mutated exploration: 0.500 -> 0.510"
  ],
  "performance_delta": 0.05,
  "new_patterns": [],
  "optimization_applied": {
    "optimization_applied": true,
    "new_strategies_added": 2,
    "patterns_extracted": 2,
    "original_strategy_count": 3,
    "new_strategy_count": 5,
    "optimization_timestamp": "2025-06-25T02:31:50.807324",
    "performance_before": {
      "fitness": 0.0,
      "efficiency": 0.0
    }
  }
}
```

### 2025-06-24T21:31:51.815169 - Evolving agent: f99f8d3e-945d-4822-8224-2c77008f8981

### 2025-06-24T21:31:51.828943 - Evolution result for f99f8d3e-945d-4822-8224-2c77008f8981

```json
{
  "rule_applied": "rule_110",
  "strategy_changes": [
    "Mutated efficiency: 0.800 -> 0.810",
    "Mutated creativity: 0.500 -> 0.510",
    "Mutated exploration: 0.500 -> 0.510"
  ],
  "performance_delta": 0.05,
  "new_patterns": [],
  "optimization_applied": {
    "optimization_applied": true,
    "new_strategies_added": 2,
    "patterns_extracted": 2,
    "original_strategy_count": 3,
    "new_strategy_count": 5,
    "optimization_timestamp": "2025-06-25T02:31:51.826876",
    "performance_before": {
      "fitness": 0.0,
      "efficiency": 0.0
    }
  }
}
```

### 2025-06-24T21:31:52.835399 - === Checking Discovered Patterns ===

### 2025-06-24T21:31:52.848348 - Discovered Patterns

```json
{
  "patterns": [],
  "total": 0,
  "summary": {
    "total_patterns": 0
  }
}
```

### 2025-06-24T21:31:52.848732 - === Testing Code Analysis ===

### 2025-06-24T21:31:52.856097 - Analysis failed 1

```json
{
  "status_code": 500,
  "error": "{\"detail\":\"Code analysis failed: name 'datetime' is not defined\"}"
}
```

### 2025-06-24T21:31:52.863741 - Analysis failed 2

```json
{
  "status_code": 500,
  "error": "{\"detail\":\"Code analysis failed: name 'datetime' is not defined\"}"
}
```

### 2025-06-24T21:31:52.863841 - === System Efficiency Metrics ===

### 2025-06-24T21:31:52.870623 - Efficiency Metrics

```json
{
  "metrics": {
    "agent_performance": {
      "average_fitness": 0.0,
      "max_fitness": 0.0,
      "min_fitness": 0.0,
      "total_agents": 7
    },
    "token_efficiency": {
      "average_efficiency": 0.0,
      "total_tokens_used": 300
    },
    "pattern_discovery": {
      "total_patterns": 15,
      "patterns_per_agent": 2.142857142857143,
      "unique_pattern_types": 5
    }
  },
  "service": "IndexAgent"
}
```

### 2025-06-24T21:31:52.870931 - === Testing Pattern Detection ===

### 2025-06-24T21:31:52.881369 - Pattern detection failed

```json
{
  "status_code": 422,
  "error": "{\"detail\":[{\"type\":\"missing\",\"loc\":[\"body\",\"agent_ids\"],\"msg\":\"Field required\",\"input\":{\"agents\":[\"eb92a5b4-0f79-4381-a11d-4f5587ba672f\",\"aa6f26c0-3552-432e-96dc-a5dea307f0c7\"],\"behaviors\":[{\"agent_id\":\"eb92a5b4-0f79-4381-a11d-4f5587ba672f\",\"action\":\"optimize\",\"context\":\"recursive_function\",\"timestamp\":\"2025-06-25T02:31:52.871528Z\"},{\"agent_id\":\"aa6f26c0-3552-432e-96dc-a5dea307f0c7\",\"action\":\"memoize\",\"context\":\"fibonacci_calculation\",\"timestamp\":\"2025-06-25T02:31:52.871706Z\"}],\"window_size\":100}}]}"
}
```

### 2025-06-24T21:31:52.881538 - === Final Agent States ===

### 2025-06-24T21:31:52.887368 - Agent eb92a5b4-0f79-4381-a11d-4f5587ba672f final state

```json
{
  "id": "eb92a5b4-0f79-4381-a11d-4f5587ba672f",
  "name": "IndexAgent_5",
  "genome": {
    "traits": {
      "efficiency": 0.81,
      "creativity": 0.51,
      "exploration": 0.51
    },
    "strategies": [
      "goal_oriented_strategy",
      "domain_code_optimization_strategy",
      "token_optimization",
      "dspy_improvement_strategy",
      "dspy_optimized_approach_1"
    ],
    "mutation_rate": 0.1
  },
  "level": 0,
  "parent_id": null,
  "children": [],
  "token_budget": {
    "total": 1500,
    "used": 100,
    "remaining": 1400,
    "efficiency_score": 0.0
  },
  "diversity_score": 0.016666666666666607,
  "emergent_patterns": [
    "high_performance_evolution_0",
    "multi_strategy_adaptation_0",
    "improvement_seeking_0",
    "reusable_pattern_1",
    "optimization_pattern_2"
  ],
  "fitness_score": 0.0,
  "generation": 1,
  "status": "active",
  "created_at": "2025-06-25T02:31:49.774272",
  "updated_at": "2025-06-25T02:31:49.790581",
  "worktree_path": null,
  "budget_status": {
    "agent_id": "eb92a5b4-0f79-4381-a11d-4f5587ba672f",
    "allocated": 1500,
    "consumed": 0,
    "reserved": 0,
    "remaining": 1500,
    "utilization_rate": 0.0,
    "efficiency_score": 1.0,
    "last_updated": "2025-06-25T02:31:49.774311",
    "performance_metrics": {
      "tokens_per_task": 0.0,
      "value_per_token": 0.0,
      "completion_rate": 0.0,
      "error_rate": 0.0,
      "efficiency_trend": []
    }
  }
}
```

### 2025-06-24T21:31:52.893965 - Agent aa6f26c0-3552-432e-96dc-a5dea307f0c7 final state

```json
{
  "id": "aa6f26c0-3552-432e-96dc-a5dea307f0c7",
  "name": "IndexAgent_6",
  "genome": {
    "traits": {
      "efficiency": 0.81,
      "creativity": 0.51,
      "exploration": 0.51
    },
    "strategies": [
      "goal_oriented_strategy",
      "domain_code_optimization_strategy",
      "token_optimization",
      "dspy_improvement_strategy",
      "dspy_optimized_approach_2"
    ],
    "mutation_rate": 0.1
  },
  "level": 0,
  "parent_id": null,
  "children": [],
  "token_budget": {
    "total": 1500,
    "used": 100,
    "remaining": 1400,
    "efficiency_score": 0.0
  },
  "diversity_score": 0.018333333333333424,
  "emergent_patterns": [
    "high_performance_evolution_0",
    "multi_strategy_adaptation_0",
    "improvement_seeking_0",
    "reusable_pattern_1",
    "optimization_pattern_2"
  ],
  "fitness_score": 0.0,
  "generation": 1,
  "status": "active",
  "created_at": "2025-06-25T02:31:49.779017",
  "updated_at": "2025-06-25T02:31:50.807321",
  "worktree_path": null,
  "budget_status": {
    "agent_id": "aa6f26c0-3552-432e-96dc-a5dea307f0c7",
    "allocated": 1500,
    "consumed": 0,
    "reserved": 0,
    "remaining": 1500,
    "utilization_rate": 0.0,
    "efficiency_score": 1.0,
    "last_updated": "2025-06-25T02:31:49.779082",
    "performance_metrics": {
      "tokens_per_task": 0.0,
      "value_per_token": 0.0,
      "completion_rate": 0.0,
      "error_rate": 0.0,
      "efficiency_trend": []
    }
  }
}
```

### 2025-06-24T21:31:52.899617 - Agent f99f8d3e-945d-4822-8224-2c77008f8981 final state

```json
{
  "id": "f99f8d3e-945d-4822-8224-2c77008f8981",
  "name": "IndexAgent_7",
  "genome": {
    "traits": {
      "efficiency": 0.81,
      "creativity": 0.51,
      "exploration": 0.51
    },
    "strategies": [
      "goal_oriented_strategy",
      "domain_code_optimization_strategy",
      "token_optimization",
      "dspy_improvement_strategy",
      "dspy_optimized_approach_3"
    ],
    "mutation_rate": 0.1
  },
  "level": 0,
  "parent_id": null,
  "children": [],
  "token_budget": {
    "total": 1500,
    "used": 100,
    "remaining": 1400,
    "efficiency_score": 0.0
  },
  "diversity_score": 0.020000000000000018,
  "emergent_patterns": [
    "high_performance_evolution_0",
    "multi_strategy_adaptation_0",
    "improvement_seeking_0",
    "reusable_pattern_1",
    "optimization_pattern_2"
  ],
  "fitness_score": 0.0,
  "generation": 1,
  "status": "active",
  "created_at": "2025-06-25T02:31:49.783657",
  "updated_at": "2025-06-25T02:31:51.826872",
  "worktree_path": null,
  "budget_status": {
    "agent_id": "f99f8d3e-945d-4822-8224-2c77008f8981",
    "allocated": 1500,
    "consumed": 0,
    "reserved": 0,
    "remaining": 1500,
    "utilization_rate": 0.0,
    "efficiency_score": 1.0,
    "last_updated": "2025-06-25T02:31:49.783683",
    "performance_metrics": {
      "tokens_per_task": 0.0,
      "value_per_token": 0.0,
      "completion_rate": 0.0,
      "error_rate": 0.0,
      "efficiency_trend": []
    }
  }
}
```

## Summary

- Total Agents Created: 3
- Evolution Cycles Run: 3
- Test Duration: Live execution
- Status: Completed
