"""Quote service for DynamoDB operations."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError

from ..models.quote import Quote
from ..utils.logger import get_logger

logger = get_logger(__name__)


class QuoteService:
    """Service for managing quotes in DynamoDB."""
    
    def __init__(self, dynamodb_client=None, table_name: str = 'quotes'):
        """
        Initialize the quote service.
        
        Args:
            dynamodb_client: Boto3 DynamoDB client (optional, will create if not provided)
            table_name: Name of the DynamoDB table
        """
        self.dynamodb = dynamodb_client or boto3.resource('dynamodb')
        self.table_name = table_name
        self.table = self.dynamodb.Table(table_name)
        logger.info(f"QuoteService initialized with table: {table_name}")
    
    def create_quote(self, quote: Quote) -> Quote:
        """
        Create a new quote in DynamoDB.
        
        Args:
            quote: Quote object to create
        
        Returns:
            Created Quote object
        
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            item = quote.to_dict()
            self.table.put_item(Item=item)
            logger.info(f"Created quote: {quote.quote_id}")
            return quote
        except ClientError as e:
            logger.error(f"Failed to create quote: {e}")
            raise
    
    def get_quote(self, quote_id: str) -> Optional[Quote]:
        """
        Get a quote by ID.
        
        Args:
            quote_id: Quote ID
        
        Returns:
            Quote object if found, None otherwise
        
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            response = self.table.get_item(Key={'quote_id': quote_id})
            
            if 'Item' not in response:
                logger.warning(f"Quote not found: {quote_id}")
                return None
            
            quote = Quote.from_dict(response['Item'])
            logger.info(f"Retrieved quote: {quote_id}")
            return quote
        except ClientError as e:
            logger.error(f"Failed to get quote {quote_id}: {e}")
            raise
    
    def update_quote(self, quote: Quote) -> Quote:
        """
        Update an existing quote.
        
        Args:
            quote: Quote object with updated data
        
        Returns:
            Updated Quote object
        
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # Update the updated_at timestamp
            quote.updated_at = datetime.now()
            
            item = quote.to_dict()
            self.table.put_item(Item=item)
            logger.info(f"Updated quote: {quote.quote_id}")
            return quote
        except ClientError as e:
            logger.error(f"Failed to update quote {quote.quote_id}: {e}")
            raise
    
    def delete_quote(self, quote_id: str) -> bool:
        """
        Delete a quote by ID.
        
        Args:
            quote_id: Quote ID
        
        Returns:
            True if deleted, False if not found
        
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            response = self.table.delete_item(
                Key={'quote_id': quote_id},
                ReturnValues='ALL_OLD'
            )
            
            if 'Attributes' in response:
                logger.info(f"Deleted quote: {quote_id}")
                return True
            else:
                logger.warning(f"Quote not found for deletion: {quote_id}")
                return False
        except ClientError as e:
            logger.error(f"Failed to delete quote {quote_id}: {e}")
            raise
    
    def list_quotes_by_user(
        self,
        user_id: str,
        limit: int = 50,
        start_key: Optional[Dict[str, Any]] = None
    ) -> tuple[List[Quote], Optional[Dict[str, Any]]]:
        """
        List all quotes for a specific user.
        
        Args:
            user_id: User ID
            limit: Maximum number of quotes to return
            start_key: Pagination key from previous request
        
        Returns:
            Tuple of (list of Quote objects, next pagination key)
        
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            query_params = {
                'IndexName': 'user-quotes-index',
                'KeyConditionExpression': 'user_id = :user_id',
                'ExpressionAttributeValues': {':user_id': user_id},
                'Limit': limit,
                'ScanIndexForward': False  # Sort by created_at descending
            }
            
            if start_key:
                query_params['ExclusiveStartKey'] = start_key
            
            response = self.table.query(**query_params)
            
            quotes = [Quote.from_dict(item) for item in response.get('Items', [])]
            next_key = response.get('LastEvaluatedKey')
            
            logger.info(f"Retrieved {len(quotes)} quotes for user: {user_id}")
            return quotes, next_key
        except ClientError as e:
            logger.error(f"Failed to list quotes for user {user_id}: {e}")
            raise
    
    def list_all_quotes(
        self,
        limit: int = 50,
        start_key: Optional[Dict[str, Any]] = None
    ) -> tuple[List[Quote], Optional[Dict[str, Any]]]:
        """
        List all quotes (admin function).
        
        Args:
            limit: Maximum number of quotes to return
            start_key: Pagination key from previous request
        
        Returns:
            Tuple of (list of Quote objects, next pagination key)
        
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            scan_params = {
                'Limit': limit
            }
            
            if start_key:
                scan_params['ExclusiveStartKey'] = start_key
            
            response = self.table.scan(**scan_params)
            
            quotes = [Quote.from_dict(item) for item in response.get('Items', [])]
            next_key = response.get('LastEvaluatedKey')
            
            logger.info(f"Retrieved {len(quotes)} quotes (all users)")
            return quotes, next_key
        except ClientError as e:
            logger.error(f"Failed to list all quotes: {e}")
            raise
    
    def update_quote_status(self, quote_id: str, new_status: str) -> Optional[Quote]:
        """
        Update the status of a quote.
        
        Args:
            quote_id: Quote ID
            new_status: New status ('draft', 'finalized', 'sent')
        
        Returns:
            Updated Quote object if found, None otherwise
        
        Raises:
            ClientError: If DynamoDB operation fails
            ValueError: If status is invalid
        """
        if new_status not in Quote.SUPPORTED_STATUSES:
            raise ValueError(
                f"Invalid status: {new_status}. "
                f"Supported statuses: {', '.join(Quote.SUPPORTED_STATUSES)}"
            )
        
        quote = self.get_quote(quote_id)
        if quote is None:
            return None
        
        quote.update_status(new_status)
        return self.update_quote(quote)
    
    def add_export_url(
        self,
        quote_id: str,
        format_type: str,
        url: str
    ) -> Optional[Quote]:
        """
        Add an export URL to a quote.
        
        Args:
            quote_id: Quote ID
            format_type: Export format ('pdf', 'excel', 'json')
            url: S3 URL for the exported file
        
        Returns:
            Updated Quote object if found, None otherwise
        
        Raises:
            ClientError: If DynamoDB operation fails
            ValueError: If format is invalid
        """
        if format_type not in Quote.SUPPORTED_FORMATS:
            raise ValueError(
                f"Invalid format: {format_type}. "
                f"Supported formats: {', '.join(Quote.SUPPORTED_FORMATS)}"
            )
        
        quote = self.get_quote(quote_id)
        if quote is None:
            return None
        
        quote.add_export_url(format_type, url)
        return self.update_quote(quote)
    
    def get_quote_count_by_user(self, user_id: str) -> int:
        """
        Get the total number of quotes for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Number of quotes
        
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            response = self.table.query(
                IndexName='user-quotes-index',
                KeyConditionExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': user_id},
                Select='COUNT'
            )
            
            count = response.get('Count', 0)
            logger.info(f"User {user_id} has {count} quotes")
            return count
        except ClientError as e:
            logger.error(f"Failed to count quotes for user {user_id}: {e}")
            raise
    
    def get_quotes_by_status(
        self,
        user_id: str,
        status: str,
        limit: int = 50
    ) -> List[Quote]:
        """
        Get quotes by user and status.
        
        Args:
            user_id: User ID
            status: Quote status
            limit: Maximum number of quotes to return
        
        Returns:
            List of Quote objects
        
        Raises:
            ClientError: If DynamoDB operation fails
            ValueError: If status is invalid
        """
        if status not in Quote.SUPPORTED_STATUSES:
            raise ValueError(
                f"Invalid status: {status}. "
                f"Supported statuses: {', '.join(Quote.SUPPORTED_STATUSES)}"
            )
        
        try:
            response = self.table.query(
                IndexName='user-quotes-index',
                KeyConditionExpression='user_id = :user_id',
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':user_id': user_id,
                    ':status': status
                },
                Limit=limit,
                ScanIndexForward=False
            )
            
            quotes = [Quote.from_dict(item) for item in response.get('Items', [])]
            logger.info(f"Retrieved {len(quotes)} {status} quotes for user: {user_id}")
            return quotes
        except ClientError as e:
            logger.error(f"Failed to get quotes by status for user {user_id}: {e}")
            raise
