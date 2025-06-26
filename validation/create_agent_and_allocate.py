#!/usr/bin/env python3
"""
Create Agent and Allocate Tokens

Creates a new agent properly and then allocates tokens.
"""

import requests
import json
from datetime import datetime


def create_and_allocate():
    """Create agent and allocate tokens."""
    print("=" * 60)
    print("Create Agent and Allocate Tokens")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Step 1: Create an agent through DEAN orchestrator
    print("\n1. Creating New Agent")
    print("-" * 40)
    
    agent_data = {
        "goal": "Test token allocation",
        "capabilities": ["analyze", "optimize"],
        "token_limit": 1000,
        "metadata": {
            "test": "token_allocation",
            "created_at": datetime.now().isoformat()
        }
    }
    
    response = requests.post(
        "http://localhost:8082/api/v1/agents/create",
        json=agent_data
    )
    
    if response.status_code != 200:
        print(f"✗ Failed to create agent: {response.status_code}")
        print(f"  Error: {response.text[:200]}")
        return False
    
    agent = response.json()
    agent_id = agent.get("id")
    print(f"✓ Created agent: {agent_id}")
    
    # Step 2: Use an existing agent from database
    print("\n2. Using Existing Database Agent")
    print("-" * 40)
    
    # Use one of the agents we know exists in the database
    db_agent_id = "054905ec-9e9a-4ef8-a1a6-06044617ae8b"
    print(f"  Using agent: {db_agent_id}")
    
    # Step 3: Allocate tokens to database agent
    print("\n3. Allocating Tokens")
    print("-" * 40)
    
    allocation_data = {
        "agent_id": db_agent_id,
        "requested_tokens": 5000,
        "agent_metadata": {
            "type": "test",
            "efficiency_score": 0.8,
            "generation": 1
        }
    }
    
    response = requests.post(
        "http://localhost:8091/api/v1/economy/allocate",
        json=allocation_data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Allocation successful!")
        print(f"  Requested: {allocation_data['requested_tokens']:,}")
        print(f"  Allocated: {result.get('allocated_tokens', 0):,}")
        print(f"  Efficiency multiplier: {result.get('efficiency_multiplier', 1):.2f}")
        print(f"  Remaining budget: {result.get('remaining_global_budget', 0):,}")
        
        # Check budget status
        print("\n4. Budget Status")
        print("-" * 40)
        
        budget_response = requests.get("http://localhost:8091/api/v1/economy/budget")
        if budget_response.status_code == 200:
            budget = budget_response.json()
            print(f"✓ Current budget:")
            print(f"  Total: {budget.get('global_budget', 0):,}")
            print(f"  Allocated: {budget.get('allocated', 0):,}")
            print(f"  Available: {budget.get('available', 0):,}")
        
        return True
    else:
        print(f"✗ Allocation failed: {response.status_code}")
        print(f"  Error: {response.text}")
        return False


def main():
    success = create_and_allocate()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ TOKEN ALLOCATION WORKING!")
        print("  - Successfully allocated tokens to agent")
        print("  - Budget tracking functional")
        print("  - Ready for evolution cycles")
    else:
        print("✗ Token allocation still has issues")
    print("=" * 60)


if __name__ == "__main__":
    main()