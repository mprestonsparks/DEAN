#!/usr/bin/env python3
"""
Fixed Integration Test for DEAN Services

This test script aligns with the actual deployed API endpoints.
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
        "Evolution API": "http://localhost:8091/health",
        "Prometheus": "http://localhost:9090/-/healthy"
    }
    
    healthy_count = 0
    for name, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✓ {name}: Healthy")
                healthy_count += 1
            else:
                print(f"✗ {name}: Status {response.status_code}")
        except Exception as e:
            print(f"✗ {name}: {str(e)}")
    
    return healthy_count == len(services)


def test_create_agents():
    """Test agent creation using correct API."""
    print("\n2. Testing Agent Creation")
    print("-" * 40)
    
    agent_ids = []
    
    # Create agents using DEAN orchestrator
    for i in range(3):
        agent_data = {
            "goal": f"Test agent {i} for integration testing",
            "capabilities": ["analyze", "generate", "test"],
            "token_limit": 1000,
            "metadata": {
                "test_id": f"integration_test_{i}",
                "created_at": datetime.now().isoformat()
            }
        }
        
        try:
            response = requests.post(
                "http://localhost:8082/api/v1/agents/create",
                json=agent_data,
                timeout=10
            )
            
            if response.status_code == 200:
                agent = response.json()
                agent_id = agent.get("id")
                print(f"✓ Created agent {i}: {agent_id}")
                agent_ids.append(agent_id)
            else:
                print(f"✗ Failed to create agent {i}: {response.status_code}")
                print(f"  Error: {response.text[:200]}")
                
        except Exception as e:
            print(f"✗ Error creating agent {i}: {e}")
    
    return agent_ids


def test_evolution_trial(agent_ids):
    """Test evolution trial with created agents."""
    print("\n3. Testing Evolution Trial")
    print("-" * 40)
    
    if not agent_ids:
        print("✗ No agents available for evolution")
        return None
    
    evolution_config = {
        "name": "Integration Test Evolution",
        "agent_ids": agent_ids,
        "generations": 5,
        "population_size": len(agent_ids),
        "mutation_rate": 0.1,
        "crossover_rate": 0.7,
        "diversity_threshold": 0.3,
        "token_budget": 10000
    }
    
    try:
        # Start evolution via DEAN orchestrator
        response = requests.post(
            "http://localhost:8082/api/v1/evolution/start",
            json=evolution_config,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            evolution_id = result.get("evolution_id") or result.get("id")
            print(f"✓ Started evolution: {evolution_id}")
            
            # Monitor evolution progress
            print("\n  Monitoring evolution progress...")
            for generation in range(1, 6):
                time.sleep(3)  # Wait between checks
                
                try:
                    status_response = requests.get(
                        f"http://localhost:8082/api/v1/evolution/{evolution_id}/status",
                        timeout=10
                    )
                    
                    if status_response.status_code == 200:
                        status = status_response.json()
                        print(f"  Generation {generation}: ")
                        print(f"    - Status: {status.get('status', 'Unknown')}")
                        print(f"    - Best fitness: {status.get('best_fitness', 0):.4f}")
                        print(f"    - Diversity: {status.get('diversity', 0):.3f}")
                        print(f"    - Patterns found: {status.get('patterns_discovered', 0)}")
                    else:
                        print(f"  Generation {generation}: Unable to get status")
                        
                except Exception as e:
                    print(f"  Generation {generation}: Error - {e}")
            
            return evolution_id
            
        else:
            print(f"✗ Failed to start evolution: {response.status_code}")
            print(f"  Error: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"✗ Error running evolution: {e}")
        return None


def test_token_economy():
    """Test token economy enforcement."""
    print("\n4. Testing Token Economy")
    print("-" * 40)
    
    try:
        # Test token allocation through Evolution API
        allocation_data = {
            "agent_id": "test_economy_agent_1",
            "requested_tokens": 2000,
            "agent_metadata": {
                "type": "test",
                "efficiency_score": 0.8
            }
        }
        
        response = requests.post(
            "http://localhost:8091/api/v1/tokens/allocate",
            json=allocation_data,
            timeout=10
        )
        
        if response.status_code == 200:
            allocation = response.json()
            allocated = allocation.get("allocated_tokens", 0)
            print(f"✓ Allocated {allocated} tokens")
            print(f"  Efficiency multiplier: {allocation.get('efficiency_multiplier', 1):.2f}")
            print(f"  Remaining budget: {allocation.get('remaining_global_budget', 0)}")
            
            # Test budget exhaustion
            print("\n  Testing budget exhaustion...")
            allocated_count = 1
            rejected_count = 0
            
            for i in range(50):  # Try many allocations
                test_data = {
                    "agent_id": f"exhaustion_test_{i}",
                    "requested_tokens": 5000,
                    "agent_metadata": {"type": "exhaustion_test"}
                }
                
                test_response = requests.post(
                    "http://localhost:8091/api/v1/tokens/allocate",
                    json=test_data,
                    timeout=5
                )
                
                if test_response.status_code == 200:
                    allocated_count += 1
                else:
                    rejected_count += 1
                    if rejected_count == 1:
                        print(f"  First rejection at agent {i}")
            
            print(f"  Total allocated: {allocated_count}")
            print(f"  Total rejected: {rejected_count}")
            print(f"  ✓ Budget enforcement: {'Working' if rejected_count > 0 else 'Not enforced'}")
            
            return rejected_count > 0
        else:
            print(f"✗ Failed to allocate tokens: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing token economy: {e}")
        return False


def query_database_metrics():
    """Query database for evolution metrics."""
    print("\n5. Querying Database Metrics")
    print("-" * 40)
    
    try:
        # Query through DEAN API
        response = requests.get(
            "http://localhost:8082/api/v1/metrics/evolution",
            timeout=10
        )
        
        if response.status_code == 200:
            metrics = response.json()
            print("✓ Retrieved evolution metrics:")
            print(f"  Total agents created: {metrics.get('total_agents', 0)}")
            print(f"  Active agents: {metrics.get('active_agents', 0)}")
            print(f"  Total patterns discovered: {metrics.get('total_patterns', 0)}")
            print(f"  Average diversity: {metrics.get('average_diversity', 0):.3f}")
            print(f"  Token efficiency: {metrics.get('average_token_efficiency', 0):.4f}")
            print(f"  Evolution trials: {metrics.get('evolution_trials', 0)}")
            return True
        else:
            print(f"✗ Failed to get metrics: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error querying metrics: {e}")
        return False


def test_pattern_discovery():
    """Test pattern discovery functionality."""
    print("\n6. Testing Pattern Discovery")
    print("-" * 40)
    
    try:
        # Get patterns through IndexAgent
        response = requests.get(
            "http://localhost:8081/api/v1/patterns",
            timeout=10
        )
        
        if response.status_code == 200:
            patterns = response.json()
            pattern_count = len(patterns) if isinstance(patterns, list) else 0
            print(f"✓ Retrieved {pattern_count} patterns")
            
            if pattern_count > 0:
                # Analyze patterns
                valid_patterns = 0
                for pattern in patterns[:5]:  # Show first 5
                    if isinstance(pattern, dict):
                        effectiveness = pattern.get('effectiveness', 0)
                        if effectiveness >= 0.5:
                            valid_patterns += 1
                        print(f"  Pattern: {pattern.get('id', 'Unknown')[:8]}...")
                        print(f"    Type: {pattern.get('type', 'Unknown')}")
                        print(f"    Effectiveness: {effectiveness:.3f}")
                        print(f"    Discovered: {pattern.get('discovered_at', 'Unknown')}")
                
                print(f"\n  High-effectiveness patterns: {valid_patterns}")
            
            return pattern_count > 0
        else:
            print(f"✗ Failed to get patterns: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error getting patterns: {e}")
        return False


def check_prometheus_metrics():
    """Check Prometheus for DEAN metrics."""
    print("\n7. Checking Prometheus Metrics")
    print("-" * 40)
    
    try:
        # Query for DEAN metrics
        metrics_to_check = [
            "dean_agents_created_total",
            "dean_tokens_allocated_total",
            "dean_tokens_consumed_total",
            "dean_evolution_generations_total",
            "dean_patterns_discovered_total",
            "dean_population_diversity"
        ]
        
        found_metrics = []
        for metric in metrics_to_check:
            response = requests.get(
                f"http://localhost:9090/api/v1/query",
                params={"query": metric},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("data", {}).get("result"):
                    value = data["data"]["result"][0].get("value", [None, None])[1]
                    found_metrics.append((metric, value))
        
        print(f"✓ Found {len(found_metrics)}/{len(metrics_to_check)} DEAN metrics")
        for metric, value in found_metrics:
            print(f"  {metric}: {value}")
        
        return len(found_metrics) > 0
        
    except Exception as e:
        print(f"✗ Error checking Prometheus: {e}")
        return False


def main():
    """Run complete integration test."""
    print("=" * 80)
    print("DEAN System Integration Test")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 80)
    
    results = {}
    
    # Test 1: Service Health
    results["service_health"] = test_service_health()
    
    if not results["service_health"]:
        print("\n✗ Services not healthy - aborting remaining tests")
        return False
    
    # Test 2: Create Agents
    agent_ids = test_create_agents()
    results["agent_creation"] = len(agent_ids) > 0
    
    # Test 3: Evolution Trial
    evolution_id = test_evolution_trial(agent_ids)
    results["evolution_trial"] = evolution_id is not None
    
    # Test 4: Token Economy
    results["token_economy"] = test_token_economy()
    
    # Test 5: Database Metrics
    results["database_metrics"] = query_database_metrics()
    
    # Test 6: Pattern Discovery
    results["pattern_discovery"] = test_pattern_discovery()
    
    # Test 7: Prometheus Metrics
    results["prometheus_metrics"] = check_prometheus_metrics()
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:<20} {status}")
    
    print("-" * 80)
    print(f"Total: {total}, Passed: {passed}, Failed: {total - passed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    # Save results
    test_report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": passed/total*100 if total > 0 else 0
        },
        "results": results,
        "agent_ids": agent_ids if 'agent_ids' in locals() else [],
        "evolution_id": evolution_id if 'evolution_id' in locals() else None
    }
    
    with open("integration_test_report.json", "w") as f:
        json.dump(test_report, f, indent=2)
    
    print(f"\nDetailed report saved to: integration_test_report.json")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)