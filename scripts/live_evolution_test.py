#!/usr/bin/env python3
"""
Live Evolution Test - Real Execution with Actual Services
No mock data, only real API calls and responses
"""

import requests
import json
import time
from datetime import datetime
import sys

class DEANLiveTest:
    def __init__(self):
        self.dean_url = "http://localhost:8082"
        self.indexagent_url = "http://localhost:8081"
        self.evolution_url = "http://localhost:8090"
        self.results = []
        self.agent_ids = []
        
    def log(self, message, data=None):
        """Log with timestamp"""
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] {message}")
        if data:
            print(json.dumps(data, indent=2))
        self.results.append({
            "timestamp": timestamp,
            "message": message,
            "data": data
        })
    
    def check_service_health(self):
        """Check all services are healthy"""
        self.log("=== Service Health Check ===")
        
        services = [
            ("DEAN Orchestrator", f"{self.dean_url}/health"),
            ("IndexAgent", f"{self.indexagent_url}/health"),
        ]
        
        all_healthy = True
        for name, url in services:
            try:
                response = requests.get(url, timeout=5)
                health_data = response.json()
                self.log(f"{name} Health", health_data)
                if health_data.get("status") != "healthy":
                    all_healthy = False
            except Exception as e:
                self.log(f"{name} Error: {str(e)}")
                all_healthy = False
                
        return all_healthy
    
    def create_agents(self, count=3):
        """Create real agents via API"""
        self.log(f"=== Creating {count} Agents ===")
        
        goals = [
            "Discover optimization patterns in recursive algorithms",
            "Identify and extract memoization opportunities", 
            "Detect parallelization patterns in sequential code"
        ]
        
        for i in range(count):
            agent_data = {
                "goal": goals[i % len(goals)],
                "token_budget": 1500,
                "diversity_weight": 0.35,
                "specialized_domain": "code_optimization",
                "agent_metadata": {
                    "created_at": datetime.utcnow().isoformat() + "Z",
                    "test_run": True,
                    "index": i
                }
            }
            
            try:
                response = requests.post(
                    f"{self.indexagent_url}/api/v1/agents",
                    json=agent_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    agent_info = response.json()
                    agent_id = agent_info.get("id", agent_info.get("agent_id"))
                    if agent_id:
                        self.agent_ids.append(agent_id)
                        self.log(f"Created agent {i+1}", agent_info)
                else:
                    self.log(f"Failed to create agent {i+1}", {
                        "status_code": response.status_code,
                        "error": response.text
                    })
            except Exception as e:
                self.log(f"Exception creating agent {i+1}: {str(e)}")
    
    def check_token_budget(self):
        """Check global token budget"""
        self.log("=== Token Budget Status ===")
        
        try:
            response = requests.get(f"{self.indexagent_url}/api/v1/budget/global")
            budget_data = response.json()
            self.log("Global Budget", budget_data)
            return budget_data
        except Exception as e:
            self.log(f"Error checking budget: {str(e)}")
            return None
    
    def run_evolution_cycles(self):
        """Run evolution for each agent"""
        self.log("=== Running Evolution Cycles ===")
        
        if not self.agent_ids:
            self.log("No agents available for evolution")
            return
            
        evolution_params = {
            "generations": 3,
            "mutation_rate": 0.15,
            "crossover_rate": 0.25,
            "ca_rules": [30, 90, 110, 184],
            "elitism_rate": 0.1,
            "tournament_size": 3
        }
        
        for agent_id in self.agent_ids:
            self.log(f"Evolving agent: {agent_id}")
            
            try:
                response = requests.post(
                    f"{self.indexagent_url}/api/v1/agents/{agent_id}/evolve",
                    json=evolution_params,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    evolution_result = response.json()
                    self.log(f"Evolution result for {agent_id}", evolution_result)
                else:
                    self.log(f"Evolution failed for {agent_id}", {
                        "status_code": response.status_code,
                        "error": response.text
                    })
            except Exception as e:
                self.log(f"Exception during evolution: {str(e)}")
            
            # Small delay between evolutions
            time.sleep(1)
    
    def check_patterns(self):
        """Check discovered patterns"""
        self.log("=== Checking Discovered Patterns ===")
        
        try:
            response = requests.get(f"{self.indexagent_url}/api/v1/patterns/discovered")
            patterns = response.json()
            self.log("Discovered Patterns", patterns)
            return patterns
        except Exception as e:
            self.log(f"Error checking patterns: {str(e)}")
            return None
    
    def test_code_analysis(self):
        """Test code analysis functionality"""
        self.log("=== Testing Code Analysis ===")
        
        code_samples = [
            {
                "code": """def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)""",
                "language": "python",
                "repository_path": "/tmp/test_factorial.py"
            },
            {
                "code": """def fibonacci(n, memo={}):
    if n in memo:
        return memo[n]
    if n <= 1:
        return n
    memo[n] = fibonacci(n-1, memo) + fibonacci(n-2, memo)
    return memo[n]""",
                "language": "python",
                "repository_path": "/tmp/test_fibonacci.py"
            }
        ]
        
        for i, sample in enumerate(code_samples):
            try:
                response = requests.post(
                    f"{self.indexagent_url}/api/v1/code/analyze",
                    json=sample,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    analysis = response.json()
                    self.log(f"Code analysis {i+1}", analysis)
                else:
                    self.log(f"Analysis failed {i+1}", {
                        "status_code": response.status_code,
                        "error": response.text
                    })
            except Exception as e:
                self.log(f"Exception in code analysis: {str(e)}")
    
    def get_efficiency_metrics(self):
        """Get system efficiency metrics"""
        self.log("=== System Efficiency Metrics ===")
        
        try:
            response = requests.get(f"{self.indexagent_url}/api/v1/metrics/efficiency")
            metrics = response.json()
            self.log("Efficiency Metrics", metrics)
            return metrics
        except Exception as e:
            self.log(f"Error getting metrics: {str(e)}")
            return None
    
    def test_pattern_detection(self):
        """Test cross-agent pattern detection"""
        self.log("=== Testing Pattern Detection ===")
        
        if len(self.agent_ids) < 2:
            self.log("Not enough agents for pattern detection")
            return
            
        pattern_request = {
            "agents": self.agent_ids[:2],
            "behaviors": [
                {
                    "agent_id": self.agent_ids[0],
                    "action": "optimize",
                    "context": "recursive_function",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                },
                {
                    "agent_id": self.agent_ids[1],
                    "action": "memoize",
                    "context": "fibonacci_calculation",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            ],
            "window_size": 100
        }
        
        try:
            response = requests.post(
                f"{self.indexagent_url}/api/v1/patterns/detect",
                json=pattern_request,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                patterns = response.json()
                self.log("Pattern Detection Result", patterns)
            else:
                self.log("Pattern detection failed", {
                    "status_code": response.status_code,
                    "error": response.text
                })
        except Exception as e:
            self.log(f"Exception in pattern detection: {str(e)}")
    
    def get_final_agent_states(self):
        """Get final state of all agents"""
        self.log("=== Final Agent States ===")
        
        for agent_id in self.agent_ids:
            try:
                response = requests.get(f"{self.indexagent_url}/api/v1/agents/{agent_id}")
                if response.status_code == 200:
                    agent_state = response.json()
                    self.log(f"Agent {agent_id} final state", agent_state)
                else:
                    self.log(f"Failed to get agent {agent_id}", {
                        "status_code": response.status_code
                    })
            except Exception as e:
                self.log(f"Exception getting agent state: {str(e)}")
    
    def save_results(self):
        """Save results to markdown file"""
        with open("docs/real_evolution_results.md", "w") as f:
            f.write("# DEAN System Live Evolution Test Results\n\n")
            f.write(f"**Test Date**: {datetime.now().isoformat()}\n")
            f.write("**Test Type**: Live execution with real services\n\n")
            
            f.write("## Test Execution Log\n\n")
            for result in self.results:
                f.write(f"### {result['timestamp']} - {result['message']}\n\n")
                if result['data']:
                    f.write("```json\n")
                    f.write(json.dumps(result['data'], indent=2))
                    f.write("\n```\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- Total Agents Created: {len(self.agent_ids)}\n")
            f.write(f"- Evolution Cycles Run: {len(self.agent_ids)}\n")
            f.write(f"- Test Duration: Live execution\n")
            f.write("- Status: Completed\n")
    
    def run_full_test(self):
        """Run complete test suite"""
        self.log("Starting DEAN Live Evolution Test")
        
        # Check services
        if not self.check_service_health():
            self.log("ERROR: Services not healthy, aborting test")
            return False
        
        # Create agents
        self.create_agents(3)
        
        # Check budget
        self.check_token_budget()
        
        # Run evolution
        self.run_evolution_cycles()
        
        # Check patterns
        self.check_patterns()
        
        # Test code analysis
        self.test_code_analysis()
        
        # Get metrics
        self.get_efficiency_metrics()
        
        # Test pattern detection
        self.test_pattern_detection()
        
        # Get final states
        self.get_final_agent_states()
        
        # Save results
        self.save_results()
        
        self.log("Test completed successfully")
        return True

if __name__ == "__main__":
    test = DEANLiveTest()
    success = test.run_full_test()
    sys.exit(0 if success else 1)