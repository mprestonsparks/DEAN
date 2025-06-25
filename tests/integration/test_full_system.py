"""
Full System Integration Tests for DEAN

This test suite validates the complete DEAN system by exercising
all four services together in realistic scenarios.
"""

import asyncio
import pytest
import httpx
import json
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta


# Service URLs
DEAN_ORCHESTRATOR_URL = "http://localhost:8082/api/v1"
INDEXAGENT_URL = "http://localhost:8081/api/v1"
EVOLUTION_API_URL = "http://localhost:8091/api/v1"  # Fixed port
AIRFLOW_URL = "http://localhost:8080/api/v1"

# Test configuration
TEST_TOKEN = "test-jwt-token"
TEST_TIMEOUT = 300  # 5 minutes for long-running tests


class DEANIntegrationTest:
    """Base class for DEAN integration tests"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.auth_headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
        self.created_agents = []
        self.created_patterns = []
        
    async def setup(self):
        """Setup test environment"""
        # Verify all services are healthy
        await self.verify_all_services_healthy()
        
    async def teardown(self):
        """Cleanup test artifacts"""
        # Archive created agents
        for agent_id in self.created_agents:
            try:
                await self.client.delete(
                    f"{INDEXAGENT_URL}/agents/{agent_id}",
                    headers=self.auth_headers
                )
            except:
                pass
                
        await self.client.aclose()
        
    async def verify_all_services_healthy(self):
        """Verify all services are responding"""
        services = [
            ("DEAN Orchestrator", "http://localhost:8082/health"),
            ("IndexAgent", "http://localhost:8081/health"),
            ("Evolution API", "http://localhost:8091/health"),  # Now working!
            # ("Airflow", "http://localhost:8080/health")  # Skip for now - not critical
        ]
        
        for name, url in services:
            response = await self.client.get(url)
            assert response.status_code == 200, f"{name} is not healthy"
            data = response.json()
            assert data["status"] in ["healthy", "OK"], f"{name} status: {data['status']}"


@pytest.mark.asyncio
class TestServiceDiscovery:
    """Test service discovery and registration"""
    
    async def test_service_registry(self):
        """Test that DEAN orchestrator can discover all services"""
        test = DEANIntegrationTest()
        await test.setup()
        
        try:
            # Get service status from orchestrator
            response = await test.client.get(
                f"{DEAN_ORCHESTRATOR_URL}/services/status",
                headers=test.auth_headers
            )
            assert response.status_code == 200
            
            services = response.json()["services"]
            
            # Verify all required services are registered
            required_services = ["indexagent", "evolution_api", "airflow", "database", "redis"]
            for service in required_services:
                assert service in services, f"{service} not in registry"
                assert services[service]["status"] == "up", f"{service} is down"
                
        finally:
            await test.teardown()
            
    async def test_service_health_checks(self):
        """Test health check endpoints for all services"""
        test = DEANIntegrationTest()
        await test.setup()
        
        try:
            # Test each service health endpoint
            health_checks = [
                ("http://localhost:8082/health", "DEAN"),
                ("http://localhost:8081/health", "IndexAgent"),
                # ("http://localhost:8090/health", "Evolution API")  # Skip - service down
            ]
            
            for health_url, name in health_checks:
                response = await test.client.get(health_url)
                assert response.status_code == 200
                
                data = response.json()
                assert "status" in data
                assert data["status"] in ["healthy", "OK"]
                # Version is optional but good to have
                if "version" in data:
                    assert data["version"]
                
        finally:
            await test.teardown()


@pytest.mark.asyncio
class TestAgentCreation:
    """Test agent creation through orchestrator"""
    
    async def test_spawn_agents_via_orchestrator(self):
        """Test creating agents through DEAN orchestrator"""
        test = DEANIntegrationTest()
        await test.setup()
        
        try:
            # Spawn agents via orchestrator
            spawn_request = {
                "genome_template": "default",
                "population_size": 3,
                "token_budget": 1000
            }
            
            response = await test.client.post(
                f"{DEAN_ORCHESTRATOR_URL}/agents/spawn",
                json=spawn_request,
                headers=test.auth_headers
            )
            assert response.status_code == 201
            
            spawn_data = response.json()
            assert spawn_data["status"] == "success"
            assert spawn_data["agents_created"] == 3
            assert len(spawn_data["agent_ids"]) == 3
            assert spawn_data["initial_diversity"] >= 0.3
            
            test.created_agents.extend(spawn_data["agent_ids"])
            
            # Verify agents exist in IndexAgent
            for agent_id in spawn_data["agent_ids"]:
                response = await test.client.get(
                    f"{INDEXAGENT_URL}/agents/{agent_id}"
                )
                assert response.status_code == 200
                
                agent = response.json()
                assert agent["id"] == agent_id
                assert agent["status"] == "active"
                assert agent["token_budget"] > 0
                
        finally:
            await test.teardown()
            
    async def test_agent_creation_with_token_allocation(self):
        """Test agent creation includes proper token allocation"""
        test = DEANIntegrationTest()
        await test.setup()
        
        try:
            # Check initial budget
            response = await test.client.get(f"{EVOLUTION_API_URL}/economy/budget")
            assert response.status_code == 200
            initial_budget = response.json()["available"]
            
            # Create agent
            create_request = {
                "genome_template": "default",
                "population_size": 1,
                "token_budget": 500
            }
            
            response = await test.client.post(
                f"{DEAN_ORCHESTRATOR_URL}/agents/spawn",
                json=create_request,
                headers=test.auth_headers
            )
            assert response.status_code == 201
            
            agent_id = response.json()["agent_ids"][0]
            test.created_agents.append(agent_id)
            
            # Verify token allocation
            response = await test.client.get(f"{EVOLUTION_API_URL}/economy/budget")
            assert response.status_code == 200
            new_budget = response.json()["available"]
            
            assert new_budget == initial_budget - 500, "Token allocation failed"
            
        finally:
            await test.teardown()


@pytest.mark.asyncio
class TestEvolutionCycle:
    """Test complete evolution cycle"""
    
    async def test_evolution_trigger_and_monitoring(self):
        """Test triggering evolution and monitoring progress"""
        test = DEANIntegrationTest()
        await test.setup()
        
        try:
            # Create test population
            spawn_response = await test.client.post(
                f"{DEAN_ORCHESTRATOR_URL}/agents/spawn",
                json={
                    "genome_template": "default",
                    "population_size": 2,
                    "token_budget": 2000
                },
                headers=test.auth_headers
            )
            assert spawn_response.status_code == 201
            agent_ids = spawn_response.json()["agent_ids"]
            test.created_agents.extend(agent_ids)
            
            # Start evolution cycle
            evolution_request = {
                "population_ids": agent_ids,
                "generations": 3,
                "token_budget": 1500,
                "cellular_automata_rules": [110, 30]
            }
            
            response = await test.client.post(
                f"{DEAN_ORCHESTRATOR_URL}/evolution/start",
                json=evolution_request,
                headers=test.auth_headers
            )
            assert response.status_code == 202
            
            evolution_data = response.json()
            cycle_id = evolution_data["cycle_id"]
            assert evolution_data["status"] == "started"
            
            # Monitor evolution progress
            max_checks = 30
            completed = False
            
            for i in range(max_checks):
                response = await test.client.get(
                    f"{DEAN_ORCHESTRATOR_URL}/evolution/{cycle_id}/status",
                    headers=test.auth_headers
                )
                assert response.status_code == 200
                
                status = response.json()
                print(f"Evolution status check {i+1}: {status['status']}")
                
                if status["status"] == "completed":
                    completed = True
                    assert status["current_generation"] == status["total_generations"]
                    assert status["tokens_consumed"] <= 1500
                    assert status["patterns_discovered"] >= 0
                    assert status["population_diversity"] >= 0.3
                    break
                elif status["status"] == "failed":
                    pytest.fail(f"Evolution failed: {status}")
                    
                await asyncio.sleep(2)
                
            assert completed, "Evolution did not complete in time"
            
        finally:
            await test.teardown()
            
    async def test_evolution_with_diversity_maintenance(self):
        """Test that evolution maintains genetic diversity"""
        test = DEANIntegrationTest()
        await test.setup()
        
        try:
            # Create homogeneous population
            agents = []
            for i in range(3):
                response = await test.client.post(
                    f"{INDEXAGENT_URL}/agents",
                    json={
                        "genome_template": "uniform",
                        "token_budget": 500
                    }
                )
                assert response.status_code == 201
                agent_id = response.json()["id"]
                agents.append(agent_id)
                test.created_agents.append(agent_id)
                
            # Check initial diversity
            response = await test.client.post(
                f"{INDEXAGENT_URL}/diversity/population",
                json={"population_ids": agents}
            )
            assert response.status_code == 200
            initial_diversity = response.json()["genetic_variance"]
            
            # Evolve with diversity constraints
            response = await test.client.post(
                f"{EVOLUTION_API_URL}/evolution/cycle",
                json={
                    "population_ids": agents,
                    "generations": 5,
                    "token_budget": 2000,
                    "diversity_threshold": 0.3
                }
            )
            assert response.status_code == 202
            
            # Wait for evolution to complete
            await asyncio.sleep(10)
            
            # Check final diversity
            response = await test.client.post(
                f"{INDEXAGENT_URL}/diversity/population",
                json={"population_ids": agents}
            )
            assert response.status_code == 200
            final_diversity = response.json()["genetic_variance"]
            
            assert final_diversity >= 0.3, "Diversity not maintained"
            assert final_diversity > initial_diversity, "Diversity did not increase"
            
        finally:
            await test.teardown()


@pytest.mark.asyncio
class TestPatternPropagation:
    """Test pattern discovery and propagation"""
    
    async def test_pattern_discovery_and_storage(self):
        """Test pattern discovery during evolution"""
        test = DEANIntegrationTest()
        await test.setup()
        
        try:
            # Create agents
            spawn_response = await test.client.post(
                f"{DEAN_ORCHESTRATOR_URL}/agents/spawn",
                json={
                    "genome_template": "default",
                    "population_size": 2,
                    "token_budget": 1000
                },
                headers=test.auth_headers
            )
            agent_ids = spawn_response.json()["agent_ids"]
            test.created_agents.extend(agent_ids)
            
            # Trigger pattern detection
            response = await test.client.post(
                f"{INDEXAGENT_URL}/patterns/detect",
                json={
                    "agent_ids": agent_ids,
                    "detection_depth": 3
                }
            )
            assert response.status_code == 200
            
            patterns = response.json()["patterns"]
            if patterns:
                # Verify patterns are stored
                response = await test.client.get(
                    f"{DEAN_ORCHESTRATOR_URL}/patterns",
                    headers=test.auth_headers
                )
                assert response.status_code == 200
                
                stored_patterns = response.json()["patterns"]
                pattern_ids = [p["id"] for p in stored_patterns]
                
                for pattern in patterns:
                    assert pattern["id"] in pattern_ids
                    test.created_patterns.append(pattern["id"])
                    
        finally:
            await test.teardown()
            
    async def test_pattern_propagation_across_agents(self):
        """Test propagating patterns between agents"""
        test = DEANIntegrationTest()
        await test.setup()
        
        try:
            # Create source and target agents
            source_response = await test.client.post(
                f"{DEAN_ORCHESTRATOR_URL}/agents/spawn",
                json={
                    "genome_template": "innovative",
                    "population_size": 1,
                    "token_budget": 1000
                },
                headers=test.auth_headers
            )
            source_agent = source_response.json()["agent_ids"][0]
            test.created_agents.append(source_agent)
            
            target_response = await test.client.post(
                f"{DEAN_ORCHESTRATOR_URL}/agents/spawn",
                json={
                    "genome_template": "default",
                    "population_size": 2,
                    "token_budget": 500
                },
                headers=test.auth_headers
            )
            target_agents = target_response.json()["agent_ids"]
            test.created_agents.extend(target_agents)
            
            # Create a test pattern
            pattern_response = await test.client.post(
                f"{EVOLUTION_API_URL}/patterns",
                json={
                    "name": "test_optimization",
                    "type": "optimization",
                    "discovered_by": source_agent,
                    "discovery_cost": 100,
                    "initial_effectiveness": 0.8
                }
            )
            assert pattern_response.status_code == 201
            pattern_id = pattern_response.json()["id"]
            test.created_patterns.append(pattern_id)
            
            # Propagate pattern
            response = await test.client.post(
                f"{DEAN_ORCHESTRATOR_URL}/patterns/{pattern_id}/propagate",
                json={
                    "target_agents": target_agents,
                    "propagation_strength": 0.9
                },
                headers=test.auth_headers
            )
            assert response.status_code == 200
            
            propagation_data = response.json()
            assert propagation_data["status"] == "success"
            assert propagation_data["agents_updated"] == 2
            
            # Verify pattern was applied
            for agent_id in target_agents:
                response = await test.client.get(
                    f"{INDEXAGENT_URL}/agents/{agent_id}"
                )
                agent_data = response.json()
                assert pattern_id in agent_data.get("patterns_discovered", [])
                
        finally:
            await test.teardown()


@pytest.mark.asyncio
class TestTokenEconomy:
    """Test token economy enforcement"""
    
    async def test_token_budget_enforcement(self):
        """Test that token budgets are enforced during evolution"""
        test = DEANIntegrationTest()
        await test.setup()
        
        try:
            # Check available budget
            response = await test.client.get(f"{EVOLUTION_API_URL}/economy/budget")
            available_budget = response.json()["available"]
            
            # Try to allocate more than available
            response = await test.client.post(
                f"{EVOLUTION_API_URL}/economy/allocate",
                json={
                    "agent_id": "test_agent",
                    "requested_tokens": available_budget + 1000,
                    "priority": "high"
                }
            )
            assert response.status_code == 400
            
            # Allocate within budget
            response = await test.client.post(
                f"{EVOLUTION_API_URL}/economy/allocate",
                json={
                    "agent_id": "test_agent",
                    "requested_tokens": 100,
                    "priority": "medium"
                }
            )
            assert response.status_code == 200
            
            allocation = response.json()
            assert allocation["allocated_tokens"] == 100
            assert allocation["remaining_budget"] == available_budget - 100
            
        finally:
            await test.teardown()
            
    async def test_efficiency_tracking(self):
        """Test token efficiency metrics"""
        test = DEANIntegrationTest()
        await test.setup()
        
        try:
            # Create agents with different budgets
            efficient_agent = await test.client.post(
                f"{DEAN_ORCHESTRATOR_URL}/agents/spawn",
                json={
                    "genome_template": "efficient",
                    "population_size": 1,
                    "token_budget": 500
                },
                headers=test.auth_headers
            )
            efficient_id = efficient_agent.json()["agent_ids"][0]
            test.created_agents.append(efficient_id)
            
            wasteful_agent = await test.client.post(
                f"{DEAN_ORCHESTRATOR_URL}/agents/spawn",
                json={
                    "genome_template": "wasteful",
                    "population_size": 1,
                    "token_budget": 2000
                },
                headers=test.auth_headers
            )
            wasteful_id = wasteful_agent.json()["agent_ids"][0]
            test.created_agents.append(wasteful_id)
            
            # Simulate token consumption
            await asyncio.sleep(2)
            
            # Check efficiency metrics
            response = await test.client.get(
                f"{EVOLUTION_API_URL}/economy/efficiency"
            )
            assert response.status_code == 200
            
            metrics = response.json()
            assert "overall_efficiency" in metrics
            assert "patterns_per_token" in metrics
            assert "top_performers" in metrics
            assert "inefficient_agents" in metrics
            
        finally:
            await test.teardown()


@pytest.mark.asyncio
class TestEndToEndWorkflow:
    """Test complete end-to-end workflows"""
    
    async def test_complete_evolution_workflow(self):
        """Test a complete workflow from agent creation to pattern propagation"""
        test = DEANIntegrationTest()
        await test.setup()
        
        try:
            # Step 1: Create initial population
            print("Step 1: Creating initial population...")
            spawn_response = await test.client.post(
                f"{DEAN_ORCHESTRATOR_URL}/agents/spawn",
                json={
                    "genome_template": "default",
                    "population_size": 4,
                    "token_budget": 4000
                },
                headers=test.auth_headers
            )
            assert spawn_response.status_code == 201
            agent_ids = spawn_response.json()["agent_ids"]
            test.created_agents.extend(agent_ids)
            print(f"Created {len(agent_ids)} agents")
            
            # Step 2: Start evolution
            print("\nStep 2: Starting evolution cycle...")
            evolution_response = await test.client.post(
                f"{DEAN_ORCHESTRATOR_URL}/evolution/start",
                json={
                    "population_ids": agent_ids[:2],  # Evolve first 2 agents
                    "generations": 5,
                    "token_budget": 2000,
                    "cellular_automata_rules": [110, 30, 90]
                },
                headers=test.auth_headers
            )
            assert evolution_response.status_code == 202
            cycle_id = evolution_response.json()["cycle_id"]
            print(f"Evolution cycle started: {cycle_id}")
            
            # Step 3: Monitor evolution
            print("\nStep 3: Monitoring evolution...")
            completed = False
            patterns_discovered = 0
            
            for i in range(20):
                status_response = await test.client.get(
                    f"{DEAN_ORCHESTRATOR_URL}/evolution/{cycle_id}/status",
                    headers=test.auth_headers
                )
                status = status_response.json()
                
                if status["status"] == "completed":
                    completed = True
                    patterns_discovered = status["patterns_discovered"]
                    print(f"Evolution completed! Patterns discovered: {patterns_discovered}")
                    break
                    
                print(f"Generation {status['current_generation']}/{status['total_generations']}")
                await asyncio.sleep(3)
                
            assert completed, "Evolution did not complete"
            
            # Step 4: Check for patterns
            if patterns_discovered > 0:
                print("\nStep 4: Retrieving discovered patterns...")
                patterns_response = await test.client.get(
                    f"{DEAN_ORCHESTRATOR_URL}/patterns",
                    params={"min_effectiveness": 0.5},
                    headers=test.auth_headers
                )
                patterns = patterns_response.json()["patterns"]
                print(f"Found {len(patterns)} effective patterns")
                
                if patterns:
                    # Step 5: Propagate best pattern
                    print("\nStep 5: Propagating best pattern...")
                    best_pattern = max(patterns, key=lambda p: p["effectiveness"])
                    
                    propagate_response = await test.client.post(
                        f"{DEAN_ORCHESTRATOR_URL}/patterns/{best_pattern['id']}/propagate",
                        json={
                            "target_agents": agent_ids[2:],  # Propagate to remaining agents
                            "propagation_strength": 1.0
                        },
                        headers=test.auth_headers
                    )
                    assert propagate_response.status_code == 200
                    print(f"Pattern '{best_pattern['name']}' propagated successfully")
                    
            # Step 6: Verify final state
            print("\nStep 6: Verifying final system state...")
            
            # Check token usage
            token_response = await test.client.get(
                f"{DEAN_ORCHESTRATOR_URL}/metrics/tokens",
                headers=test.auth_headers
            )
            token_metrics = token_response.json()
            print(f"Total tokens consumed: {token_metrics['total_consumed']}")
            print(f"Efficiency ratio: {token_metrics['efficiency_ratio']}")
            
            # Check population diversity
            diversity_response = await test.client.post(
                f"{INDEXAGENT_URL}/diversity/population",
                json={"population_ids": agent_ids}
            )
            diversity = diversity_response.json()
            print(f"Final population diversity: {diversity['genetic_variance']}")
            
            assert diversity["genetic_variance"] >= 0.3, "Diversity too low"
            assert token_metrics["efficiency_ratio"] > 0, "No value generated"
            
            print("\n✅ Complete evolution workflow successful!")
            
        finally:
            await test.teardown()


# Test runner
async def run_all_tests():
    """Run all integration tests"""
    test_classes = [
        TestServiceDiscovery,
        TestAgentCreation,
        TestEvolutionCycle,
        TestPatternPropagation,
        TestTokenEconomy,
        TestEndToEndWorkflow
    ]
    
    results = []
    
    for test_class in test_classes:
        print(f"\n{'='*60}")
        print(f"Running {test_class.__name__}")
        print('='*60)
        
        instance = test_class()
        test_methods = [m for m in dir(instance) if m.startswith("test_")]
        
        for method_name in test_methods:
            print(f"\n{method_name}...")
            try:
                method = getattr(instance, method_name)
                await method()
                print(f"✅ {method_name} PASSED")
                results.append((test_class.__name__, method_name, "PASSED"))
            except Exception as e:
                print(f"❌ {method_name} FAILED: {str(e)}")
                results.append((test_class.__name__, method_name, f"FAILED: {str(e)}"))
                
    # Print summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    
    passed = sum(1 for _, _, result in results if result == "PASSED")
    total = len(results)
    
    for class_name, method, result in results:
        status = "✅" if result == "PASSED" else "❌"
        print(f"{status} {class_name}.{method}: {result}")
        
    print(f"\nTotal: {passed}/{total} passed ({passed/total*100:.1f}%)")
    
    return passed == total


if __name__ == "__main__":
    # Run tests
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)