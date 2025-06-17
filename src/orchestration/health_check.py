#!/usr/bin/env python3
"""Simple health check for the orchestrator service"""

import sys
import httpx

try:
    response = httpx.get("http://localhost:8082/health", timeout=5.0)
    if response.status_code == 200:
        sys.exit(0)  # Healthy
    else:
        sys.exit(1)  # Unhealthy
except Exception:
    sys.exit(1)  # Unhealthy