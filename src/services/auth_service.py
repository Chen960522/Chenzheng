"""Authentication service for user login, logout, and token management."""

from datetime import datetime, timedelta
from typing import Optional, Dict
from passlib.context import CryptContext
from jose import jwt, JWTError

from src.models.user import User, Session
from src.services.user_service import UserService
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AuthenticationService:
    """Service for authentication and session management."""
    
    def __init__(self, user_service: Optional[UserService] = None):
        """Initialize AuthenticationService."""
        self.user_service = user_service or UserService()
        self.pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.jwt_access_token_expire_minutes
    
    def hash_password(self, password: str) -> str:
        """Hash a password using Argon2id."""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user with username and password.
        
        Returns:
            User object if authentication successful, None otherwise
        """
        try:
            user = self.user_service.get_user_by_username(username)
            
            if not user:
                logger.warning(f"Authentication failed: user not found - {username}")
                return None
            
            if not user.is_active:
                logger.warning(f"Authentication failed: user deactivated - {username}")
                return None
            
            if not self.verify_password(password, user.password_hash):
                logger.warning(f"Authentication failed: invalid password - {username}")
                return None
            
            logger.info(f"User authenticated successfully: {username}")
            return user
            
        except Exception as e:
            logger.error(f"Authentication error for user {username}: {e}")
            return None
    
    def create_access_token(self, user: User) -> str:
        """
        Create a JWT access token for a user.
        
        Args:
            user: User object
            
        Returns:
            JWT token string
        """
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        payload = {
            "sub": user.user_id,
            "username": user.username,
            "role": user.role,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.info(f"Created access token for user: {user.username}")
        return token
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload dict if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token is expired
            exp = payload.get("exp")
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                logger.warning("Token verification failed: token expired")
                return None
            
            return payload
            
        except JWTError as e:
            logger.warning(f"Token verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    def login(
        self,
        username: str,
        password: str,
        ip_address: str,
        user_agent: str
    ) -> Optional[Dict]:
        """
        Login a user and create a session.
        
        Args:
            username: Username
            password: Plain text password
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Dict with user info and token if successful, None otherwise
        """
        # Authenticate user
        user = self.authenticate_user(username, password)
        if not user:
            return None
        
        # Create access token
        token = self.create_access_token(user)
        
        # Create session
        session = Session(
            session_id=Session.generate_id(),
            user_id=user.user_id,
            token=token,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes),
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        try:
            self.user_service.create_session(session)
            self.user_service.update_last_login(user.user_id)
            
            logger.info(f"User logged in: {username}")
            
            return {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "full_name": user.full_name,
                "token": token,
                "session_id": session.session_id,
                "expires_at": session.expires_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create session for user {username}: {e}")
            return None
    
    def logout(self, session_id: str) -> bool:
        """
        Logout a user by deleting their session.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.user_service.delete_session(session_id)
            logger.info(f"User logged out: session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to logout session {session_id}: {e}")
            return False
    
    def logout_all_sessions(self, user_id: str) -> bool:
        """
        Logout all sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.user_service.delete_user_sessions(user_id)
            logger.info(f"All sessions logged out for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to logout all sessions for user {user_id}: {e}")
            return False
    
    def validate_session(self, session_id: str, token: str) -> Optional[User]:
        """
        Validate a session and token.
        
        Args:
            session_id: Session ID
            token: JWT token
            
        Returns:
            User object if valid, None otherwise
        """
        try:
            # Get session from database
            session = self.user_service.get_session_by_id(session_id)
            if not session:
                logger.warning(f"Session validation failed: session not found - {session_id}")
                return None
            
            # Check if session is expired
            if session.is_expired():
                logger.warning(f"Session validation failed: session expired - {session_id}")
                self.user_service.delete_session(session_id)
                return None
            
            # Verify token matches session
            if session.token != token:
                logger.warning(f"Session validation failed: token mismatch - {session_id}")
                return None
            
            # Verify token is valid
            payload = self.verify_token(token)
            if not payload:
                logger.warning(f"Session validation failed: invalid token - {session_id}")
                return None
            
            # Get user
            user = self.user_service.get_user_by_id(session.user_id)
            if not user:
                logger.warning(f"Session validation failed: user not found - {session.user_id}")
                return None
            
            # Check if user is active
            if not user.is_active:
                logger.warning(f"Session validation failed: user deactivated - {user.username}")
                return None
            
            return user
            
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return None
    
    def refresh_token(self, old_token: str) -> Optional[str]:
        """
        Refresh an access token.
        
        Args:
            old_token: Current JWT token
            
        Returns:
            New JWT token if successful, None otherwise
        """
        try:
            # Verify old token
            payload = self.verify_token(old_token)
            if not payload:
                return None
            
            # Get user
            user_id = payload.get("sub")
            user = self.user_service.get_user_by_id(user_id)
            if not user or not user.is_active:
                return None
            
            # Create new token
            new_token = self.create_access_token(user)
            logger.info(f"Token refreshed for user: {user.username}")
            return new_token
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None
