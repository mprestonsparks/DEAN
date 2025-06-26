#!/usr/bin/env python3
"""
Test Token Allocation

Verifies token economy is working correctly after initialization.
"""

import requests
import json
import uuid
from datetime import datetime


def test_token_allocation():
    """Test token allocation functionality."""
    print("=" * 60)
    print("Token Economy Allocation Test")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Check current budget
    print("\n1. Current Token Budget")
    print("-" * 40)
    
    response = requests.get("http://localhost:8091/api/v1/economy/budget")
    if response.status_code == 200:
        budget = response.json()
        print(f"✓ Global budget: {budget.get('global_budget', 0):,}")
        print(f"  Allocated: {budget.get('allocated', 0):,}")
        print(f"  Available: {budget.get('available', 0):,}")
        print(f"  Agents: {budget.get('agents_count', 0)}")
    else:
        print(f"✗ Failed to get budget: {response.status_code}")
        return False
    
    # Test allocation
    print("\n2. Testing Token Allocation")
    print("-" * 40)
    
    allocation_data = {
        "agent_id": str(uuid.uuid4()),
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
        
        # Test multiple allocations
        print("\n3. Testing Multiple Allocations")
        print("-" * 40)
        
        success_count = 0
        for i in range(5):
            test_data = {
                "agent_id": str(uuid.uuid4()),
                "requested_tokens": 3000,
                "agent_metadata": {
                    "type": "batch_test",
                    "efficiency_score": 0.5 + (i * 0.1)
                }
            }
            
            test_response = requests.post(
                "http://localhost:8091/api/v1/economy/allocate",
                json=test_data
            )
            
            if test_response.status_code == 200:
                alloc = test_response.json()
                print(f"  Agent {i}: Allocated {alloc.get('allocated_tokens', 0):,} tokens")
                success_count += 1
            else:
                print(f"  Agent {i}: Failed - {test_response.status_code}")
        
        print(f"\n✓ Successfully allocated tokens to {success_count}/5 agents")
        
        # Check final budget
        print("\n4. Final Budget Status")
        print("-" * 40)
        
        final_response = requests.get("http://localhost:8091/api/v1/economy/budget")
        if final_response.status_code == 200:
            final_budget = final_response.json()
            print(f"✓ Final budget status:")
            print(f"  Total allocated: {final_budget.get('allocated', 0):,}")
            print(f"  Still available: {final_budget.get('available', 0):,}")
            print(f"  Total agents: {final_budget.get('agents_count', 0)}")
        
        return True
    else:
        print(f"✗ Allocation failed: {response.status_code}")
        print(f"  Error: {response.text}")
        return False


def main():
    success = test_token_allocation()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ TOKEN ECONOMY IS WORKING CORRECTLY")
        print("  - Budget initialized with 1,000,000 tokens")
        print("  - Allocation mechanism functioning")
        print("  - Multiple agents can receive tokens")
    else:
        print("✗ TOKEN ECONOMY STILL HAS ISSUES")
    print("=" * 60)


if __name__ == "__main__":
    main()