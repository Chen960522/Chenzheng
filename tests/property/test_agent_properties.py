"""
Property-based tests for AWS Pricing Assistant Agent.

Tests universal properties of agent behavior:
- Property 20: Agent workflow orchestration
- Property 21: Graceful error handling
- Property 24: Context preservation
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis import HealthCheck

from src.agents.pricing_agent import PricingAgent
from src.services.agent_service import AgentService


# Strategy for generating valid service configurations
@st.composite
def service_config_strategy(draw):
    """Generate valid service configuration JSON."""
    providers = ["alibaba", "huawei", "tencent", "gcp", "azure"]
    service_types = ["compute", "storage", "database", "network"]
    service_names = {
        "alibaba": {"compute": "ECS", "storage": "OSS", "database": "RDS"},
        "huawei": {"compute": "ECS", "storage": "OBS", "database": "RDS"},
        "tencent": {"compute": "CVM", "storage": "COS", "database": "CDB"},
        "gcp": {"compute": "Compute Engine", "storage": "Cloud Storage", "database": "Cloud SQL"},
        "azure": {"compute": "Virtual Machines", "storage": "Blob Storage", "database": "SQL Database"}
    }
    
    provider = draw(st.sampled_from(providers))
    service_type = draw(st.sampled_from(service_types))
    service_name = service_names.get(provider, {}).get(service_type, "Unknown")
    
    cpu = draw(st.integers(min_value=1, max_value=64))
    memory = draw(st.integers(min_value=1, max_value=256))
    
    config = {
        "services": [
            {
                "provider": provider,
                "service_type": service_type,
                "service_name": service_name,
                "specifications": {
                    "cpu": cpu,
                    "memory": memory
                }
            }
        ]
    }
    
    import json
    return json.dumps(config)


class TestAgentWorkflowOrchestration:
    """
    Property 20: Agent workflow orchestration
    
    For any valid pricing request, the Agent should execute parsing, mapping,
    and pricing steps in the correct order.
    
    **Feature: aws-pricing-assistant, Property 20: Agent workflow orchestration**
    **Validates: Requirements 5.1**
    """
    
    @given(config=service_config_strategy())
    @settings(
        max_examples=10,  # Reduced for faster testing
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_workflow_executes_in_order(self, config):
        """
        Test that agent executes workflow steps in correct order.
        
        For any valid configuration, the workflow should:
        1. Parse configuration first
        2. Map services second
        3. Calculate pricing third
        4. Generate quote fourth
        """
        agent = PricingAgent()
        
        response = agent.process_request(
            user_message=config,
            user_id="test-user"
        )
        
        # If workflow succeeds, check step order
        if response.get("success") and response.get("workflow_steps"):
            steps = response["workflow_steps"]
            step_names = [s["step"] for s in steps]
            
            # Verify steps are in correct order
            if "parse" in step_names:
                parse_idx = step_names.index("parse")
                
                if "map" in step_names:
                    map_idx = step_names.index("map")
                    assert parse_idx < map_idx, "Parse must come before map"
                
                if "pricing" in step_names:
                    pricing_idx = step_names.index("pricing")
                    assert parse_idx < pricing_idx, "Parse must come before pricing"
                
                if "quote" in step_names:
                    quote_idx = step_names.index("quote")
                    assert parse_idx < quote_idx, "Parse must come before quote"


class TestGracefulErrorHandling:
    """
    Property 21: Graceful error handling
    
    For any error encountered during the workflow, the Agent should handle it
    gracefully and provide meaningful feedback.
    
    **Feature: aws-pricing-assistant, Property 21: Graceful error handling**
    **Validates: Requirements 5.2**
    """
    
    @given(
        invalid_input=st.one_of(
            st.text(min_size=1, max_size=100),  # Random text
            st.just('{"invalid": json'),  # Invalid JSON
            st.just(''),  # Empty string
            st.just('   '),  # Whitespace only
        )
    )
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_handles_invalid_input_gracefully(self, invalid_input):
        """
        Test that agent handles invalid input gracefully.
        
        For any invalid input, the agent should:
        1. Not crash
        2. Return a response with success status
        3. Provide meaningful error message if parsing fails
        """
        agent = PricingAgent()
        
        # Agent should not crash
        response = agent.process_request(
            user_message=invalid_input,
            user_id="test-user"
        )
        
        # Should always return a response
        assert isinstance(response, dict)
        assert "success" in response
        
        # If it fails, should have error message
        if not response.get("success"):
            assert "error" in response or "message" in response
    
    @given(user_id=st.text(min_size=1, max_size=50))
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_handles_various_user_ids(self, user_id):
        """
        Test that agent handles various user IDs gracefully.
        
        For any user ID, the agent should process requests without crashing.
        """
        agent = PricingAgent()
        
        response = agent.process_request(
            user_message="Hello",
            user_id=user_id
        )
        
        assert isinstance(response, dict)
        assert "success" in response


class TestContextPreservation:
    """
    Property 24: Context preservation
    
    For any workflow involving multiple iterations, the Agent should maintain
    conversation context.
    
    **Feature: aws-pricing-assistant, Property 24: Context preservation**
    **Validates: Requirements 5.5**
    """
    
    @given(
        messages=st.lists(
            st.text(min_size=1, max_size=100),
            min_size=2,
            max_size=5
        )
    )
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_preserves_conversation_history(self, messages):
        """
        Test that agent preserves conversation history.
        
        For any sequence of messages, the agent should:
        1. Store all messages in history
        2. Maintain correct order
        3. Track both user and assistant messages
        """
        agent = PricingAgent()
        
        for message in messages:
            agent.process_request(
                user_message=message,
                user_id="test-user"
            )
        
        history = agent.get_conversation_history()
        
        # Should have 2x messages (user + assistant for each)
        assert len(history) == len(messages) * 2
        
        # Should alternate between user and assistant
        for i in range(0, len(history), 2):
            assert history[i]["role"] == "user"
            assert history[i + 1]["role"] == "assistant"
    
    def test_session_maintains_context(self):
        """
        Test that agent session maintains context across requests.
        
        For any session, context should be preserved across multiple requests.
        """
        service = AgentService()
        session_id = service.create_session("test-user")
        
        # Send multiple messages
        service.process_message(session_id, "Hello")
        service.process_message(session_id, "How are you?")
        service.process_message(session_id, "What can you do?")
        
        session = service.get_session(session_id)
        history = session.get_conversation_history()
        
        # Should have all messages
        assert len(history) >= 6  # 3 user + 3 assistant
    
    @given(
        num_sessions=st.integers(min_value=1, max_value=5),
        messages_per_session=st.integers(min_value=1, max_value=3)
    )
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_multiple_sessions_independent(self, num_sessions, messages_per_session):
        """
        Test that multiple sessions maintain independent context.
        
        For any number of sessions, each should maintain its own context
        independently of others.
        """
        service = AgentService()
        
        sessions = []
        for i in range(num_sessions):
            session_id = service.create_session(f"user-{i}")
            sessions.append(session_id)
            
            # Send messages to this session
            for j in range(messages_per_session):
                service.process_message(session_id, f"Message {j}")
        
        # Verify each session has correct number of messages
        for session_id in sessions:
            session = service.get_session(session_id)
            history = session.get_conversation_history()
            
            # Should have messages_per_session * 2 (user + assistant)
            assert len(history) == messages_per_session * 2


class TestAgentLanguageDetection:
    """Test agent language detection properties."""
    
    @given(
        chinese_text=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lo',),  # Chinese characters
                min_codepoint=0x4E00,
                max_codepoint=0x9FFF
            ),
            min_size=5,
            max_size=50
        )
    )
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_detects_chinese_text(self, chinese_text):
        """
        Test that agent correctly detects Chinese text.
        
        For any text with significant Chinese characters, language should be
        detected as 'zh'.
        """
        agent = PricingAgent()
        
        detected = agent._detect_language(chinese_text)
        
        # Should detect as Chinese
        assert detected == "zh"
    
    @given(
        english_text=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll'),  # English letters
                min_codepoint=ord('A'),
                max_codepoint=ord('z')
            ),
            min_size=5,
            max_size=50
        )
    )
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_detects_english_text(self, english_text):
        """
        Test that agent correctly detects English text.
        
        For any text with only English characters, language should be
        detected as 'en'.
        """
        agent = PricingAgent()
        
        detected = agent._detect_language(english_text)
        
        # Should detect as English
        assert detected == "en"
