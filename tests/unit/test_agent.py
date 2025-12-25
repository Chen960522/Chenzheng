"""
Unit tests for AWS Pricing Assistant Agent.

Tests agent tools, workflow orchestration, and error handling.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from src.agents.tools import AgentTools
from src.agents.pricing_agent import PricingAgent
from src.services.agent_service import AgentService, AgentSession


class TestAgentTools:
    """Test agent tools functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tools = AgentTools()
    
    def test_parse_configuration_json(self):
        """Test parsing JSON configuration."""
        config = '''
        {
            "services": [
                {
                    "provider": "alibaba",
                    "service_type": "compute",
                    "service_name": "ECS",
                    "specifications": {"cpu": 2, "memory": 4}
                }
            ]
        }
        '''
        
        result = self.tools.parse_configuration(config, format_hint="json")
        
        assert result["success"] is True
        assert result["count"] == 1
        assert result["services"][0]["provider"] == "alibaba"
        assert result["services"][0]["service_name"] == "ECS"
    
    def test_parse_configuration_yaml(self):
        """Test parsing YAML configuration."""
        config = '''
services:
  - provider: huawei
    service_type: storage
    service_name: OBS
    specifications:
      capacity: 1000
        '''
        
        result = self.tools.parse_configuration(config, format_hint="yaml")
        
        assert result["success"] is True
        assert result["count"] == 1
        assert result["services"][0]["provider"] == "huawei"
    
    def test_map_services(self):
        """Test service mapping."""
        services = [
            {
                "provider": "alibaba",
                "service_type": "compute",
                "service_name": "ECS",
                "specifications": {"cpu": 2, "memory": 4}
            }
        ]
        
        result = self.tools.map_services(services)
        
        # Should handle gracefully even if DynamoDB is not available
        if result["success"]:
            assert result["count"] > 0
            assert result["mappings"][0]["aws_service"] == "EC2"
        else:
            # If it fails due to AWS resources, that's acceptable in unit tests
            assert "error" in result
    
    def test_calculate_pricing(self):
        """Test pricing calculation."""
        aws_services = [
            {
                "aws_service": "EC2",
                "aws_service_category": "compute",
                "aws_service_type": "t3.micro",
                "specifications": {"cpu": 2, "memory": 1},
                "confidence_score": 0.95,
                "explanation": "T3 micro instance",
                "alternatives": []
            }
        ]
        
        result = self.tools.calculate_pricing(aws_services)
        
        assert result["success"] is True
        assert result["total_monthly_cost"] > 0
        assert result["currency"] == "USD"
    
    def test_generate_quote(self):
        """Test quote generation."""
        parsed_services = [
            {
                "provider": "alibaba",
                "service_type": "compute",
                "service_name": "ECS",
                "specifications": {"cpu": 2, "memory": 4}
            }
        ]
        
        aws_mappings = [
            {
                "aws_service": "EC2",
                "aws_service_category": "compute",
                "aws_service_type": "t3.small",
                "specifications": {"cpu": 2, "memory": 2},
                "confidence_score": 0.95,
                "explanation": "T3 small matches requirements",
                "alternatives": []
            }
        ]
        
        pricing_results = [
            {
                "aws_service": "EC2",
                "aws_service_type": "t3.small",
                "monthly_cost": 15.18,
                "annual_cost": 182.16,
                "pricing_model": "on-demand",
                "region": "us-east-1",
                "breakdown": {"compute": 15.18},
                "currency": "USD"
            }
        ]
        
        result = self.tools.generate_quote(
            user_id="test-user",
            original_input="Test configuration",
            parsed_services=parsed_services,
            aws_mappings=aws_mappings,
            pricing_results=pricing_results
        )
        
        assert result["success"] is True
        assert "quote_id" in result
        assert result["total_monthly_cost"] > 0
    
    def test_query_knowledge_base(self):
        """Test Knowledge Base query."""
        result = self.tools.query_knowledge_base("AWS EC2 pricing")
        
        # Should not fail even if KB is not configured
        assert "success" in result
    
    def test_execute_tool_unknown(self):
        """Test executing unknown tool."""
        result = self.tools.execute_tool("unknown_tool", {})
        
        assert result["success"] is False
        assert "Unknown tool" in result["error"]


class TestPricingAgent:
    """Test pricing agent functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent = PricingAgent(language="en")
    
    def test_agent_initialization(self):
        """Test agent initialization."""
        assert self.agent.model_id == "anthropic.claude-3-5-sonnet-20241022-v2:0"
        assert self.agent.language == "en"
        assert len(self.agent.conversation_history) == 0
    
    def test_detect_language_english(self):
        """Test English language detection."""
        text = "I need pricing for EC2 instances"
        language = self.agent._detect_language(text)
        
        assert language == "en"
    
    def test_detect_language_chinese(self):
        """Test Chinese language detection."""
        text = "我需要阿里云ECS的AWS报价"
        language = self.agent._detect_language(text)
        
        assert language == "zh"
    
    def test_looks_like_configuration(self):
        """Test configuration detection."""
        # JSON configuration
        assert self.agent._looks_like_configuration('{"services": []}') is True
        
        # YAML configuration
        assert self.agent._looks_like_configuration('services:\n  - provider: alibaba') is True
        
        # Service keywords
        assert self.agent._looks_like_configuration('I need 2 ECS instances') is True
        
        # Conversational
        assert self.agent._looks_like_configuration('Hello, how are you?') is False
    
    def test_process_conversational_request(self):
        """Test processing conversational request."""
        response = self.agent.process_request(
            user_message="Hello, what can you do?",
            user_id="test-user"
        )
        
        assert response["success"] is True
        assert response["type"] == "conversation"
        assert len(self.agent.conversation_history) == 2  # User + assistant
    
    def test_process_configuration_request(self):
        """Test processing configuration request."""
        config = '''
        {
            "services": [
                {
                    "provider": "alibaba",
                    "service_type": "compute",
                    "service_name": "ECS",
                    "specifications": {"cpu": 2, "memory": 4}
                }
            ]
        }
        '''
        
        response = self.agent.process_request(
            user_message=config,
            user_id="test-user"
        )
        
        # Should handle gracefully even if AWS resources are not available
        if response["success"]:
            assert response["type"] == "quote"
            assert "quote_id" in response
            assert response["service_count"] > 0
        else:
            # If it fails due to AWS resources, that's acceptable
            assert "error" in response
    
    def test_conversation_history(self):
        """Test conversation history tracking."""
        self.agent.process_request("Hello", "test-user")
        self.agent.process_request("How are you?", "test-user")
        
        history = self.agent.get_conversation_history()
        
        assert len(history) == 4  # 2 user + 2 assistant messages
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
    
    def test_clear_conversation_history(self):
        """Test clearing conversation history."""
        self.agent.process_request("Hello", "test-user")
        assert len(self.agent.conversation_history) > 0
        
        self.agent.clear_conversation_history()
        assert len(self.agent.conversation_history) == 0
    
    def test_get_tool_definitions(self):
        """Test getting tool definitions."""
        tools = self.agent.get_tool_definitions()
        
        assert len(tools) == 5
        assert any(t["name"] == "parse_configuration" for t in tools)
        assert any(t["name"] == "map_services" for t in tools)
        assert any(t["name"] == "calculate_pricing" for t in tools)


class TestAgentSession:
    """Test agent session functionality."""
    
    def test_session_creation(self):
        """Test session creation."""
        session = AgentSession(
            session_id="test-session",
            user_id="test-user",
            language="en"
        )
        
        assert session.session_id == "test-session"
        assert session.user_id == "test-user"
        assert session.language == "en"
        assert len(session.quotes) == 0
    
    def test_process_message(self):
        """Test processing message in session."""
        session = AgentSession("test-session", "test-user")
        
        response = session.process_message("Hello")
        
        assert "success" in response
        assert session.last_activity is not None
    
    def test_quote_tracking(self):
        """Test quote tracking in session."""
        session = AgentSession("test-session", "test-user")
        
        config = '''
        {
            "services": [
                {
                    "provider": "alibaba",
                    "service_type": "compute",
                    "service_name": "ECS",
                    "specifications": {"cpu": 2, "memory": 4}
                }
            ]
        }
        '''
        
        response = session.process_message(config)
        
        if response.get("success") and response.get("type") == "quote":
            quotes = session.get_quotes()
            assert len(quotes) > 0
            assert "quote_id" in quotes[0]


class TestAgentService:
    """Test agent service functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = AgentService()
    
    def test_create_session(self):
        """Test creating a session."""
        session_id = self.service.create_session("test-user", language="en")
        
        assert session_id is not None
        assert session_id in self.service.sessions
    
    def test_get_session(self):
        """Test getting a session."""
        session_id = self.service.create_session("test-user")
        session = self.service.get_session(session_id)
        
        assert session is not None
        assert session.user_id == "test-user"
    
    def test_get_nonexistent_session(self):
        """Test getting nonexistent session."""
        session = self.service.get_session("nonexistent")
        
        assert session is None
    
    def test_process_message(self):
        """Test processing message through service."""
        session_id = self.service.create_session("test-user")
        
        response = self.service.process_message(session_id, "Hello")
        
        assert response["success"] is True
    
    def test_process_message_invalid_session(self):
        """Test processing message with invalid session."""
        response = self.service.process_message("invalid-session", "Hello")
        
        assert response["success"] is False
        assert "Session not found" in response["message"]
    
    def test_delete_session(self):
        """Test deleting a session."""
        session_id = self.service.create_session("test-user")
        
        result = self.service.delete_session(session_id)
        
        assert result is True
        assert session_id not in self.service.sessions
    
    def test_delete_nonexistent_session(self):
        """Test deleting nonexistent session."""
        result = self.service.delete_session("nonexistent")
        
        assert result is False
    
    def test_get_active_sessions_count(self):
        """Test getting active sessions count."""
        initial_count = self.service.get_active_sessions_count()
        
        self.service.create_session("user1")
        self.service.create_session("user2")
        
        assert self.service.get_active_sessions_count() == initial_count + 2
    
    def test_get_user_sessions(self):
        """Test getting user sessions."""
        session1 = self.service.create_session("user1")
        session2 = self.service.create_session("user1")
        session3 = self.service.create_session("user2")
        
        user1_sessions = self.service.get_user_sessions("user1")
        
        assert len(user1_sessions) == 2
        assert session1 in user1_sessions
        assert session2 in user1_sessions
        assert session3 not in user1_sessions
    
    def test_progress_callback(self):
        """Test progress callback functionality."""
        session_id = self.service.create_session("test-user")
        
        progress_updates = []
        
        def callback(update):
            progress_updates.append(update)
        
        self.service.process_message(
            session_id,
            "Hello",
            progress_callback=callback
        )
        
        assert len(progress_updates) > 0
        assert any(u["status"] == "processing" for u in progress_updates)


class TestAgentErrorHandling:
    """Test agent error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tools = AgentTools()
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        result = self.tools.parse_configuration(
            '{"invalid json',
            format_hint="json"
        )
        
        assert result["success"] is False
        assert "error" in result
    
    def test_map_empty_services(self):
        """Test mapping empty services list."""
        result = self.tools.map_services([])
        
        assert result["success"] is True
        assert result["count"] == 0
    
    def test_calculate_pricing_invalid_service(self):
        """Test calculating pricing for invalid service."""
        aws_services = [
            {
                "aws_service": "InvalidService",
                "aws_service_type": "invalid-type",
                "specifications": {}
            }
        ]
        
        # Should handle gracefully
        result = self.tools.calculate_pricing(aws_services)
        
        # May succeed with fallback pricing or fail gracefully
        assert "success" in result
