"""WebSocket endpoints for real-time updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Set
import json
import asyncio

from src.services.auth_service import AuthenticationService
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/ws", tags=["websocket"])

# Initialize services
auth_service = AuthenticationService()


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.
    
    Maintains active connections per user and provides methods to send updates.
    """
    
    def __init__(self):
        # Map of user_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Map of WebSocket -> user_id for cleanup
        self.connection_users: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.connection_users[websocket] = user_id
        
        logger.info(f"WebSocket connected for user {user_id}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.connection_users:
            user_id = self.connection_users[websocket]
            
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                
                # Clean up empty sets
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            del self.connection_users[websocket]
            logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send a message to all connections of a specific user."""
        if user_id in self.active_connections:
            disconnected = set()
            
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {str(e)}")
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for connection in disconnected:
                self.disconnect(connection)
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)
    
    def get_user_connection_count(self, user_id: str) -> int:
        """Get the number of active connections for a user."""
        return len(self.active_connections.get(user_id, set()))
    
    def get_total_connections(self) -> int:
        """Get the total number of active connections."""
        return sum(len(connections) for connections in self.active_connections.values())


# Global connection manager
manager = ConnectionManager()


@router.websocket("/quote-status")
async def websocket_quote_status(
    websocket: WebSocket,
    session_id: str = Query(...),
    token: str = Query(...)
):
    """
    WebSocket endpoint for real-time quote generation updates.
    
    Clients connect with session_id and token for authentication.
    Receives progress updates during quote generation process.
    
    Message format:
    {
        "type": "progress" | "complete" | "error",
        "quote_id": "...",
        "message": "...",
        "progress": 0-100,
        "data": {...}
    }
    """
    
    # Authenticate the WebSocket connection
    try:
        user = auth_service.validate_session(session_id, token)
        
        if not user:
            await websocket.close(code=1008, reason="Invalid authentication")
            return
        
        if not user.is_active:
            await websocket.close(code=1008, reason="User account is deactivated")
            return
        
        user_id = user.user_id
        
    except Exception as e:
        logger.error(f"WebSocket authentication error: {str(e)}")
        await websocket.close(code=1011, reason="Authentication error")
        return
    
    # Connect the WebSocket
    await manager.connect(websocket, user_id)
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connected successfully",
            "user_id": user_id
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive messages from client (e.g., ping/pong for keepalive)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle ping messages
                if message.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": message.get("timestamp")
                    })
                
                # Handle other message types as needed
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for user {user_id}")
                break
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from user {user_id}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid message format"
                })
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {str(e)}")
                break
    
    finally:
        manager.disconnect(websocket)


# Helper functions for sending updates (to be used by other services)

async def send_quote_progress(user_id: str, quote_id: str, message: str, progress: int, data: dict = None):
    """
    Send a progress update for quote generation.
    
    Args:
        user_id: User ID to send update to
        quote_id: Quote ID being processed
        message: Progress message
        progress: Progress percentage (0-100)
        data: Optional additional data
    """
    await manager.send_personal_message({
        "type": "progress",
        "quote_id": quote_id,
        "message": message,
        "progress": progress,
        "data": data or {}
    }, user_id)


async def send_quote_complete(user_id: str, quote_id: str, quote_data: dict):
    """
    Send a completion notification for quote generation.
    
    Args:
        user_id: User ID to send update to
        quote_id: Quote ID that was completed
        quote_data: Complete quote data
    """
    await manager.send_personal_message({
        "type": "complete",
        "quote_id": quote_id,
        "message": "Quote generation completed successfully",
        "data": quote_data
    }, user_id)


async def send_quote_error(user_id: str, quote_id: str, error_message: str):
    """
    Send an error notification for quote generation.
    
    Args:
        user_id: User ID to send update to
        quote_id: Quote ID that failed
        error_message: Error description
    """
    await manager.send_personal_message({
        "type": "error",
        "quote_id": quote_id,
        "message": error_message
    }, user_id)


# Export manager and helper functions
__all__ = [
    'router',
    'manager',
    'send_quote_progress',
    'send_quote_complete',
    'send_quote_error'
]
