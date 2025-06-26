#!/usr/bin/env python3
"""
Final Integration Test for DEAN System

Tests the actual deployed services with correct endpoints.
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


def test_indexagent_operations():
    """Test IndexAgent agent management."""
    print("\n2. Testing IndexAgent Operations")
    print("-" * 40)
    
    # Create an agent
    agent_data = {
        "goal": "Test agent for integration verification",
        "model": "claude-3-sonnet",
        "capabilities": ["analyze", "generate", "test"],
        "token_limit": 2000,
        "genome": {
            "traits": {
                "exploration": 0.6,
                "efficiency": 0.7,
                "learning_rate": 0.1
            },
            "strategies": ["baseline", "explore"]
        }
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
            
            # Get agent details
            detail_response = requests.get(
                f"http://localhost:8081/api/v1/agents/{agent_id}",
                timeout=5
            )
            
            if detail_response.status_code == 200:
                details = detail_response.json()
                print(f"  Fitness: {details.get('fitness', 0):.4f}")
                print(f"  Token budget: {details.get('token_budget', 0)}")
                print(f"  Created: {details.get('created_at', 'Unknown')}")
            
            return agent_id
        else:
            print(f"✗ Failed to create agent: {response.status_code}")
            print(f"  Error: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def test_evolution_api():
    """Test Evolution API functionality."""
    print("\n3. Testing Evolution API")
    print("-" * 40)
    
    # Check global budget
    try:
        response = requests.get(
            "http://localhost:8091/api/v1/economy/budget",
            timeout=5
        )
        
        if response.status_code == 200:
            budget = response.json()
            print(f"✓ Global token budget: {budget.get('total_budget', 0)}")
            print(f"  Used: {budget.get('used_budget', 0)}")
            print(f"  Remaining: {budget.get('remaining_budget', 0)}")
            
            # Test token allocation
            allocation_data = {
                "agent_id": "test_allocation_agent",
                "requested_tokens": 1000,
                "agent_metadata": {
                    "efficiency_score": 0.8,
                    "generation": 1
                }
            }
            
            alloc_response = requests.post(
                "http://localhost:8091/api/v1/economy/allocate",
                json=allocation_data,
                timeout=10
            )
            
            if alloc_response.status_code == 200:
                allocation = alloc_response.json()
                print(f"\n✓ Token allocation successful")
                print(f"  Allocated: {allocation.get('allocated_tokens', 0)}")
                print(f"  Efficiency bonus: {allocation.get('efficiency_multiplier', 1):.2f}")
                return True
            else:
                print(f"\n✗ Token allocation failed: {alloc_response.status_code}")
                return False
        else:
            print(f"✗ Failed to get budget: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_evolution_cycle():
    """Test running an evolution cycle."""
    print("\n4. Testing Evolution Cycle")
    print("-" * 40)
    
    # Get existing agents
    try:
        response = requests.get(
            "http://localhost:8081/api/v1/agents",
            timeout=5
        )
        
        if response.status_code == 200:
            agents = response.json()
            
            # Handle both list and dict response formats
            if isinstance(agents, dict) and "agents" in agents:
                agent_list = agents["agents"]
            elif isinstance(agents, list):
                agent_list = agents
            else:
                print("✗ Unexpected agent list format")
                return None
            
            print(f"✓ Found {len(agent_list)} existing agents")
            
            if len(agent_list) >= 2:
                # Start evolution with existing agents
                agent_ids = [a["id"] for a in agent_list[:3]]
                
                evolution_data = {
                    "agent_ids": agent_ids,
                    "generations": 3,
                    "mutation_rate": 0.1,
                    "crossover_rate": 0.7,
                    "population_size": len(agent_ids)
                }
                
                start_response = requests.post(
                    "http://localhost:8091/api/v1/evolution/start",
                    json=evolution_data,
                    timeout=10
                )
                
                if start_response.status_code == 200:
                    result = start_response.json()
                    cycle_id = result.get("cycle_id")
                    print(f"✓ Started evolution cycle: {cycle_id}")
                    
                    # Monitor progress
                    print("\n  Monitoring evolution...")
                    for i in range(3):
                        time.sleep(2)
                        
                        status_response = requests.get(
                            f"http://localhost:8091/api/v1/evolution/{cycle_id}/status",
                            timeout=5
                        )
                        
                        if status_response.status_code == 200:
                            status = status_response.json()
                            print(f"  Generation {i+1}:")
                            print(f"    Status: {status.get('status', 'Unknown')}")
                            print(f"    Progress: {status.get('progress', 0):.1%}")
                            print(f"    Best fitness: {status.get('best_fitness', 0):.4f}")
                        else:
                            print(f"  Generation {i+1}: Unable to get status")
                    
                    return cycle_id
                else:
                    print(f"✗ Failed to start evolution: {start_response.status_code}")
                    print(f"  Error: {start_response.text[:200]}")
                    return None
            else:
                print("✗ Not enough agents for evolution")
                return None
        else:
            print(f"✗ Failed to list agents: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def test_pattern_discovery():
    """Test pattern discovery functionality."""
    print("\n5. Testing Pattern Discovery")
    print("-" * 40)
    
    try:
        # Get discovered patterns
        response = requests.get(
            "http://localhost:8081/api/v1/patterns/discovered",
            timeout=10
        )
        
        if response.status_code == 200:
            patterns = response.json()
            
            # Handle both list and dict response formats
            if isinstance(patterns, dict) and "patterns" in patterns:
                pattern_list = patterns["patterns"]
            elif isinstance(patterns, list):
                pattern_list = patterns
            else:
                pattern_list = []
            
            print(f"✓ Retrieved {len(pattern_list)} patterns")
            
            if len(pattern_list) > 0:
                # Analyze patterns
                print("\n  Pattern Analysis:")
                valid_count = 0
                for i, pattern in enumerate(pattern_list[:3]):
                    effectiveness = pattern.get('effectiveness', 0)
                    improvement = pattern.get('performance_improvement', 0)
                    
                    if effectiveness >= 0.5:
                        valid_count += 1
                    
                    print(f"  Pattern {i+1}:")
                    print(f"    Type: {pattern.get('type', 'Unknown')}")
                    print(f"    Effectiveness: {effectiveness:.3f}")
                    print(f"    Performance gain: {improvement:.1%}")
                
                print(f"\n  High-effectiveness patterns: {valid_count}/{len(pattern_list)}")
            
            return len(pattern_list) > 0
        else:
            print(f"✗ Failed to get patterns: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_diversity_check():
    """Test diversity maintenance."""
    print("\n6. Testing Diversity Check")
    print("-" * 40)
    
    try:
        # Get agent population for diversity check
        agents_response = requests.get(
            "http://localhost:8081/api/v1/agents",
            timeout=5
        )
        
        if agents_response.status_code == 200:
            agents = agents_response.json()
            
            # Extract agent list
            if isinstance(agents, dict) and "agents" in agents:
                agent_list = agents["agents"]
            elif isinstance(agents, list):
                agent_list = agents
            else:
                agent_list = []
            
            if len(agent_list) >= 2:
                # Check diversity
                diversity_data = {
                    "agent_ids": [a["id"] for a in agent_list[:5]],
                    "threshold": 0.3
                }
                
                response = requests.post(
                    "http://localhost:8091/api/v1/diversity/check",
                    json=diversity_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    diversity = result.get('diversity_score', 0)
                    print(f"✓ Population diversity: {diversity:.3f}")
                    print(f"  Status: {result.get('status', 'Unknown')}")
                    print(f"  Above threshold: {diversity >= 0.3}")
                    
                    if result.get('recommendations'):
                        print(f"  Recommendations: {result['recommendations']}")
                    
                    return diversity >= 0.3
                else:
                    print(f"✗ Failed to check diversity: {response.status_code}")
                    return False
            else:
                print("✗ Not enough agents for diversity check")
                return False
        else:
            print(f"✗ Failed to get agents: {agents_response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_metrics_endpoints():
    """Test metrics collection."""
    print("\n7. Testing Metrics Endpoints")
    print("-" * 40)
    
    metrics_found = 0
    
    # Check DEAN metrics
    try:
        response = requests.get("http://localhost:8082/metrics", timeout=5)
        if response.status_code == 200:
            print("✓ DEAN metrics endpoint active")
            metrics_found += 1
    except:
        print("✗ DEAN metrics endpoint not available")
    
    # Check IndexAgent metrics
    try:
        response = requests.get("http://localhost:8081/metrics", timeout=5)
        if response.status_code == 200:
            print("✓ IndexAgent metrics endpoint active")
            metrics_found += 1
    except:
        print("✗ IndexAgent metrics endpoint not available")
    
    # Check efficiency metrics
    try:
        response = requests.get(
            "http://localhost:8081/api/v1/metrics/efficiency",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Efficiency metrics:")
            print(f"  Average efficiency: {data.get('average_efficiency', 0):.4f}")
            print(f"  Total value generated: {data.get('total_value', 0):.2f}")
            print(f"  Total tokens consumed: {data.get('total_tokens', 0)}")
            metrics_found += 1
    except:
        print("✗ Efficiency metrics not available")
    
    return metrics_found >= 2


def main():
    """Run complete integration test."""
    print("=" * 80)
    print("DEAN System Final Integration Test")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 80)
    
    results = {}
    
    # Test 1: Service Health
    results["service_health"] = test_service_health()
    
    if not results["service_health"]:
        print("\n✗ Services not healthy - aborting remaining tests")
        return False
    
    # Test 2: IndexAgent Operations
    agent_id = test_indexagent_operations()
    results["agent_operations"] = agent_id is not None
    
    # Test 3: Evolution API
    results["evolution_api"] = test_evolution_api()
    
    # Test 4: Evolution Cycle
    cycle_id = test_evolution_cycle()
    results["evolution_cycle"] = cycle_id is not None
    
    # Test 5: Pattern Discovery
    results["pattern_discovery"] = test_pattern_discovery()
    
    # Test 6: Diversity Check
    results["diversity_check"] = test_diversity_check()
    
    # Test 7: Metrics
    results["metrics_endpoints"] = test_metrics_endpoints()
    
    # Summary
    print("\n" + "=" * 80)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:<20} {status}")
    
    print("-" * 80)
    print(f"Total: {total}, Passed: {passed}, Failed: {total - passed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    # Save detailed report
    test_report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": passed/total*100 if total > 0 else 0
        },
        "results": results,
        "system_info": {
            "agent_created": agent_id if 'agent_id' in locals() else None,
            "evolution_cycle": cycle_id if 'cycle_id' in locals() else None
        }
    }
    
    with open("final_integration_report.json", "w") as f:
        json.dump(test_report, f, indent=2)
    
    print(f"\nDetailed report saved to: final_integration_report.json")
    
    # Print acceptance criteria results
    print("\n" + "=" * 80)
    print("ACCEPTANCE CRITERIA VALIDATION")
    print("=" * 80)
    print(f"1. Services deployed: {'✓ YES' if results['service_health'] else '✗ NO'}")
    print(f"2. Database initialized: {'✓ YES (agents exist)' if results['agent_operations'] else '✗ NO'}")
    print(f"3. Integration tests pass: {'✓ YES' if passed >= 5 else '✗ NO'}")
    print(f"4. Evolution runs: {'✓ YES' if results.get('evolution_cycle', False) else '✗ NO'}")
    print(f"5. Metrics observable: {'✓ YES' if results['metrics_endpoints'] else '✗ NO'}")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)