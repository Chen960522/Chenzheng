"""User and Session database operations."""

from datetime import datetime
from typing import Optional, List
from boto3.dynamodb.conditions import Key
import boto3

from src.models.user import User, Session
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class UserService:
    """Service for user database operations."""
    
    def __init__(self, dynamodb_client=None):
        """Initialize UserService with DynamoDB client."""
        if dynamodb_client is None:
            dynamodb_client = boto3.resource('dynamodb', region_name=settings.aws_region)
        self.dynamodb = dynamodb_client
        self.users_table = self.dynamodb.Table(settings.dynamodb_users_table)
        self.sessions_table = self.dynamodb.Table(settings.dynamodb_sessions_table)
    
    # User CRUD operations
    
    def create_user(self, user: User) -> User:
        """Create a new user in DynamoDB."""
        try:
            self.users_table.put_item(Item=user.to_dynamodb_item())
            logger.info(f"Created user: {user.username}")
            return user
        except Exception as e:
            logger.error(f"Failed to create user {user.username}: {e}")
            raise
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by user_id."""
        try:
            response = self.users_table.get_item(Key={'user_id': user_id})
            if 'Item' in response:
                return User.from_dynamodb_item(response['Item'])
            return None
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            raise
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username using GSI."""
        try:
            response = self.users_table.query(
                IndexName='username-index',
                KeyConditionExpression=Key('username').eq(username)
            )
            if response['Items']:
                return User.from_dynamodb_item(response['Items'][0])
            return None
        except Exception as e:
            logger.error(f"Failed to get user by username {username}: {e}")
            raise
    
    def list_users(self) -> List[User]:
        """List all users."""
        try:
            response = self.users_table.scan()
            users = [User.from_dynamodb_item(item) for item in response['Items']]
            
            # Handle pagination if needed
            while 'LastEvaluatedKey' in response:
                response = self.users_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                users.extend([User.from_dynamodb_item(item) for item in response['Items']])
            
            return users
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            raise
    
    def update_user(self, user: User) -> User:
        """Update an existing user."""
        try:
            self.users_table.put_item(Item=user.to_dynamodb_item())
            logger.info(f"Updated user: {user.username}")
            return user
        except Exception as e:
            logger.error(f"Failed to update user {user.username}: {e}")
            raise
    
    def delete_user(self, user_id: str) -> None:
        """Delete a user."""
        try:
            self.users_table.delete_item(Key={'user_id': user_id})
            logger.info(f"Deleted user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            raise
    
    def deactivate_user(self, user_id: str) -> Optional[User]:
        """Deactivate a user (soft delete)."""
        user = self.get_user_by_id(user_id)
        if user:
            user.is_active = False
            return self.update_user(user)
        return None
    
    def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp."""
        try:
            self.users_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression='SET last_login = :timestamp',
                ExpressionAttributeValues={':timestamp': datetime.utcnow().isoformat()}
            )
        except Exception as e:
            logger.error(f"Failed to update last login for user {user_id}: {e}")
            raise
    
    # Session CRUD operations
    
    def create_session(self, session: Session) -> Session:
        """Create a new session in DynamoDB."""
        try:
            self.sessions_table.put_item(Item=session.to_dynamodb_item())
            logger.info(f"Created session for user: {session.user_id}")
            return session
        except Exception as e:
            logger.error(f"Failed to create session for user {session.user_id}: {e}")
            raise
    
    def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """Get session by session_id."""
        try:
            response = self.sessions_table.get_item(Key={'session_id': session_id})
            if 'Item' in response:
                return Session.from_dynamodb_item(response['Item'])
            return None
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            raise
    
    def get_user_sessions(self, user_id: str) -> List[Session]:
        """Get all sessions for a user using GSI."""
        try:
            response = self.sessions_table.query(
                IndexName='user-sessions-index',
                KeyConditionExpression=Key('user_id').eq(user_id)
            )
            return [Session.from_dynamodb_item(item) for item in response['Items']]
        except Exception as e:
            logger.error(f"Failed to get sessions for user {user_id}: {e}")
            raise
    
    def delete_session(self, session_id: str) -> None:
        """Delete a session (logout)."""
        try:
            self.sessions_table.delete_item(Key={'session_id': session_id})
            logger.info(f"Deleted session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            raise
    
    def delete_user_sessions(self, user_id: str) -> None:
        """Delete all sessions for a user."""
        try:
            sessions = self.get_user_sessions(user_id)
            for session in sessions:
                self.delete_session(session.session_id)
            logger.info(f"Deleted all sessions for user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to delete sessions for user {user_id}: {e}")
            raise
