"""
WebSocket handler for real-time communication.
"""

import json
from typing import Set, Any, Dict
import structlog
from fastapi import WebSocket

# Configure logging
logger = structlog.get_logger()


class WebSocketManager:
    """Manages WebSocket connections for broadcasting updates."""
    
    def __init__(self):
        """Initialize WebSocket manager."""
        self.active_connections: Set[WebSocket] = set()
        logger.info("WebSocket manager initialized")
    
    async def connect(self, websocket: WebSocket):
        """Accept and track a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("WebSocket connected", total_connections=len(self.active_connections))
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        logger.info("WebSocket disconnected", total_connections=len(self.active_connections))
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error("Failed to send personal message", error=str(e))
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
            
        message_str = json.dumps(message)
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error("Failed to send broadcast message", error=str(e))
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
        
        if disconnected:
            logger.info("Cleaned up disconnected clients", count=len(disconnected))
    
    async def broadcast_json(self, data: Dict[str, Any]):
        """Broadcast JSON data to all connected clients."""
        await self.broadcast(data)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)