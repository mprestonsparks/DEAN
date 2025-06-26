#!/usr/bin/env python3
"""
Simple Integration Test for DEAN Services using requests library.
"""

import requests
import json
import time
from datetime import datetime


def test_service_health():
    """Test all services are healthy."""
    print("\n1. Testing Service Health")
    print("-" * 40)
    
    services = {
        "DEAN Orchestrator": "http://localhost:8082/health",
        "IndexAgent": "http://localhost:8081/health",
        "Token Economy": "http://localhost:8091/health",
        "Prometheus": "http://localhost:9090/-/healthy"
    }
    
    healthy_count = 0
    for name, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✓ {name}: Healthy")
                if name != "Prometheus":
                    data = response.json()
                    print(f"  Service: {data.get('service', 'Unknown')}")
                    print(f"  Version: {data.get('version', 'Unknown')}")
                healthy_count += 1
            else:
                print(f"✗ {name}: Status {response.status_code}")
        except Exception as e:
            print(f"✗ {name}: {str(e)}")
    
    return healthy_count == len(services)


def test_create_agent():
    """Test agent creation."""
    print("\n2. Testing Agent Creation")
    print("-" * 40)
    
    agent_data = {
        "genome": {
            "traits": {
                "exploration": 0.5,
                "efficiency": 0.5,
                "learning_rate": 0.1
            },
            "strategies": ["baseline", "explore"]
        },
        "token_budget": 2000
    }
    
    try:
        response = requests.post(
            "http://localhost:8081/api/v1/agents",
            json=agent_data,
            timeout=10
        )
        
        if response.status_code == 200:
            agent = response.json()
            agent_id = agent.get("id")
            print(f"✓ Created agent: {agent_id}")
            print(f"  Initial fitness: {agent.get('fitness', 0)}")
            print(f"  Token budget: {agent.get('token_budget', 0)}")
            return agent_id
        else:
            print(f"✗ Failed to create agent: {response.status_code}")
            print(f"  Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ Error creating agent: {e}")
        return None


def test_evolution_trial():
    """Test running an evolution trial."""
    print("\n3. Testing Evolution Trial")
    print("-" * 40)
    
    trial_data = {
        "population_size": 3,
        "generations": 5,
        "token_budget": 10000,
        "diversity_threshold": 0.3,
        "mutation_rate": 0.1
    }
    
    try:
        # Start evolution trial
        response = requests.post(
            "http://localhost:8082/api/v1/evolution/start",
            json=trial_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            trial_id = result.get("trial_id")
            print(f"✓ Started evolution trial: {trial_id}")
            
            # Wait a bit for some progress
            print("  Waiting for evolution progress...")
            time.sleep(5)
            
            # Check trial status
            status_response = requests.get(
                f"http://localhost:8082/api/v1/evolution/{trial_id}/status",
                timeout=10
            )
            
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"  Status: {status.get('status', 'Unknown')}")
                print(f"  Generation: {status.get('current_generation', 0)}/{trial_data['generations']}")
                print(f"  Population diversity: {status.get('diversity', 0):.3f}")
                return trial_id
            else:
                print(f"  Failed to get status: {status_response.status_code}")
                return trial_id
        else:
            print(f"✗ Failed to start trial: {response.status_code}")
            print(f"  Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ Error running trial: {e}")
        return None


def test_pattern_discovery():
    """Test pattern discovery."""
    print("\n4. Testing Pattern Discovery")
    print("-" * 40)
    
    try:
        response = requests.get(
            "http://localhost:8081/api/v1/patterns/discovered",
            timeout=10
        )
        
        if response.status_code == 200:
            patterns = response.json()
            pattern_count = len(patterns) if isinstance(patterns, list) else 0
            print(f"✓ Retrieved {pattern_count} patterns")
            
            if pattern_count > 0 and isinstance(patterns, list):
                # Show first pattern
                pattern = patterns[0]
                print(f"  Example pattern:")
                print(f"    Type: {pattern.get('type', 'Unknown')}")
                print(f"    Effectiveness: {pattern.get('effectiveness', 0):.3f}")
                print(f"    Performance improvement: {pattern.get('performance_improvement', 0):.1%}")
                
                # Count valid patterns
                valid_patterns = [p for p in patterns if p.get('performance_improvement', 0) >= 0.2]
                print(f"  Valid patterns (20%+ improvement): {len(valid_patterns)}")
            
            return pattern_count > 0
        else:
            print(f"✗ Failed to get patterns: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error getting patterns: {e}")
        return False


def test_token_economy():
    """Test token economy enforcement."""
    print("\n5. Testing Token Economy")
    print("-" * 40)
    
    try:
        # Test allocation
        allocation_data = {
            "agent_id": "test_token_agent_1",
            "requested_tokens": 2000,
            "agent_metadata": {"type": "test"}
        }
        
        response = requests.post(
            "http://localhost:8091/api/v1/tokens/allocate",
            json=allocation_data,
            timeout=10
        )
        
        if response.status_code == 200:
            allocation = response.json()
            allocated = allocation.get("allocated_tokens", 0)
            print(f"✓ Allocated {allocated} tokens to test agent")
            print(f"  Efficiency multiplier: {allocation.get('efficiency_multiplier', 1):.2f}")
            print(f"  Remaining global budget: {allocation.get('remaining_global_budget', 0)}")
            
            # Test budget exhaustion
            print("\n  Testing budget exhaustion:")
            allocated_count = 1  # We already allocated once
            rejected_count = 0
            
            for i in range(10):
                test_data = {
                    "agent_id": f"exhaustion_test_{i}",
                    "requested_tokens": 3000,
                    "agent_metadata": {"type": "exhaustion_test"}
                }
                
                test_response = requests.post(
                    "http://localhost:8091/api/v1/tokens/allocate",
                    json=test_data,
                    timeout=10
                )
                
                if test_response.status_code == 200:
                    allocated_count += 1
                else:
                    rejected_count += 1
            
            print(f"  Allocated: {allocated_count}, Rejected: {rejected_count}")
            print(f"  ✓ Budget enforcement working: {rejected_count > 0}")
            
            return rejected_count > 0
        else:
            print(f"✗ Failed to allocate tokens: {response.status_code}")
            print(f"  Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing token economy: {e}")
        return False


def test_metrics():
    """Test Prometheus metrics."""
    print("\n6. Testing Metrics Collection")
    print("-" * 40)
    
    try:
        # Query Prometheus for DEAN metrics
        dean_metrics = [
            "dean_agents_created_total",
            "dean_tokens_allocated_total",
            "dean_evolution_duration_seconds",
            "dean_population_diversity"
        ]
        
        found_metrics = []
        for metric in dean_metrics:
            response = requests.get(
                f"http://localhost:9090/api/v1/query",
                params={"query": metric},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("data", {}).get("result"):
                    found_metrics.append(metric)
        
        print(f"✓ Found {len(found_metrics)}/{len(dean_metrics)} DEAN metrics")
        for metric in found_metrics:
            print(f"  - {metric}")
        
        return len(found_metrics) > 0
        
    except Exception as e:
        print(f"✗ Error checking metrics: {e}")
        return False


def test_database_data():
    """Test database contains evolution data."""
    print("\n7. Testing Database Data")
    print("-" * 40)
    
    try:
        # Query database through the API
        response = requests.get(
            "http://localhost:8082/api/v1/evolution/metrics",
            timeout=10
        )
        
        if response.status_code == 200:
            metrics = response.json()
            print(f"✓ Retrieved evolution metrics")
            print(f"  Total agents: {metrics.get('total_agents', 0)}")
            print(f"  Total patterns: {metrics.get('total_patterns', 0)}")
            print(f"  Active trials: {metrics.get('active_trials', 0)}")
            print(f"  Average diversity: {metrics.get('average_diversity', 0):.3f}")
            return True
        else:
            print(f"✗ Failed to get metrics: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error getting database data: {e}")
        return False


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("DEAN System Integration Test")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Service Health", test_service_health()))
    
    if results[0][1]:  # Only continue if services are healthy
        results.append(("Agent Creation", test_create_agent() is not None))
        results.append(("Evolution Trial", test_evolution_trial() is not None))
        results.append(("Pattern Discovery", test_pattern_discovery()))
        results.append(("Token Economy", test_token_economy()))
        results.append(("Metrics Collection", test_metrics()))
        results.append(("Database Data", test_database_data()))
    else:
        print("\n✗ Skipping remaining tests - services not healthy")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:<20} {status}")
    
    print("-" * 60)
    print(f"Total: {total}, Passed: {passed}, Failed: {total - passed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    # Save results
    test_results = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": passed/total*100 if total > 0 else 0
        },
        "tests": {name: result for name, result in results}
    }
    
    with open("integration_test_results.json", "w") as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\nResults saved to: integration_test_results.json")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)