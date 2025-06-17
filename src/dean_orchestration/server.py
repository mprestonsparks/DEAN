"""Main entry point for the DEAN server command.

This module serves as the primary entry point for the `dean-server` command
as specified in pyproject.toml. It starts the unified orchestration server.
"""

import sys
import os
from typing import Optional
import uvicorn
from structlog import get_logger

# Import server application
from ..orchestration.unified_server import app

logger = get_logger(__name__)


def main(args: Optional[list[str]] = None) -> int:
    """Main entry point for the dean-server command.
    
    Starts the DEAN orchestration server with configurable host and port.
    
    Args:
        args: Command line arguments (not used, configuration via environment)
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Get configuration from environment
    host = os.getenv("DEAN_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("DEAN_SERVER_PORT", "8082"))
    reload = os.getenv("DEAN_SERVER_RELOAD", "false").lower() == "true"
    log_level = os.getenv("DEAN_LOG_LEVEL", "info").lower()
    
    try:
        logger.info(
            "Starting DEAN orchestration server",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level
        )
        
        # Run the server
        uvicorn.run(
            "dean_orchestration.orchestration.unified_server:app",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
            access_log=True,
            use_colors=True
        )
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logger.error("Failed to start server", error=str(e), exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())