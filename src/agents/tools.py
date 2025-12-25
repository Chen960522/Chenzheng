"""
Agent tools for AWS Pricing Assistant.

These tools are used by the Strands Agent to orchestrate the pricing workflow:
1. parse_configuration_tool - Parse cloud service configurations
2. map_services_tool - Map cloud services to AWS equivalents
3. calculate_pricing_tool - Calculate AWS service pricing
4. generate_quote_tool - Generate pricing quote documents
5. query_knowledge_base_tool - Query Bedrock Knowledge Base
"""

from typing import Dict, Any, List, Optional
import json

from ..services.configuration_parser import ConfigurationParser
from ..services.service_mapper import ServiceMapper
from ..services.price_calculator import PriceCalculator
from ..services.quote_generator import QuoteGenerator
from ..services.knowledge_base_service import KnowledgeBaseService
from ..models.service_config import ServiceConfig
from ..models.cloud_service import AWSServiceMapping
from ..models.pricing_result import PricingResult
from ..utils.logger import get_logger

logger = get_logger(__name__)


# Tool definitions for Strands Agent
TOOL_DEFINITIONS = [
    {
        "name": "parse_configuration",
        "description": "Parse cloud service configuration from various formats (JSON, YAML, CSV, or plain text). Extracts service types, specifications, and provider information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "configuration_text": {
                    "type": "string",
                    "description": "The configuration text to parse. Can be in JSON, YAML, CSV, or plain text format."
                },
                "format_hint": {
                    "type": "string",
                    "enum": ["json", "yaml", "csv", "text"],
                    "description": "Optional hint about the format of the configuration. If not provided, the parser will attempt to detect the format automatically."
                }
            },
            "required": ["configuration_text"]
        }
    },
    {
        "name": "map_services",
        "description": "Map cloud provider services (Alibaba Cloud, Huawei Cloud, Tencent Cloud, GCP, Azure) to equivalent AWS services. Returns AWS service recommendations with confidence scores and explanations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "services": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "provider": {
                                "type": "string",
                                "enum": ["alibaba", "huawei", "tencent", "gcp", "azure"],
                                "description": "Cloud provider name"
                            },
                            "service_type": {
                                "type": "string",
                                "description": "Service category (compute, storage, database, network, etc.)"
                            },
                            "service_name": {
                                "type": "string",
                                "description": "Original service name from the cloud provider"
                            },
                            "specifications": {
                                "type": "object",
                                "description": "Service specifications (CPU, memory, storage, etc.)"
                            }
                        },
                        "required": ["provider", "service_type", "service_name"]
                    },
                    "description": "List of cloud services to map to AWS equivalents"
                }
            },
            "required": ["services"]
        }
    },
    {
        "name": "calculate_pricing",
        "description": "Calculate AWS service pricing for mapped services. Supports multiple regions and pricing models (On-Demand, Reserved, Savings Plans).",
        "input_schema": {
            "type": "object",
            "properties": {
                "aws_services": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "aws_service": {
                                "type": "string",
                                "description": "AWS service name (EC2, S3, RDS, etc.)"
                            },
                            "aws_service_type": {
                                "type": "string",
                                "description": "Specific service type (instance type, storage class, etc.)"
                            },
                            "specifications": {
                                "type": "object",
                                "description": "Service specifications"
                            }
                        },
                        "required": ["aws_service", "aws_service_type"]
                    },
                    "description": "List of AWS services to calculate pricing for"
                },
                "region": {
                    "type": "string",
                    "description": "AWS region for pricing (default: us-east-1)",
                    "default": "us-east-1"
                },
                "pricing_model": {
                    "type": "string",
                    "enum": ["on-demand", "reserved", "savings-plan"],
                    "description": "Pricing model to use (default: on-demand)",
                    "default": "on-demand"
                }
            },
            "required": ["aws_services"]
        }
    },
    {
        "name": "generate_quote",
        "description": "Generate a comprehensive pricing quote document with all service details, pricing breakdown, and recommendations. Supports Chinese and English output.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "User ID requesting the quote"
                },
                "original_input": {
                    "type": "string",
                    "description": "Original configuration input text"
                },
                "parsed_services": {
                    "type": "array",
                    "description": "List of parsed service configurations"
                },
                "aws_mappings": {
                    "type": "array",
                    "description": "List of AWS service mappings"
                },
                "pricing_results": {
                    "type": "array",
                    "description": "List of pricing calculation results"
                },
                "region": {
                    "type": "string",
                    "description": "Primary AWS region (default: us-east-1)",
                    "default": "us-east-1"
                },
                "language": {
                    "type": "string",
                    "enum": ["en", "zh"],
                    "description": "Output language (default: en)",
                    "default": "en"
                },
                "notes": {
                    "type": "string",
                    "description": "Optional notes to include in the quote"
                }
            },
            "required": ["user_id", "original_input", "parsed_services", "aws_mappings", "pricing_results"]
        }
    },
    {
        "name": "query_knowledge_base",
        "description": "Query the Bedrock Knowledge Base for service mapping rules, pricing information, or AWS service descriptions. Useful for getting additional context or handling edge cases.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The query to search for in the Knowledge Base"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
]


class AgentTools:
    """
    Agent tools implementation for AWS Pricing Assistant.
    
    Provides tool functions that can be called by the Strands Agent
    to orchestrate the pricing workflow.
    """
    
    def __init__(self):
        """Initialize agent tools with service instances."""
        self.parser = ConfigurationParser()
        self.mapper = ServiceMapper()
        self.calculator = PriceCalculator()
        self.generator = QuoteGenerator()
        self.kb_service = KnowledgeBaseService()
        logger.info("AgentTools initialized")
    
    def parse_configuration(
        self,
        configuration_text: str,
        format_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse cloud service configuration.
        
        Args:
            configuration_text: Configuration text to parse
            format_hint: Optional format hint (json, yaml, csv, text)
        
        Returns:
            Dictionary with parsed services and status
        """
        try:
            logger.info(f"Parsing configuration (format_hint: {format_hint})")
            
            services = self.parser.parse(configuration_text, format_hint)
            
            # Convert ServiceConfig objects to dictionaries
            services_dict = [
                {
                    "provider": s.provider,
                    "service_type": s.service_type,
                    "service_name": s.service_name,
                    "specifications": s.specifications,
                    "region": s.region,
                    "quantity": s.quantity
                }
                for s in services
            ]
            
            logger.info(f"Successfully parsed {len(services)} services")
            
            return {
                "success": True,
                "services": services_dict,
                "count": len(services),
                "message": f"Successfully parsed {len(services)} service(s)"
            }
            
        except Exception as e:
            logger.error(f"Error parsing configuration: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to parse configuration: {str(e)}"
            }
    
    def map_services(self, services: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Map cloud services to AWS equivalents.
        
        Args:
            services: List of service dictionaries to map
        
        Returns:
            Dictionary with AWS service mappings and status
        """
        try:
            logger.info(f"Mapping {len(services)} services to AWS")
            
            mappings = []
            for service_dict in services:
                # Convert dict to ServiceConfig
                service = ServiceConfig(
                    provider=service_dict["provider"],
                    service_type=service_dict["service_type"],
                    service_name=service_dict["service_name"],
                    specifications=service_dict.get("specifications", {}),
                    region=service_dict.get("region"),
                    quantity=service_dict.get("quantity", 1)
                )
                
                # Map service
                aws_mappings = self.mapper.map_service(service)
                
                if aws_mappings:
                    # Take the best mapping (first one, already ranked)
                    best_mapping = aws_mappings[0]
                    mappings.append({
                        "original_service": service_dict["service_name"],
                        "original_provider": service_dict["provider"],
                        "aws_service": best_mapping.aws_service,
                        "aws_service_category": best_mapping.aws_service_category,
                        "aws_service_type": best_mapping.aws_service_type,
                        "specifications": best_mapping.specifications,
                        "confidence_score": best_mapping.confidence_score,
                        "explanation": best_mapping.explanation,
                        "alternatives": best_mapping.alternatives
                    })
            
            logger.info(f"Successfully mapped {len(mappings)} services")
            
            return {
                "success": True,
                "mappings": mappings,
                "count": len(mappings),
                "message": f"Successfully mapped {len(mappings)} service(s) to AWS"
            }
            
        except Exception as e:
            logger.error(f"Error mapping services: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to map services: {str(e)}"
            }
    
    def calculate_pricing(
        self,
        aws_services: List[Dict[str, Any]],
        region: str = "us-east-1",
        pricing_model: str = "on-demand"
    ) -> Dict[str, Any]:
        """
        Calculate AWS service pricing.
        
        Args:
            aws_services: List of AWS service dictionaries
            region: AWS region for pricing
            pricing_model: Pricing model (on-demand, reserved, savings-plan)
        
        Returns:
            Dictionary with pricing results and status
        """
        try:
            logger.info(f"Calculating pricing for {len(aws_services)} services in {region}")
            
            pricing_results = []
            total_monthly = 0
            total_annual = 0
            
            for service_dict in aws_services:
                # Convert dict to AWSServiceMapping
                mapping = AWSServiceMapping(
                    aws_service=service_dict["aws_service"],
                    aws_service_category=service_dict.get("aws_service_category", ""),
                    aws_service_type=service_dict["aws_service_type"],
                    specifications=service_dict.get("specifications", {}),
                    confidence_score=service_dict.get("confidence_score", 1.0),
                    explanation=service_dict.get("explanation", ""),
                    alternatives=service_dict.get("alternatives", [])
                )
                
                # Calculate pricing
                pricing = self.calculator.calculate_price(
                    mapping,
                    region=region,
                    pricing_model=pricing_model
                )
                
                pricing_results.append({
                    "aws_service": mapping.aws_service,
                    "aws_service_type": mapping.aws_service_type,
                    "monthly_cost": float(pricing.monthly_cost),
                    "annual_cost": float(pricing.annual_cost),
                    "pricing_model": pricing.pricing_model,
                    "region": pricing.region,
                    "breakdown": {k: float(v) for k, v in pricing.breakdown.items()},
                    "currency": pricing.currency
                })
                
                total_monthly += pricing.monthly_cost
                total_annual += pricing.annual_cost
            
            logger.info(f"Successfully calculated pricing: ${total_monthly:.2f}/month")
            
            return {
                "success": True,
                "pricing_results": pricing_results,
                "total_monthly_cost": float(total_monthly),
                "total_annual_cost": float(total_annual),
                "currency": "USD",
                "region": region,
                "pricing_model": pricing_model,
                "message": f"Successfully calculated pricing for {len(pricing_results)} service(s)"
            }
            
        except Exception as e:
            logger.error(f"Error calculating pricing: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to calculate pricing: {str(e)}"
            }
    
    def generate_quote(
        self,
        user_id: str,
        original_input: str,
        parsed_services: List[Dict[str, Any]],
        aws_mappings: List[Dict[str, Any]],
        pricing_results: List[Dict[str, Any]],
        region: str = "us-east-1",
        language: str = "en",
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate pricing quote document.
        
        Args:
            user_id: User ID requesting the quote
            original_input: Original configuration input
            parsed_services: List of parsed services
            aws_mappings: List of AWS mappings
            pricing_results: List of pricing results
            region: Primary AWS region
            language: Output language (en or zh)
            notes: Optional notes
        
        Returns:
            Dictionary with quote information and status
        """
        try:
            logger.info(f"Generating quote for user {user_id}")
            
            # Convert dicts back to objects
            services = [
                ServiceConfig(
                    provider=s["provider"],
                    service_type=s["service_type"],
                    service_name=s["service_name"],
                    specifications=s.get("specifications", {}),
                    region=s.get("region"),
                    quantity=s.get("quantity", 1)
                )
                for s in parsed_services
            ]
            
            mappings = [
                AWSServiceMapping(
                    aws_service=m["aws_service"],
                    aws_service_category=m.get("aws_service_category", ""),
                    aws_service_type=m["aws_service_type"],
                    specifications=m.get("specifications", {}),
                    confidence_score=m.get("confidence_score", 1.0),
                    explanation=m.get("explanation", ""),
                    alternatives=m.get("alternatives", [])
                )
                for m in aws_mappings
            ]
            
            from decimal import Decimal
            from datetime import datetime
            
            pricing = [
                PricingResult(
                    monthly_cost=Decimal(str(p["monthly_cost"])),
                    annual_cost=Decimal(str(p["annual_cost"])),
                    pricing_model=p["pricing_model"],
                    region=p["region"],
                    breakdown={k: Decimal(str(v)) for k, v in p["breakdown"].items()},
                    currency=p.get("currency", "USD"),
                    last_updated=datetime.now()
                )
                for p in pricing_results
            ]
            
            # Generate quote
            quote = self.generator.generate_quote(
                user_id=user_id,
                original_input=original_input,
                parsed_services=services,
                aws_mappings=mappings,
                pricing_results=pricing,
                region=region,
                language=language,
                notes=notes
            )
            
            logger.info(f"Successfully generated quote: {quote.quote_id}")
            
            return {
                "success": True,
                "quote_id": quote.quote_id,
                "total_monthly_cost": float(quote.total_monthly_cost),
                "total_annual_cost": float(quote.total_annual_cost),
                "service_count": len(services),
                "region": region,
                "language": language,
                "message": f"Successfully generated quote {quote.quote_id}"
            }
            
        except Exception as e:
            logger.error(f"Error generating quote: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to generate quote: {str(e)}"
            }
    
    def query_knowledge_base(
        self,
        query: str,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Query Bedrock Knowledge Base.
        
        Args:
            query: Query string
            max_results: Maximum number of results
        
        Returns:
            Dictionary with query results and status
        """
        try:
            logger.info(f"Querying Knowledge Base: {query}")
            
            results = self.kb_service.query(query, max_results=max_results)
            
            logger.info(f"Found {len(results)} results")
            
            return {
                "success": True,
                "results": results,
                "count": len(results),
                "message": f"Found {len(results)} result(s)"
            }
            
        except Exception as e:
            logger.error(f"Error querying Knowledge Base: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to query Knowledge Base: {str(e)}"
            }
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for Strands Agent."""
        return TOOL_DEFINITIONS
    
    def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name.
        
        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool
        
        Returns:
            Tool execution result
        """
        tool_map = {
            "parse_configuration": self.parse_configuration,
            "map_services": self.map_services,
            "calculate_pricing": self.calculate_pricing,
            "generate_quote": self.generate_quote,
            "query_knowledge_base": self.query_knowledge_base
        }
        
        if tool_name not in tool_map:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "message": f"Tool '{tool_name}' not found"
            }
        
        try:
            return tool_map[tool_name](**tool_input)
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to execute tool '{tool_name}': {str(e)}"
            }
