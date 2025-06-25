"""Web Dashboard Server for DEAN Evolution System.

This module runs a separate FastAPI server on port 8083 specifically
for serving the web dashboard interface.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app for web dashboard
app = FastAPI(
    title="DEAN Web Dashboard",
    description="Web interface for DEAN Evolution Trial monitoring",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get web directory path
web_path = Path(__file__).parent.parent.parent / "web"

# Mount static files
if web_path.exists():
    # CSS files
    css_path = web_path / "css"
    if css_path.exists():
        app.mount("/css", StaticFiles(directory=str(css_path)), name="css")
    
    # JavaScript files
    js_path = web_path / "js"
    if js_path.exists():
        app.mount("/js", StaticFiles(directory=str(js_path)), name="js")
else:
    logger.warning(f"Web directory not found at {web_path}")


@app.get("/")
async def root():
    """Serve the main dashboard page."""
    index_file = web_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    else:
        return {"error": "Dashboard not found", "path": str(index_file)}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "DEAN Web Dashboard",
        "port": 8083
    }


def start_web_server(host: str = "0.0.0.0", port: int = 8083):
    """Start the web dashboard server."""
    logger.info(f"Starting DEAN Web Dashboard on {host}:{port}")
    logger.info(f"Web files served from: {web_path}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    start_web_server()