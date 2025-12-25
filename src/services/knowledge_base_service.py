"""
Knowledge Base service for querying Bedrock Knowledge Base.

This service provides methods to query the Knowledge Base for:
- Service mapping rules
- AWS pricing information
- AWS service descriptions
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import boto3
from botocore.exceptions import ClientError

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class KnowledgeBaseResult:
    """Result from Knowledge Base query."""
    content: str
    score: float
    metadata: Dict[str, Any]
    source_location: Optional[str] = None


class KnowledgeBaseService:
    """Service for querying Bedrock Knowledge Base."""
    
    def __init__(self):
        """Initialize Bedrock Agent Runtime client."""
        self.client = boto3.client(
            'bedrock-agent-runtime',
            region_name=settings.aws_region
        )
        self.kb_id = settings.bedrock_knowledge_base_id
        
        if not self.kb_id:
            logger.warning("Knowledge Base ID not configured")
    
    def query(
        self,
        query_text: str,
        max_results: int = 5,
        min_score: float = 0.5
    ) -> List[KnowledgeBaseResult]:
        """
        Query the Knowledge Base.
        
        Args:
            query_text: The query text
            max_results: Maximum number of results to return
            min_score: Minimum relevance score (0.0 to 1.0)
            
        Returns:
            List of KnowledgeBaseResult objects
            
        Raises:
            ValueError: If Knowledge Base ID is not configured
            ClientError: If query fails
        """
        if not self.kb_id:
            raise ValueError("Knowledge Base ID not configured. Set BEDROCK_KNOWLEDGE_BASE_ID in .env")
        
        try:
            logger.info(f"Querying Knowledge Base: {query_text[:100]}...")
            
            response = self.client.retrieve(
                knowledgeBaseId=self.kb_id,
                retrievalQuery={
                    'text': query_text
                },
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': max_results
                    }
                }
            )
            
            results = []
            for item in response.get('retrievalResults', []):
                score = item.get('score', 0.0)
                
                # Filter by minimum score
                if score < min_score:
                    continue
                
                content = item.get('content', {}).get('text', '')
                metadata = item.get('metadata', {})
                location = item.get('location', {}).get('s3Location', {})
                source_location = location.get('uri') if location else None
                
                results.append(KnowledgeBaseResult(
                    content=content,
                    score=score,
                    metadata=metadata,
                    source_location=source_location
                ))
            
            logger.info(f"Found {len(results)} results")
            return results
            
        except ClientError as e:
            logger.error(f"Error querying Knowledge Base: {e}")
            raise
    
    def query_service_mapping(
        self,
        provider: str,
        service_name: str,
        specifications: Optional[Dict[str, Any]] = None
    ) -> List[KnowledgeBaseResult]:
        """
        Query for service mapping rules.
        
        Args:
            provider: Cloud provider (alibaba, huawei, tencent, gcp, azure)
            service_name: Name of the service to map
            specifications: Optional service specifications
            
        Returns:
            List of relevant mapping results
        """
        query = f"Find AWS service equivalent for {provider} {service_name}"
        
        if specifications:
            spec_str = ", ".join(f"{k}: {v}" for k, v in specifications.items())
            query += f" with specifications: {spec_str}"
        
        return self.query(query, max_results=5)
    
    def query_pricing_info(
        self,
        aws_service: str,
        service_type: Optional[str] = None,
        region: str = "us-east-1"
    ) -> List[KnowledgeBaseResult]:
        """
        Query for AWS pricing information.
        
        Args:
            aws_service: AWS service name (e.g., EC2, S3, RDS)
            service_type: Optional service type (e.g., t3.micro, Standard)
            region: AWS region
            
        Returns:
            List of relevant pricing results
        """
        query = f"AWS {aws_service} pricing in {region}"
        
        if service_type:
            query += f" for {service_type}"
        
        return self.query(query, max_results=3)
    
    def query_service_description(
        self,
        aws_service: str
    ) -> List[KnowledgeBaseResult]:
        """
        Query for AWS service description and features.
        
        Args:
            aws_service: AWS service name
            
        Returns:
            List of relevant service description results
        """
        query = f"AWS {aws_service} service description, features, and use cases"
        
        return self.query(query, max_results=3)
    
    def test_connection(self) -> bool:
        """
        Test connection to Knowledge Base.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            results = self.query("AWS EC2", max_results=1)
            logger.info("Knowledge Base connection test successful")
            return len(results) > 0
        except Exception as e:
            logger.error(f"Knowledge Base connection test failed: {e}")
            return False


# Global instance
knowledge_base_service = KnowledgeBaseService()
