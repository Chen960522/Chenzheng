"""
AWS Pricing Assistant Agent using Strands Agents SDK and Bedrock AgentCore.

This agent orchestrates the complete pricing workflow:
1. Parse cloud service configurations
2. Map services to AWS equivalents
3. Calculate AWS pricing
4. Generate comprehensive quotes
"""

from typing import Dict, Any, List, Optional
import json

from .tools import AgentTools, TOOL_DEFINITIONS
from .prompts import get_system_prompt
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PricingAgent:
    """
    AWS Pricing Assistant Agent.
    
    Uses Strands Agents SDK with Bedrock AgentCore to orchestrate
    the pricing workflow through tool calling and conversation management.
    """
    
    def __init__(
        self,
        model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0",
        region: str = "us-east-1",
        language: str = "en"
    ):
        """
        Initialize the Pricing Agent.
        
        Args:
            model_id: Bedrock model ID to use
            region: AWS region for Bedrock
            language: Default language for responses ('en' or 'zh')
        """
        self.model_id = model_id
        self.region = region
        self.language = language
        self.tools = AgentTools()
        self.conversation_history = []
        
        logger.info(f"PricingAgent initialized with model {model_id}")
    
    def process_request(
        self,
        user_message: str,
        user_id: str,
        session_id: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user request through the agent workflow.
        
        Args:
            user_message: User's input message
            user_id: User ID making the request
            session_id: Optional session ID for conversation continuity
            language: Optional language override ('en' or 'zh')
        
        Returns:
            Dictionary with agent response and any generated artifacts
        """
        try:
            logger.info(f"Processing request from user {user_id}")
            
            # Detect language if not specified
            if language is None:
                language = self._detect_language(user_message)
            
            # Add user message to history
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            
            # Get system prompt
            system_prompt = get_system_prompt(language)
            
            # For now, we'll implement a simplified workflow
            # In production, this would use Strands Agents SDK with AgentCore
            response = self._execute_workflow(
                user_message=user_message,
                user_id=user_id,
                language=language,
                system_prompt=system_prompt
            )
            
            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response["message"]
            })
            
            logger.info(f"Successfully processed request")
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"抱歉，处理请求时出错：{str(e)}" if language == "zh" else f"Sorry, an error occurred: {str(e)}"
            }
    
    def _detect_language(self, text: str) -> str:
        """
        Detect if text is primarily Chinese or English.
        
        Args:
            text: Text to analyze
        
        Returns:
            Language code ('en' or 'zh')
        """
        # Simple heuristic: count Chinese characters
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        total_chars = len(text.replace(' ', ''))
        
        if total_chars > 0 and chinese_chars / total_chars > 0.3:
            return "zh"
        return "en"
    
    def _execute_workflow(
        self,
        user_message: str,
        user_id: str,
        language: str,
        system_prompt: str
    ) -> Dict[str, Any]:
        """
        Execute the pricing workflow.
        
        This is a simplified implementation. In production, this would use
        Strands Agents SDK with AgentCore for more sophisticated orchestration.
        
        Args:
            user_message: User's message
            user_id: User ID
            language: Language code
            system_prompt: System prompt to use
        
        Returns:
            Workflow execution result
        """
        # Try to detect if this is a configuration input
        if self._looks_like_configuration(user_message):
            return self._process_configuration_workflow(
                user_message=user_message,
                user_id=user_id,
                language=language
            )
        else:
            # This is a conversational message
            return {
                "success": True,
                "message": self._generate_conversational_response(user_message, language),
                "type": "conversation"
            }
    
    def _looks_like_configuration(self, text: str) -> bool:
        """
        Check if text looks like a service configuration.
        
        Args:
            text: Text to check
        
        Returns:
            True if it looks like a configuration
        """
        # Check for JSON/YAML/CSV patterns
        if text.strip().startswith('{') or text.strip().startswith('['):
            return True
        if 'services:' in text or 'provider:' in text:
            return True
        if 'ECS' in text or 'OSS' in text or 'CVM' in text or 'OBS' in text:
            return True
        if 'EC2' in text or 'S3' in text or 'RDS' in text:
            return True
        
        # Check for keywords
        keywords = ['instance', 'storage', 'database', 'compute', 'cpu', 'memory', 'alibaba', 'huawei', 'tencent', 'gcp', 'azure']
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in keywords)
    
    def _process_configuration_workflow(
        self,
        user_message: str,
        user_id: str,
        language: str
    ) -> Dict[str, Any]:
        """
        Process a configuration through the complete workflow.
        
        Args:
            user_message: Configuration text
            user_id: User ID
            language: Language code
        
        Returns:
            Workflow result with quote
        """
        workflow_steps = []
        
        # Step 1: Parse configuration
        logger.info("Step 1: Parsing configuration")
        parse_result = self.tools.parse_configuration(user_message)
        workflow_steps.append({"step": "parse", "result": parse_result})
        
        if not parse_result["success"]:
            return {
                "success": False,
                "error": parse_result["error"],
                "message": parse_result["message"],
                "workflow_steps": workflow_steps
            }
        
        parsed_services = parse_result["services"]
        
        # Step 2: Map services
        logger.info("Step 2: Mapping services to AWS")
        map_result = self.tools.map_services(parsed_services)
        workflow_steps.append({"step": "map", "result": map_result})
        
        if not map_result["success"]:
            return {
                "success": False,
                "error": map_result["error"],
                "message": map_result["message"],
                "workflow_steps": workflow_steps
            }
        
        aws_mappings = map_result["mappings"]
        
        # Step 3: Calculate pricing
        logger.info("Step 3: Calculating pricing")
        pricing_result = self.tools.calculate_pricing(aws_mappings)
        workflow_steps.append({"step": "pricing", "result": pricing_result})
        
        if not pricing_result["success"]:
            return {
                "success": False,
                "error": pricing_result["error"],
                "message": pricing_result["message"],
                "workflow_steps": workflow_steps
            }
        
        # Step 4: Generate quote
        logger.info("Step 4: Generating quote")
        quote_result = self.tools.generate_quote(
            user_id=user_id,
            original_input=user_message,
            parsed_services=parsed_services,
            aws_mappings=aws_mappings,
            pricing_results=pricing_result["pricing_results"],
            language=language
        )
        workflow_steps.append({"step": "quote", "result": quote_result})
        
        if not quote_result["success"]:
            return {
                "success": False,
                "error": quote_result["error"],
                "message": quote_result["message"],
                "workflow_steps": workflow_steps
            }
        
        # Generate summary message
        summary = self._generate_summary_message(
            parsed_services=parsed_services,
            aws_mappings=aws_mappings,
            pricing_result=pricing_result,
            quote_result=quote_result,
            language=language
        )
        
        return {
            "success": True,
            "message": summary,
            "quote_id": quote_result["quote_id"],
            "total_monthly_cost": pricing_result["total_monthly_cost"],
            "total_annual_cost": pricing_result["total_annual_cost"],
            "service_count": len(parsed_services),
            "workflow_steps": workflow_steps,
            "type": "quote"
        }
    
    def _generate_summary_message(
        self,
        parsed_services: List[Dict],
        aws_mappings: List[Dict],
        pricing_result: Dict,
        quote_result: Dict,
        language: str
    ) -> str:
        """Generate a summary message for the user."""
        if language == "zh":
            message = f"""✅ 报价生成成功！

📋 **服务摘要**
- 解析了 {len(parsed_services)} 个服务
- 映射到 {len(aws_mappings)} 个 AWS 服务

💰 **定价摘要**
- 月度费用: ${pricing_result['total_monthly_cost']:.2f}
- 年度费用: ${pricing_result['total_annual_cost']:.2f}
- 货币: {pricing_result['currency']}
- 区域: {pricing_result['region']}

📄 **报价单**
- 报价 ID: {quote_result['quote_id']}

**服务映射详情:**
"""
            for i, mapping in enumerate(aws_mappings, 1):
                message += f"\n{i}. {mapping['original_service']} ({mapping['original_provider']}) → {mapping['aws_service']} ({mapping['aws_service_type']})"
                message += f"\n   置信度: {mapping['confidence_score']:.0%}"
                message += f"\n   说明: {mapping['explanation']}"
        else:
            message = f"""✅ Quote generated successfully!

📋 **Service Summary**
- Parsed {len(parsed_services)} service(s)
- Mapped to {len(aws_mappings)} AWS service(s)

💰 **Pricing Summary**
- Monthly Cost: ${pricing_result['total_monthly_cost']:.2f}
- Annual Cost: ${pricing_result['total_annual_cost']:.2f}
- Currency: {pricing_result['currency']}
- Region: {pricing_result['region']}

📄 **Quote**
- Quote ID: {quote_result['quote_id']}

**Service Mapping Details:**
"""
            for i, mapping in enumerate(aws_mappings, 1):
                message += f"\n{i}. {mapping['original_service']} ({mapping['original_provider']}) → {mapping['aws_service']} ({mapping['aws_service_type']})"
                message += f"\n   Confidence: {mapping['confidence_score']:.0%}"
                message += f"\n   Explanation: {mapping['explanation']}"
        
        return message
    
    def _generate_conversational_response(self, user_message: str, language: str) -> str:
        """Generate a conversational response."""
        if language == "zh":
            return """你好！我是 AWS 智能定价助手。

我可以帮助你：
1. 解析云服务配置（支持 JSON、YAML、CSV 或纯文本）
2. 将其他云服务商的服务映射到 AWS 等效服务
3. 计算 AWS 服务定价
4. 生成专业的报价文档

请提供你的云服务配置，我会帮你生成 AWS 报价。你可以直接粘贴配置文本，或者描述你需要的服务。"""
        else:
            return """Hello! I'm the AWS Pricing Assistant.

I can help you:
1. Parse cloud service configurations (JSON, YAML, CSV, or plain text)
2. Map services from other cloud providers to AWS equivalents
3. Calculate AWS service pricing
4. Generate professional pricing quotes

Please provide your cloud service configuration, and I'll help you generate an AWS quote. You can paste the configuration text directly or describe the services you need."""
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the conversation history."""
        return self.conversation_history
    
    def clear_conversation_history(self):
        """Clear the conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get the tool definitions for this agent."""
        return self.tools.get_tool_definitions()
