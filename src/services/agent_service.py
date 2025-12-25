"""
Agent Service for managing pricing agent instances and sessions.

Provides high-level interface for agent interactions with:
- Session management
- Progress tracking
- Error handling
- Quote modifications
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from ..agents.pricing_agent import PricingAgent
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AgentSession:
    """
    Represents an agent conversation session.
    
    Tracks conversation history, context, and state for a user's
    interaction with the pricing agent.
    """
    
    def __init__(self, session_id: str, user_id: str, language: str = "en"):
        """
        Initialize agent session.
        
        Args:
            session_id: Unique session identifier
            user_id: User ID for this session
            language: Preferred language ('en' or 'zh')
        """
        self.session_id = session_id
        self.user_id = user_id
        self.language = language
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.agent = PricingAgent(language=language)
        self.context = {}
        self.quotes = []
        
        logger.info(f"Created agent session {session_id} for user {user_id}")
    
    def process_message(self, message: str) -> Dict[str, Any]:
        """
        Process a user message through the agent.
        
        Args:
            message: User's message
        
        Returns:
            Agent response
        """
        self.last_activity = datetime.now()
        
        response = self.agent.process_request(
            user_message=message,
            user_id=self.user_id,
            session_id=self.session_id,
            language=self.language
        )
        
        # Track quotes
        if response.get("type") == "quote" and response.get("quote_id"):
            self.quotes.append({
                "quote_id": response["quote_id"],
                "created_at": datetime.now(),
                "total_monthly_cost": response.get("total_monthly_cost"),
                "total_annual_cost": response.get("total_annual_cost")
            })
        
        return response
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get conversation history."""
        return self.agent.get_conversation_history()
    
    def clear_history(self):
        """Clear conversation history."""
        self.agent.clear_conversation_history()
        logger.info(f"Cleared history for session {self.session_id}")
    
    def get_quotes(self) -> List[Dict[str, Any]]:
        """Get all quotes generated in this session."""
        return self.quotes


class AgentService:
    """
    Service for managing pricing agent instances and sessions.
    
    Provides:
    - Session creation and management
    - Multi-user support
    - Progress tracking
    - Error recovery
    """
    
    def __init__(self):
        """Initialize agent service."""
        self.sessions: Dict[str, AgentSession] = {}
        logger.info("AgentService initialized")
    
    def create_session(
        self,
        user_id: str,
        language: str = "en",
        session_id: Optional[str] = None
    ) -> str:
        """
        Create a new agent session.
        
        Args:
            user_id: User ID
            language: Preferred language ('en' or 'zh')
            session_id: Optional session ID (generated if not provided)
        
        Returns:
            Session ID
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        session = AgentSession(
            session_id=session_id,
            user_id=user_id,
            language=language
        )
        
        self.sessions[session_id] = session
        
        logger.info(f"Created session {session_id} for user {user_id}")
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[AgentSession]:
        """
        Get an existing session.
        
        Args:
            session_id: Session ID
        
        Returns:
            AgentSession or None if not found
        """
        return self.sessions.get(session_id)
    
    def process_message(
        self,
        session_id: str,
        message: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Process a message in a session.
        
        Args:
            session_id: Session ID
            message: User's message
            progress_callback: Optional callback for progress updates
        
        Returns:
            Agent response
        """
        session = self.get_session(session_id)
        
        if session is None:
            return {
                "success": False,
                "error": "Session not found",
                "message": "Session not found. Please create a new session."
            }
        
        try:
            # Send progress update if callback provided
            if progress_callback:
                progress_callback({
                    "status": "processing",
                    "message": "Processing your request..."
                })
            
            response = session.process_message(message)
            
            # Send completion update
            if progress_callback:
                if response.get("success"):
                    progress_callback({
                        "status": "completed",
                        "message": "Request completed successfully"
                    })
                else:
                    progress_callback({
                        "status": "error",
                        "message": response.get("message", "An error occurred")
                    })
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message in session {session_id}: {e}")
            
            if progress_callback:
                progress_callback({
                    "status": "error",
                    "message": f"Error: {str(e)}"
                })
            
            return {
                "success": False,
                "error": str(e),
                "message": f"An error occurred: {str(e)}"
            }
    
    def modify_quote(
        self,
        session_id: str,
        quote_id: str,
        modifications: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Modify an existing quote.
        
        Args:
            session_id: Session ID
            quote_id: Quote ID to modify
            modifications: Modifications to apply (region, pricing_model, etc.)
        
        Returns:
            Modified quote result
        """
        session = self.get_session(session_id)
        
        if session is None:
            return {
                "success": False,
                "error": "Session not found",
                "message": "Session not found"
            }
        
        # Find the quote in session
        quote_info = next(
            (q for q in session.quotes if q["quote_id"] == quote_id),
            None
        )
        
        if quote_info is None:
            return {
                "success": False,
                "error": "Quote not found",
                "message": f"Quote {quote_id} not found in this session"
            }
        
        # Create a modification request message
        mod_message = f"Modify quote {quote_id} with: {modifications}"
        
        return session.process_message(mod_message)
    
    def get_session_quotes(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all quotes for a session.
        
        Args:
            session_id: Session ID
        
        Returns:
            List of quotes
        """
        session = self.get_session(session_id)
        
        if session is None:
            return []
        
        return session.get_quotes()
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session ID
        
        Returns:
            True if deleted, False if not found
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session {session_id}")
            return True
        
        return False
    
    def cleanup_inactive_sessions(self, max_age_hours: int = 24):
        """
        Clean up inactive sessions.
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        now = datetime.now()
        to_delete = []
        
        for session_id, session in self.sessions.items():
            age = (now - session.last_activity).total_seconds() / 3600
            if age > max_age_hours:
                to_delete.append(session_id)
        
        for session_id in to_delete:
            self.delete_session(session_id)
        
        if to_delete:
            logger.info(f"Cleaned up {len(to_delete)} inactive sessions")
    
    def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        return len(self.sessions)
    
    def get_user_sessions(self, user_id: str) -> List[str]:
        """
        Get all session IDs for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            List of session IDs
        """
        return [
            session_id
            for session_id, session in self.sessions.items()
            if session.user_id == user_id
        ]
