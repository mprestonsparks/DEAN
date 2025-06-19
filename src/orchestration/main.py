#!/usr/bin/env python3
"""
DEAN Orchestrator - Main Application Entry Point
"""

import sys
import os

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the FastAPI app - try production version first
try:
    from unified_server_production import app
except ImportError:
    try:
        from unified_server import app
    except ImportError:
        try:
            from .unified_server import app
        except ImportError:
            # If unified_server doesn't exist, create a basic app
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware
            
            app = FastAPI(
                title="DEAN Orchestration Service",
                description="Distributed Evolutionary Agent Network Orchestrator",
                version="1.0.0"
            )
            
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            
            @app.get("/")
            async def root():
                return {"message": "DEAN Orchestrator API", "status": "operational"}
            
            @app.get("/health")
            async def health():
                return {
                    "status": "healthy",
                    "service": "orchestrator",
                    "version": "1.0.0"
                }

# For running directly with python main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8082,
        reload=False
    )