"""User and Session data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from decimal import Decimal
import uuid


@dataclass
class User:
    """User account model."""
    
    user_id: str
    username: str
    email: str
    password_hash: str
    role: str  # 'admin' or 'sales'
    full_name: str
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    
    @staticmethod
    def generate_id() -> str:
        """Generate a new user ID."""
        return str(uuid.uuid4())
    
    def to_dynamodb_item(self) -> dict:
        """Convert to DynamoDB item format."""
        item = {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'role': self.role,
            'full_name': self.full_name,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active
        }
        if self.last_login:
            item['last_login'] = self.last_login.isoformat()
        return item
    
    @classmethod
    def from_dynamodb_item(cls, item: dict) -> 'User':
        """Create User from DynamoDB item."""
        return cls(
            user_id=item['user_id'],
            username=item['username'],
            email=item['email'],
            password_hash=item['password_hash'],
            role=item['role'],
            full_name=item['full_name'],
            created_at=datetime.fromisoformat(item['created_at']),
            last_login=datetime.fromisoformat(item['last_login']) if 'last_login' in item else None,
            is_active=item.get('is_active', True)
        )


@dataclass
class Session:
    """User session model."""
    
    session_id: str
    user_id: str
    token: str
    created_at: datetime
    expires_at: datetime
    ip_address: str
    user_agent: str
    
    @staticmethod
    def generate_id() -> str:
        """Generate a new session ID."""
        return str(uuid.uuid4())
    
    def to_dynamodb_item(self) -> dict:
        """Convert to DynamoDB item format."""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'token': self.token,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }
    
    @classmethod
    def from_dynamodb_item(cls, item: dict) -> 'Session':
        """Create Session from DynamoDB item."""
        return cls(
            session_id=item['session_id'],
            user_id=item['user_id'],
            token=item['token'],
            created_at=datetime.fromisoformat(item['created_at']),
            expires_at=datetime.fromisoformat(item['expires_at']),
            ip_address=item['ip_address'],
            user_agent=item['user_agent']
        )
    
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at
