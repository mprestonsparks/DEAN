#!/usr/bin/env python3
"""
End-to-End Integration Test for Deployed DEAN Services

This script tests the actual deployed services via their APIs.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, List, Any


class E2EIntegrationTest:
    """Tests deployed DEAN services end-to-end."""
    
    def __init__(self):
        self.orchestrator_url = "http://localhost:8082"
        self.indexagent_url = "http://localhost:8081"
        self.token_economy_url = "http://localhost:8091"
        
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "services": {},
            "summary": {}
        }
    
    async def check_service_health(self, name: str, url: str) -> bool:
        """Check if a service is healthy."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        self.results["services"][name] = {
                            "healthy": True,
                            "data": data
                        }
                        return True
        except Exception as e:
            self.results["services"][name] = {
                "healthy": False,
                "error": str(e)
            }
        return False
    
    async def test_all_services_healthy(self):
        """Test that all services are healthy."""
        print("\n1. Testing Service Health...")
        
        services = [
            ("DEAN Orchestrator", self.orchestrator_url),
            ("IndexAgent", self.indexagent_url),
            ("Token Economy", self.token_economy_url)
        ]
        
        health_results = []
        for name, url in services:
            healthy = await self.check_service_health(name, url)
            print(f"  {name}: {'✓' if healthy else '✗'}")
            health_results.append(healthy)
        
        all_healthy = all(health_results)
        self.results["tests"]["service_health"] = {
            "passed": all_healthy,
            "message": f"{sum(health_results)}/{len(services)} services healthy"
        }
        
        return all_healthy
    
    async def test_create_evolution_trial(self):
        """Test creating an evolution trial via orchestrator."""
        print("\n2. Testing Evolution Trial Creation...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Create evolution trial
                trial_data = {
                    "population_size": 3,
                    "generations": 5,
                    "token_budget": 10000,
                    "diversity_threshold": 0.3
                }
                
                async with session.post(
                    f"{self.orchestrator_url}/api/v1/evolution/start",
                    json=trial_data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        trial_id = result.get("trial_id")
                        print(f"  Created trial: {trial_id}")
                        
                        self.results["tests"]["create_trial"] = {
                            "passed": True,
                            "trial_id": trial_id,
                            "data": result
                        }
                        return trial_id
                    else:
                        error = await response.text()
                        print(f"  Failed to create trial: {error}")
                        self.results["tests"]["create_trial"] = {
                            "passed": False,
                            "error": error
                        }
                        
        except Exception as e:
            print(f"  Error: {e}")
            self.results["tests"]["create_trial"] = {
                "passed": False,
                "error": str(e)
            }
            
        return None
    
    async def test_agent_operations(self):
        """Test agent creation and evolution."""
        print("\n3. Testing Agent Operations...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Create an agent
                agent_data = {
                    "genome": {
                        "traits": {
                            "exploration": 0.5,
                            "efficiency": 0.5,
                            "learning_rate": 0.1
                        },
                        "strategies": ["baseline"]
                    },
                    "token_budget": 1000
                }
                
                async with session.post(
                    f"{self.indexagent_url}/api/v1/agents",
                    json=agent_data
                ) as response:
                    if response.status == 200:
                        agent = await response.json()
                        agent_id = agent.get("id")
                        print(f"  Created agent: {agent_id}")
                        
                        # Test agent evolution
                        evolve_data = {
                            "generations": 3,
                            "mutation_rate": 0.1
                        }
                        
                        async with session.post(
                            f"{self.indexagent_url}/api/v1/agents/{agent_id}/evolve",
                            json=evolve_data
                        ) as evolve_response:
                            if evolve_response.status == 200:
                                evolution_result = await evolve_response.json()
                                print(f"  Evolution completed: {evolution_result.get('status')}")
                                
                                self.results["tests"]["agent_operations"] = {
                                    "passed": True,
                                    "agent_id": agent_id,
                                    "evolution": evolution_result
                                }
                                return True
                    
        except Exception as e:
            print(f"  Error: {e}")
            
        self.results["tests"]["agent_operations"] = {
            "passed": False,
            "error": "Failed to create/evolve agent"
        }
        return False
    
    async def test_pattern_discovery(self):
        """Test pattern discovery functionality."""
        print("\n4. Testing Pattern Discovery...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Get discovered patterns
                async with session.get(
                    f"{self.indexagent_url}/api/v1/patterns/discovered"
                ) as response:
                    if response.status == 200:
                        patterns = await response.json()
                        pattern_count = len(patterns) if isinstance(patterns, list) else 0
                        
                        print(f"  Found {pattern_count} patterns")
                        
                        # Check if any patterns have required improvement
                        valid_patterns = [
                            p for p in patterns 
                            if isinstance(p, dict) and 
                            p.get("performance_improvement", 0) >= 0.2
                        ] if isinstance(patterns, list) else []
                        
                        print(f"  Valid patterns (20%+ improvement): {len(valid_patterns)}")
                        
                        self.results["tests"]["pattern_discovery"] = {
                            "passed": pattern_count > 0,
                            "total_patterns": pattern_count,
                            "valid_patterns": len(valid_patterns)
                        }
                        return pattern_count > 0
                        
        except Exception as e:
            print(f"  Error: {e}")
            
        self.results["tests"]["pattern_discovery"] = {
            "passed": False,
            "error": "Failed to retrieve patterns"
        }
        return False
    
    async def test_token_economy(self):
        """Test token economy enforcement."""
        print("\n5. Testing Token Economy...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test token allocation
                allocation_data = {
                    "agent_id": "test_economy_agent",
                    "requested_tokens": 5000
                }
                
                async with session.post(
                    f"{self.token_economy_url}/api/v1/tokens/allocate",
                    json=allocation_data
                ) as response:
                    if response.status == 200:
                        allocation = await response.json()
                        allocated = allocation.get("allocated_tokens", 0)
                        print(f"  Allocated {allocated} tokens")
                        
                        # Test budget exhaustion
                        exhaustion_results = []
                        for i in range(5):
                            test_data = {
                                "agent_id": f"exhaustion_test_{i}",
                                "requested_tokens": 3000
                            }
                            
                            async with session.post(
                                f"{self.token_economy_url}/api/v1/tokens/allocate",
                                json=test_data
                            ) as test_response:
                                if test_response.status == 200:
                                    exhaustion_results.append("allocated")
                                else:
                                    exhaustion_results.append("rejected")
                        
                        rejected_count = exhaustion_results.count("rejected")
                        print(f"  Budget exhaustion test: {rejected_count}/5 agents rejected")
                        
                        self.results["tests"]["token_economy"] = {
                            "passed": rejected_count > 0,
                            "initial_allocation": allocated,
                            "exhaustion_test": exhaustion_results
                        }
                        return rejected_count > 0
                        
        except Exception as e:
            print(f"  Error: {e}")
            
        self.results["tests"]["token_economy"] = {
            "passed": False,
            "error": "Failed to test token economy"
        }
        return False
    
    async def test_metrics_collection(self):
        """Test Prometheus metrics collection."""
        print("\n6. Testing Metrics Collection...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Check Prometheus metrics
                async with session.get("http://localhost:9090/api/v1/query?query=up") as response:
                    if response.status == 200:
                        metrics = await response.json()
                        active_targets = len(metrics.get("data", {}).get("result", []))
                        print(f"  Active Prometheus targets: {active_targets}")
                        
                        # Check DEAN-specific metrics
                        dean_metrics = [
                            "dean_agents_created_total",
                            "dean_tokens_allocated_total",
                            "dean_evolution_duration_seconds"
                        ]
                        
                        found_metrics = []
                        for metric in dean_metrics:
                            async with session.get(
                                f"http://localhost:9090/api/v1/query?query={metric}"
                            ) as metric_response:
                                if metric_response.status == 200:
                                    data = await metric_response.json()
                                    if data.get("data", {}).get("result"):
                                        found_metrics.append(metric)
                        
                        print(f"  DEAN metrics found: {len(found_metrics)}/{len(dean_metrics)}")
                        
                        self.results["tests"]["metrics_collection"] = {
                            "passed": len(found_metrics) > 0,
                            "prometheus_targets": active_targets,
                            "dean_metrics": found_metrics
                        }
                        return len(found_metrics) > 0
                        
        except Exception as e:
            print(f"  Error: {e}")
            
        self.results["tests"]["metrics_collection"] = {
            "passed": False,
            "error": "Failed to check metrics"
        }
        return False
    
    async def run_all_tests(self):
        """Run all integration tests."""
        print("=" * 60)
        print("DEAN End-to-End Integration Test")
        print("=" * 60)
        
        # Run tests
        test_results = []
        
        # Check services
        test_results.append(await self.test_all_services_healthy())
        
        # Only proceed if services are healthy
        if test_results[0]:
            test_results.append(await self.test_create_evolution_trial() is not None)
            test_results.append(await self.test_agent_operations())
            test_results.append(await self.test_pattern_discovery())
            test_results.append(await self.test_token_economy())
            test_results.append(await self.test_metrics_collection())
        else:
            print("\nSkipping remaining tests - services not healthy")
            test_results.extend([False] * 5)
        
        # Summary
        passed = sum(1 for r in test_results if r)
        total = len(test_results)
        
        self.results["summary"] = {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": (passed / total * 100) if total > 0 else 0
        }
        
        print("\n" + "=" * 60)
        print("E2E TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ✓")
        print(f"Failed: {total - passed} ✗")
        print(f"Success Rate: {self.results['summary']['success_rate']:.1f}%")
        
        # Save results
        with open("e2e_test_results.json", "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\nDetailed results saved to: e2e_test_results.json")
        
        return self.results


async def main():
    """Run E2E integration test."""
    test = E2EIntegrationTest()
    results = await test.run_all_tests()
    
    # Exit with appropriate code
    if results["summary"]["failed"] > 0:
        exit(1)
    else:
        exit(0)


if __name__ == "__main__":
    asyncio.run(main())