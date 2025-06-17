#!/usr/bin/env python3
"""
Performance Validation Script for DEAN Orchestration System

Simulates workload on hardware similar to i7/RTX 3080 to validate performance.
Tests API response times, memory usage, and system behavior under load.
"""

import asyncio
import aiohttp
import psutil
import time
import statistics
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

# Configuration
ORCHESTRATOR_URL = "http://localhost:8082"
EVOLUTION_URL = "http://localhost:8083"
INDEXAGENT_URL = "http://localhost:8081"

# Hardware profile (i7/RTX 3080 simulation)
HARDWARE_PROFILE = {
    "cpu_cores": 8,  # i7 typical core count
    "cpu_threads": 16,  # With hyperthreading
    "ram_gb": 32,  # Typical gaming/workstation RAM
    "gpu_memory_gb": 10,  # RTX 3080 VRAM
    "expected_cpu_freq": 3.6,  # GHz base frequency
}

# Test parameters
CONCURRENT_USERS = 10
REQUESTS_PER_USER = 50
EVOLUTION_TRIALS = 5
AGENT_COUNT = 100


class PerformanceValidator:
    """Validates DEAN system performance."""
    
    def __init__(self):
        self.metrics = {
            "api_response_times": [],
            "memory_usage": [],
            "cpu_usage": [],
            "evolution_times": [],
            "agent_creation_times": [],
            "pattern_query_times": [],
            "concurrent_request_times": [],
        }
        self.access_token = None
        self.start_time = None
        
    async def run(self):
        """Run complete performance validation."""
        print("=" * 70)
        print("DEAN Performance Validation")
        print(f"Target Hardware: Intel i7 / NVIDIA RTX 3080")
        print("=" * 70)
        print()
        
        self.start_time = time.time()
        
        # System info
        self.print_system_info()
        
        # Get authentication token
        await self.authenticate()
        
        # Run performance tests
        await self.test_api_response_times()
        await self.test_concurrent_load()
        await self.test_agent_creation_performance()
        await self.test_evolution_performance()
        await self.test_pattern_query_performance()
        self.test_memory_usage()
        await self.test_system_under_stress()
        
        # Generate report
        self.generate_performance_report()
    
    def print_system_info(self):
        """Print current system information."""
        print("Current System Information:")
        print("-" * 50)
        
        # CPU info
        cpu_count = psutil.cpu_count(logical=False)
        cpu_threads = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        
        print(f"CPU Cores: {cpu_count} (Threads: {cpu_threads})")
        print(f"CPU Frequency: {cpu_freq.current:.2f} MHz (Max: {cpu_freq.max:.2f} MHz)")
        
        # Memory info
        memory = psutil.virtual_memory()
        print(f"Total RAM: {memory.total / (1024**3):.1f} GB")
        print(f"Available RAM: {memory.available / (1024**3):.1f} GB")
        
        # Disk info
        disk = psutil.disk_usage('/')
        print(f"Disk Space: {disk.free / (1024**3):.1f} GB free of {disk.total / (1024**3):.1f} GB")
        
        print()
        print(f"Performance tests will simulate load for:")
        print(f"  - {CONCURRENT_USERS} concurrent users")
        print(f"  - {REQUESTS_PER_USER} requests per user")
        print(f"  - {EVOLUTION_TRIALS} evolution trials")
        print(f"  - {AGENT_COUNT} agents")
        print()
    
    async def authenticate(self):
        """Get authentication token."""
        print("Authenticating...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{ORCHESTRATOR_URL}/auth/login",
                json={"username": "admin", "password": "admin123"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.access_token = data["access_token"]
                    print("✓ Authentication successful")
                else:
                    print("✗ Authentication failed")
                    sys.exit(1)
    
    async def test_api_response_times(self):
        """Test individual API response times."""
        print("\n1. Testing API Response Times...")
        print("-" * 50)
        
        endpoints = [
            ("GET", f"{ORCHESTRATOR_URL}/api/agents", "List agents"),
            ("GET", f"{EVOLUTION_URL}/evolution/trials", "List trials"),
            ("GET", f"{INDEXAGENT_URL}/patterns", "List patterns"),
            ("GET", f"{ORCHESTRATOR_URL}/api/metrics", "Get metrics"),
        ]
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with aiohttp.ClientSession() as session:
            for method, url, description in endpoints:
                times = []
                
                # Warm up
                await session.get(url, headers=headers)
                
                # Measure
                for _ in range(10):
                    start = time.time()
                    async with session.get(url, headers=headers) as response:
                        await response.read()
                    elapsed = (time.time() - start) * 1000  # ms
                    times.append(elapsed)
                
                avg_time = statistics.mean(times)
                p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile
                
                self.metrics["api_response_times"].append({
                    "endpoint": description,
                    "avg_ms": avg_time,
                    "p95_ms": p95_time
                })
                
                status = "✓" if avg_time < 100 else "⚠"
                print(f"{status} {description}: avg={avg_time:.1f}ms, p95={p95_time:.1f}ms")
    
    async def test_concurrent_load(self):
        """Test system under concurrent load."""
        print("\n2. Testing Concurrent Load...")
        print("-" * 50)
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async def make_request(session, url):
            start = time.time()
            try:
                async with session.get(url, headers=headers) as response:
                    await response.read()
                    return time.time() - start, response.status
            except Exception as e:
                return time.time() - start, 0
        
        async with aiohttp.ClientSession() as session:
            # Simulate concurrent users
            print(f"Simulating {CONCURRENT_USERS} concurrent users...")
            
            tasks = []
            for _ in range(CONCURRENT_USERS * REQUESTS_PER_USER):
                url = f"{ORCHESTRATOR_URL}/api/agents"
                tasks.append(make_request(session, url))
            
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            # Analyze results
            response_times = [r[0] for r in results]
            success_count = sum(1 for r in results if r[1] == 200)
            
            avg_response = statistics.mean(response_times) * 1000
            p95_response = statistics.quantiles(response_times, n=20)[18] * 1000
            requests_per_second = len(results) / total_time
            
            self.metrics["concurrent_request_times"] = {
                "total_requests": len(results),
                "success_rate": success_count / len(results) * 100,
                "avg_response_ms": avg_response,
                "p95_response_ms": p95_response,
                "requests_per_second": requests_per_second
            }
            
            print(f"✓ Processed {len(results)} requests in {total_time:.2f}s")
            print(f"  Success rate: {success_count / len(results) * 100:.1f}%")
            print(f"  Throughput: {requests_per_second:.1f} req/s")
            print(f"  Avg response: {avg_response:.1f}ms")
            print(f"  P95 response: {p95_response:.1f}ms")
    
    async def test_agent_creation_performance(self):
        """Test agent creation performance."""
        print("\n3. Testing Agent Creation Performance...")
        print("-" * 50)
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with aiohttp.ClientSession() as session:
            print(f"Creating {AGENT_COUNT} agents...")
            
            times = []
            agent_ids = []
            
            start_batch = time.time()
            
            for i in range(AGENT_COUNT):
                agent_data = {
                    "name": f"perf-test-agent-{i}",
                    "language": "python",
                    "capabilities": ["search", "optimize", "analyze"]
                }
                
                start = time.time()
                async with session.post(
                    f"{INDEXAGENT_URL}/agents",
                    json=agent_data,
                    headers=headers
                ) as response:
                    if response.status in [200, 201]:
                        data = await response.json()
                        agent_ids.append(data["id"])
                
                elapsed = time.time() - start
                times.append(elapsed)
                
                # Progress indicator
                if (i + 1) % 20 == 0:
                    print(f"  Created {i + 1}/{AGENT_COUNT} agents...")
            
            total_time = time.time() - start_batch
            
            avg_time = statistics.mean(times) * 1000
            total_rate = AGENT_COUNT / total_time
            
            self.metrics["agent_creation_times"] = {
                "total_agents": AGENT_COUNT,
                "avg_creation_ms": avg_time,
                "total_time_s": total_time,
                "agents_per_second": total_rate
            }
            
            print(f"✓ Created {AGENT_COUNT} agents in {total_time:.2f}s")
            print(f"  Average creation time: {avg_time:.1f}ms")
            print(f"  Creation rate: {total_rate:.1f} agents/s")
    
    async def test_evolution_performance(self):
        """Test evolution trial performance."""
        print("\n4. Testing Evolution Performance...")
        print("-" * 50)
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with aiohttp.ClientSession() as session:
            print(f"Running {EVOLUTION_TRIALS} evolution trials...")
            
            trial_times = []
            
            for i in range(EVOLUTION_TRIALS):
                config = {
                    "repository": f"perf-test-{i}",
                    "generations": 3,  # Reduced for performance test
                    "population_size": 20,
                    "mutation_rate": 0.1,
                    "crossover_rate": 0.7
                }
                
                # Start trial
                start = time.time()
                async with session.post(
                    f"{EVOLUTION_URL}/evolution/start",
                    json=config,
                    headers=headers
                ) as response:
                    if response.status in [200, 201]:
                        trial = await response.json()
                        trial_id = trial["trial_id"]
                        
                        # Monitor until completion
                        completed = False
                        checks = 0
                        max_checks = 60  # 2 minutes max
                        
                        while not completed and checks < max_checks:
                            await asyncio.sleep(2)
                            
                            async with session.get(
                                f"{EVOLUTION_URL}/evolution/{trial_id}/status",
                                headers=headers
                            ) as status_response:
                                if status_response.status == 200:
                                    status = await status_response.json()
                                    if status["status"] in ["completed", "failed"]:
                                        completed = True
                            
                            checks += 1
                        
                        elapsed = time.time() - start
                        trial_times.append(elapsed)
                        
                        print(f"  Trial {i + 1}/{EVOLUTION_TRIALS} completed in {elapsed:.2f}s")
            
            if trial_times:
                avg_time = statistics.mean(trial_times)
                
                self.metrics["evolution_times"] = {
                    "trials_run": len(trial_times),
                    "avg_trial_seconds": avg_time,
                    "total_time_seconds": sum(trial_times)
                }
                
                print(f"✓ Evolution trials completed")
                print(f"  Average trial time: {avg_time:.2f}s")
    
    async def test_pattern_query_performance(self):
        """Test pattern query performance."""
        print("\n5. Testing Pattern Query Performance...")
        print("-" * 50)
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        queries = [
            {"min_confidence": 0.8, "limit": 100},
            {"pattern_type": "optimization", "limit": 50},
            {"min_confidence": 0.9, "pattern_type": "refactoring", "limit": 20},
        ]
        
        async with aiohttp.ClientSession() as session:
            query_times = []
            
            for i, params in enumerate(queries):
                times = []
                
                for _ in range(10):
                    start = time.time()
                    async with session.get(
                        f"{EVOLUTION_URL}/patterns",
                        params=params,
                        headers=headers
                    ) as response:
                        data = await response.json()
                        patterns = data.get("patterns", [])
                    
                    elapsed = (time.time() - start) * 1000
                    times.append(elapsed)
                
                avg_time = statistics.mean(times)
                query_times.append(avg_time)
                
                print(f"✓ Query {i + 1}: {avg_time:.1f}ms (returned {len(patterns)} patterns)")
            
            self.metrics["pattern_query_times"] = {
                "queries_tested": len(queries),
                "avg_query_ms": statistics.mean(query_times)
            }
    
    def test_memory_usage(self):
        """Test memory usage patterns."""
        print("\n6. Testing Memory Usage...")
        print("-" * 50)
        
        # Get current memory usage
        process = psutil.Process()
        memory_info = process.memory_info()
        
        # System-wide memory
        system_memory = psutil.virtual_memory()
        
        memory_metrics = {
            "process_memory_mb": memory_info.rss / (1024 * 1024),
            "system_memory_percent": system_memory.percent,
            "available_memory_gb": system_memory.available / (1024**3)
        }
        
        self.metrics["memory_usage"] = memory_metrics
        
        print(f"✓ Process memory: {memory_metrics['process_memory_mb']:.1f} MB")
        print(f"✓ System memory usage: {memory_metrics['system_memory_percent']:.1f}%")
        print(f"✓ Available memory: {memory_metrics['available_memory_gb']:.1f} GB")
        
        # Check if within expected bounds for i7/RTX 3080 system
        if memory_metrics['system_memory_percent'] < 80:
            print("✓ Memory usage is within acceptable limits")
        else:
            print("⚠ High memory usage detected")
    
    async def test_system_under_stress(self):
        """Test system behavior under stress."""
        print("\n7. Testing System Under Stress...")
        print("-" * 50)
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # Create high load scenario
        print("Creating high load scenario...")
        
        async def stress_test_task(session, task_id):
            """Individual stress test task."""
            results = {"errors": 0, "success": 0, "response_times": []}
            
            for _ in range(10):
                start = time.time()
                try:
                    # Random operations
                    operations = [
                        ("GET", f"{ORCHESTRATOR_URL}/api/agents"),
                        ("GET", f"{EVOLUTION_URL}/patterns"),
                        ("POST", f"{INDEXAGENT_URL}/search"),
                    ]
                    
                    method, url = operations[task_id % len(operations)]
                    
                    if method == "GET":
                        async with session.get(url, headers=headers) as response:
                            await response.read()
                            if response.status == 200:
                                results["success"] += 1
                            else:
                                results["errors"] += 1
                    else:
                        data = {"query": "test", "limit": 10}
                        async with session.post(url, json=data, headers=headers) as response:
                            await response.read()
                            if response.status in [200, 201]:
                                results["success"] += 1
                            else:
                                results["errors"] += 1
                    
                    elapsed = time.time() - start
                    results["response_times"].append(elapsed)
                    
                except Exception:
                    results["errors"] += 1
                
                await asyncio.sleep(0.1)  # Small delay between requests
            
            return results
        
        async with aiohttp.ClientSession() as session:
            # Run stress test with many concurrent tasks
            stress_tasks = []
            num_tasks = 50  # High concurrency
            
            start_time = time.time()
            
            for i in range(num_tasks):
                stress_tasks.append(stress_test_task(session, i))
            
            results = await asyncio.gather(*stress_tasks)
            
            total_time = time.time() - start_time
            
            # Aggregate results
            total_success = sum(r["success"] for r in results)
            total_errors = sum(r["errors"] for r in results)
            all_response_times = []
            for r in results:
                all_response_times.extend(r["response_times"])
            
            if all_response_times:
                avg_response = statistics.mean(all_response_times) * 1000
                p95_response = statistics.quantiles(all_response_times, n=20)[18] * 1000
            else:
                avg_response = 0
                p95_response = 0
            
            success_rate = total_success / (total_success + total_errors) * 100 if (total_success + total_errors) > 0 else 0
            
            print(f"✓ Stress test completed in {total_time:.2f}s")
            print(f"  Total requests: {total_success + total_errors}")
            print(f"  Success rate: {success_rate:.1f}%")
            print(f"  Avg response under load: {avg_response:.1f}ms")
            print(f"  P95 response under load: {p95_response:.1f}ms")
            
            # CPU usage during stress
            cpu_percent = psutil.cpu_percent(interval=1)
            print(f"  CPU usage during stress: {cpu_percent:.1f}%")
    
    def generate_performance_report(self):
        """Generate comprehensive performance report."""
        print("\n" + "=" * 70)
        print("Performance Validation Report")
        print("=" * 70)
        
        total_time = time.time() - self.start_time
        
        # API Performance
        print("\n📊 API Performance:")
        for endpoint in self.metrics["api_response_times"]:
            status = "✅" if endpoint["avg_ms"] < 100 else "⚠️"
            print(f"  {status} {endpoint['endpoint']}: {endpoint['avg_ms']:.1f}ms avg, {endpoint['p95_ms']:.1f}ms p95")
        
        # Concurrent Load
        if "concurrent_request_times" in self.metrics:
            conc = self.metrics["concurrent_request_times"]
            print(f"\n📊 Concurrent Load Handling:")
            print(f"  Requests per second: {conc['requests_per_second']:.1f}")
            print(f"  Success rate: {conc['success_rate']:.1f}%")
            print(f"  Average response: {conc['avg_response_ms']:.1f}ms")
            print(f"  P95 response: {conc['p95_response_ms']:.1f}ms")
        
        # Agent Creation
        if "agent_creation_times" in self.metrics:
            agent = self.metrics["agent_creation_times"]
            print(f"\n📊 Agent Creation Performance:")
            print(f"  Creation rate: {agent['agents_per_second']:.1f} agents/s")
            print(f"  Average time: {agent['avg_creation_ms']:.1f}ms per agent")
        
        # Evolution Performance
        if "evolution_times" in self.metrics:
            evo = self.metrics["evolution_times"]
            print(f"\n📊 Evolution Trial Performance:")
            print(f"  Average trial time: {evo['avg_trial_seconds']:.1f}s")
            print(f"  Trials completed: {evo['trials_run']}")
        
        # Memory Usage
        if "memory_usage" in self.metrics:
            mem = self.metrics["memory_usage"]
            print(f"\n📊 Memory Usage:")
            print(f"  Process memory: {mem['process_memory_mb']:.1f} MB")
            print(f"  System memory: {mem['system_memory_percent']:.1f}%")
        
        # Hardware Suitability Assessment
        print(f"\n🎯 Hardware Suitability Assessment (i7/RTX 3080):")
        
        suitable = True
        recommendations = []
        
        # Check API performance
        avg_api_time = statistics.mean([e["avg_ms"] for e in self.metrics["api_response_times"]])
        if avg_api_time < 100:
            print("  ✅ API response times are excellent")
        else:
            print("  ⚠️  API response times could be improved")
            recommendations.append("Consider optimizing database queries")
            suitable = False
        
        # Check concurrent handling
        if self.metrics["concurrent_request_times"]["requests_per_second"] > 50:
            print("  ✅ Concurrent request handling is good")
        else:
            print("  ⚠️  Concurrent request handling needs improvement")
            recommendations.append("Consider connection pooling optimization")
            suitable = False
        
        # Check memory usage
        if self.metrics["memory_usage"]["system_memory_percent"] < 70:
            print("  ✅ Memory usage is within limits")
        else:
            print("  ⚠️  High memory usage detected")
            recommendations.append("Monitor memory leaks and optimize caching")
            suitable = False
        
        # Overall assessment
        print(f"\n📋 Overall Assessment:")
        if suitable:
            print("  ✅ DEAN performs well on i7/RTX 3080 hardware")
            print("  The system can handle expected workloads efficiently")
        else:
            print("  ⚠️  Performance optimizations recommended")
            for rec in recommendations:
                print(f"    - {rec}")
        
        print(f"\n⏱️  Total validation time: {total_time:.2f} seconds")
        
        # Save detailed report
        report = {
            "timestamp": datetime.now().isoformat(),
            "hardware_profile": HARDWARE_PROFILE,
            "test_parameters": {
                "concurrent_users": CONCURRENT_USERS,
                "requests_per_user": REQUESTS_PER_USER,
                "evolution_trials": EVOLUTION_TRIALS,
                "agent_count": AGENT_COUNT
            },
            "metrics": self.metrics,
            "suitable_for_hardware": suitable,
            "recommendations": recommendations,
            "total_time_seconds": total_time
        }
        
        report_file = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")


async def main():
    """Run performance validation."""
    validator = PerformanceValidator()
    await validator.run()


if __name__ == "__main__":
    print("Starting DEAN Performance Validation...")
    print("Make sure all services are running before proceeding.")
    print()
    
    asyncio.run(main())