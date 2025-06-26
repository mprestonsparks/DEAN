#!/usr/bin/env python3
"""
Test actual endpoints available in deployed services.
"""

import requests
import json
import time
from datetime import datetime


def discover_endpoints():
    """Discover available endpoints from OpenAPI docs."""
    print("\nDiscovering Available Endpoints")
    print("=" * 60)
    
    services = {
        "DEAN Orchestrator": "http://localhost:8082",
        "IndexAgent": "http://localhost:8081",
        "Evolution API": "http://localhost:8091"
    }
    
    for name, base_url in services.items():
        print(f"\n{name}:")
        try:
            # Try to get OpenAPI spec
            response = requests.get(f"{base_url}/openapi.json", timeout=5)
            if response.status_code == 200:
                spec = response.json()
                paths = spec.get("paths", {})
                print(f"  Found {len(paths)} endpoints:")
                for path, methods in paths.items():
                    for method in methods:
                        if method in ["get", "post", "put", "delete"]:
                            print(f"    {method.upper():6} {path}")
            else:
                print(f"  No OpenAPI spec found")
        except Exception as e:
            print(f"  Error: {e}")


def test_orchestrator_endpoints():
    """Test DEAN Orchestrator specific endpoints."""
    print("\n\nTesting DEAN Orchestrator Endpoints")
    print("=" * 60)
    
    base_url = "http://localhost:8082"
    
    # Test evolution trial creation with correct schema
    print("\n1. Create Evolution Trial")
    trial_data = {
        "name": "Test Evolution Trial",
        "description": "Integration test trial",
        "config": {
            "population_size": 3,
            "generations": 5,
            "mutation_rate": 0.1,
            "crossover_rate": 0.7,
            "tournament_size": 3,
            "elitism_count": 1,
            "diversity_threshold": 0.3
        },
        "constraints": {
            "max_token_budget": 10000,
            "max_runtime_seconds": 300,
            "min_fitness_improvement": 0.01
        }
    }
    
    response = requests.post(f"{base_url}/api/v1/trials", json=trial_data)
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"  Trial ID: {result.get('id')}")
        print(f"  Status: {result.get('status')}")
        return result.get('id')
    else:
        print(f"  Error: {response.text[:200]}")
        return None


def test_indexagent_endpoints():
    """Test IndexAgent specific endpoints."""
    print("\n\nTesting IndexAgent Endpoints")
    print("=" * 60)
    
    base_url = "http://localhost:8081"
    
    # Test agent listing
    print("\n1. List Agents")
    response = requests.get(f"{base_url}/api/v1/agents")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        agents = response.json()
        print(f"  Found {len(agents)} agents")
        if agents:
            print(f"  Example agent: {agents[0].get('id')}")
    
    # Test pattern retrieval
    print("\n2. Get Patterns")
    response = requests.get(f"{base_url}/api/v1/patterns")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        patterns = response.json()
        print(f"  Found {len(patterns)} patterns")


def test_evolution_api_endpoints():
    """Test Evolution API endpoints."""
    print("\n\nTesting Evolution API Endpoints")
    print("=" * 60)
    
    base_url = "http://localhost:8091"
    
    # Test evolution status
    print("\n1. Evolution Status")
    response = requests.get(f"{base_url}/api/v1/evolution/status")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        status = response.json()
        print(f"  Active evolutions: {status.get('active_evolutions', 0)}")
        print(f"  Total generations: {status.get('total_generations', 0)}")
    
    # Test metrics
    print("\n2. Evolution Metrics")
    response = requests.get(f"{base_url}/api/v1/metrics")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        metrics = response.json()
        print(f"  Token efficiency: {metrics.get('average_token_efficiency', 0):.3f}")
        print(f"  Pattern count: {metrics.get('discovered_patterns', 0)}")


def test_websocket_monitoring():
    """Test WebSocket monitoring capabilities."""
    print("\n\nTesting Real-time Monitoring")
    print("=" * 60)
    
    # Check if WebSocket endpoints exist
    print("\n1. WebSocket Endpoints Available:")
    print("  ws://localhost:8082/ws/evolution/{trial_id} - Evolution monitoring")
    print("  ws://localhost:8082/ws/agents/{agent_id} - Agent monitoring")
    print("  ws://localhost:8081/ws/patterns - Pattern discovery stream")
    
    # Note: Actually connecting to WebSockets requires websockets library
    print("\n  (WebSocket testing requires additional libraries)")


def test_prometheus_metrics():
    """Test actual Prometheus metrics."""
    print("\n\nTesting Prometheus Metrics")
    print("=" * 60)
    
    # Query for any metrics with 'dean' prefix
    response = requests.get(
        "http://localhost:9090/api/v1/label/__name__/values"
    )
    
    if response.status_code == 200:
        all_metrics = response.json().get("data", [])
        dean_metrics = [m for m in all_metrics if "dean" in m.lower()]
        
        print(f"\nFound {len(dean_metrics)} DEAN-related metrics:")
        for metric in dean_metrics[:10]:  # Show first 10
            print(f"  - {metric}")
            
        # Get sample values
        if dean_metrics:
            sample_metric = dean_metrics[0]
            value_response = requests.get(
                f"http://localhost:9090/api/v1/query?query={sample_metric}"
            )
            if value_response.status_code == 200:
                data = value_response.json()
                results = data.get("data", {}).get("result", [])
                if results:
                    print(f"\nSample value for {sample_metric}:")
                    print(f"  Value: {results[0].get('value', ['', ''])[1]}")


def test_actual_evolution():
    """Run a real evolution test with correct API calls."""
    print("\n\nRunning Actual Evolution Test")
    print("=" * 60)
    
    # Step 1: Create agents via IndexAgent
    print("\n1. Creating test agents...")
    agent_ids = []
    
    for i in range(3):
        agent_data = {
            "id": f"test_agent_{i}_{int(time.time())}",
            "goal": "Optimize test function",
            "capabilities": ["analyze", "generate", "test"],
            "model": "test-model",
            "token_limit": 1000
        }
        
        response = requests.post(
            "http://localhost:8081/api/v1/agents",
            json=agent_data
        )
        
        if response.status_code == 200:
            agent = response.json()
            agent_ids.append(agent["id"])
            print(f"  Created agent: {agent['id']}")
        else:
            print(f"  Failed to create agent: {response.status_code}")
    
    if not agent_ids:
        print("  No agents created, skipping evolution")
        return
    
    # Step 2: Trigger evolution
    print("\n2. Starting evolution process...")
    evolution_data = {
        "agent_ids": agent_ids,
        "generations": 3,
        "config": {
            "mutation_rate": 0.1,
            "crossover_rate": 0.7,
            "selection_pressure": 0.5
        }
    }
    
    response = requests.post(
        "http://localhost:8091/api/v1/evolution/start",
        json=evolution_data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"  Evolution started: {result.get('evolution_id')}")
        
        # Wait and check progress
        print("\n3. Monitoring evolution progress...")
        time.sleep(5)
        
        status_response = requests.get(
            f"http://localhost:8091/api/v1/evolution/{result.get('evolution_id')}/status"
        )
        
        if status_response.status_code == 200:
            status = status_response.json()
            print(f"  Current generation: {status.get('current_generation', 0)}")
            print(f"  Best fitness: {status.get('best_fitness', 0):.4f}")
            print(f"  Population diversity: {status.get('diversity', 0):.3f}")
    else:
        print(f"  Failed to start evolution: {response.status_code}")
        print(f"  Error: {response.text[:200]}")


def main():
    """Run all endpoint tests."""
    print("=" * 80)
    print("DEAN System Endpoint Discovery and Testing")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 80)
    
    # Discover available endpoints
    discover_endpoints()
    
    # Test specific service endpoints
    test_orchestrator_endpoints()
    test_indexagent_endpoints()
    test_evolution_api_endpoints()
    
    # Test monitoring capabilities
    test_websocket_monitoring()
    test_prometheus_metrics()
    
    # Run actual evolution test
    test_actual_evolution()
    
    print("\n" + "=" * 80)
    print("Testing Complete")
    print("=" * 80)


if __name__ == "__main__":
    main()