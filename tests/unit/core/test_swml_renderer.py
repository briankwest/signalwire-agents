"""
Unit tests for SWML renderer module
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any, Optional

from signalwire_agents.core.swml_renderer import SwmlRenderer


class TestSwmlRenderer:
    """Test SwmlRenderer functionality"""
    
    def test_render_swml_basic(self):
        """Test basic SWML rendering"""
        result = SwmlRenderer.render_swml("You are a helpful assistant")
        
        assert isinstance(result, str)
        parsed = json.loads(result)
        
        assert parsed["version"] == "1.0.0"
        assert "sections" in parsed
        assert "main" in parsed["sections"]
        assert len(parsed["sections"]["main"]) == 1
        
        # Check AI verb structure
        ai_verb = parsed["sections"]["main"][0]
        assert "ai" in ai_verb
        assert ai_verb["ai"]["prompt"]["text"] == "You are a helpful assistant"
    
    def test_render_swml_with_post_prompt(self):
        """Test SWML rendering with post prompt"""
        result = SwmlRenderer.render_swml(
            "You are helpful",
            post_prompt="Provide a summary"
        )
        
        parsed = json.loads(result)
        ai_verb = parsed["sections"]["main"][0]
        
        assert ai_verb["ai"]["post_prompt"]["text"] == "Provide a summary"
    
    def test_render_swml_with_swaig_functions(self):
        """Test SWML rendering with SWAIG functions"""
        functions = [
            {
                "function": "get_weather",
                "description": "Get weather information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"}
                    }
                }
            }
        ]
        
        result = SwmlRenderer.render_swml(
            "You are helpful",
            swaig_functions=functions
        )
        
        parsed = json.loads(result)
        ai_verb = parsed["sections"]["main"][0]
        
        assert "SWAIG" in ai_verb["ai"]
        assert "functions" in ai_verb["ai"]["SWAIG"]
        assert len(ai_verb["ai"]["SWAIG"]["functions"]) == 1
        assert ai_verb["ai"]["SWAIG"]["functions"][0]["function"] == "get_weather"
    
    def test_render_swml_with_pom(self):
        """Test SWML rendering with POM format"""
        pom_data = [
            {"title": "Section 1", "body": "Content 1"},
            {"title": "Section 2", "body": "Content 2"}
        ]
        
        result = SwmlRenderer.render_swml(
            pom_data,
            prompt_is_pom=True
        )
        
        parsed = json.loads(result)
        ai_verb = parsed["sections"]["main"][0]
        
        assert "pom" in ai_verb["ai"]["prompt"]
        assert ai_verb["ai"]["prompt"]["pom"] == pom_data
    
    def test_render_swml_with_hooks(self):
        """Test SWML rendering with startup and hangup hooks"""
        result = SwmlRenderer.render_swml(
            "You are helpful",
            startup_hook_url="https://example.com/startup",
            hangup_hook_url="https://example.com/hangup"
        )
        
        parsed = json.loads(result)
        ai_verb = parsed["sections"]["main"][0]
        
        assert "SWAIG" in ai_verb["ai"]
        assert "functions" in ai_verb["ai"]["SWAIG"]
        
        # Should have startup and hangup hook functions
        functions = ai_verb["ai"]["SWAIG"]["functions"]
        function_names = [f["function"] for f in functions]
        assert "startup_hook" in function_names
        assert "hangup_hook" in function_names
    
    def test_render_swml_with_default_webhook(self):
        """Test SWML rendering with default webhook URL"""
        result = SwmlRenderer.render_swml(
            "You are helpful",
            default_webhook_url="https://example.com/webhook"
        )
        
        parsed = json.loads(result)
        ai_verb = parsed["sections"]["main"][0]
        
        assert "SWAIG" in ai_verb["ai"]
        assert "defaults" in ai_verb["ai"]["SWAIG"]
        assert ai_verb["ai"]["SWAIG"]["defaults"]["web_hook_url"] == "https://example.com/webhook"
    
    @patch('yaml.dump')
    def test_render_swml_yaml_format(self, mock_yaml_dump):
        """Test SWML rendering in YAML format"""
        mock_yaml_dump.return_value = "version: 1.0.0\nsections:\n  main: []"
        
        result = SwmlRenderer.render_swml(
            "You are helpful",
            format="yaml"
        )
        
        assert isinstance(result, str)
        # Should contain YAML-specific formatting
        assert "version: 1.0.0" in result
        assert "sections:" in result
        assert "main:" in result
        mock_yaml_dump.assert_called_once()
    
    def test_render_function_response_swml_basic(self):
        """Test rendering function response SWML"""
        result = SwmlRenderer.render_function_response_swml("Hello there!")
        
        assert isinstance(result, str)
        parsed = json.loads(result)
        
        assert parsed["version"] == "1.0.0"
        assert "sections" in parsed
        assert "main" in parsed["sections"]
        assert len(parsed["sections"]["main"]) == 1
        
        # Should have a play verb with say: prefix
        play_verb = parsed["sections"]["main"][0]
        assert "play" in play_verb
        assert play_verb["play"]["url"] == "say:Hello there!"
    
    def test_render_function_response_swml_with_actions(self):
        """Test rendering function response SWML with actions"""
        # Use the correct format that the renderer expects (direct SWML verbs)
        actions = [
            {"play": {"url": "test.mp3"}},
            {"hangup": {"reason": "completed"}}
        ]
        
        result = SwmlRenderer.render_function_response_swml(
            "Response complete",
            actions=actions
        )
        
        parsed = json.loads(result)
        main_section = parsed["sections"]["main"]
        
        # Should have play verb for response plus actions
        assert len(main_section) == 3  # response + 2 actions
        
        # Check action types
        verb_types = [list(verb.keys())[0] for verb in main_section]
        assert "play" in verb_types
        assert "hangup" in verb_types
    
    @patch('yaml.dump')
    def test_render_function_response_swml_yaml(self, mock_yaml_dump):
        """Test rendering function response SWML in YAML format"""
        mock_yaml_dump.return_value = "version: 1.0.0\nsections:\n  main: []"
        
        result = SwmlRenderer.render_function_response_swml(
            "Hello",
            format="yaml"
        )
        
        assert isinstance(result, str)
        assert "version: 1.0.0" in result
        assert "sections:" in result
        mock_yaml_dump.assert_called_once()


class TestSwmlRendererErrorHandling:
    """Test error handling in SwmlRenderer"""
    
    def test_render_swml_empty_prompt(self):
        """Test rendering with empty prompt"""
        result = SwmlRenderer.render_swml("")
        
        parsed = json.loads(result)
        ai_verb = parsed["sections"]["main"][0]
        
        assert ai_verb["ai"]["prompt"]["text"] == ""
    
    def test_render_swml_none_prompt(self):
        """Test rendering with None prompt"""
        # Should handle None gracefully
        result = SwmlRenderer.render_swml(None)
        
        parsed = json.loads(result)
        ai_verb = parsed["sections"]["main"][0]
        
        assert ai_verb["ai"]["prompt"]["text"] is None
    
    def test_render_swml_invalid_format(self):
        """Test rendering with invalid format"""
        # Should default to JSON for invalid format
        result = SwmlRenderer.render_swml("Hello", format="invalid")
        
        # Should still be valid JSON
        parsed = json.loads(result)
        assert parsed["version"] == "1.0.0"
    
    def test_render_function_response_empty_text(self):
        """Test rendering function response with empty text"""
        result = SwmlRenderer.render_function_response_swml("")
        
        parsed = json.loads(result)
        
        # Should still create a document but with empty main section
        assert parsed["version"] == "1.0.0"
        assert "sections" in parsed
        assert "main" in parsed["sections"]
        # Empty text should not create a play verb
        assert len(parsed["sections"]["main"]) == 0


class TestSwmlRendererIntegration:
    """Test integration scenarios"""
    
    def test_complete_ai_agent_swml(self):
        """Test rendering complete AI agent SWML"""
        functions = [
            {
                "function": "get_account_balance",
                "description": "Get user account balance",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "account_id": {"type": "string"}
                    },
                    "required": ["account_id"]
                }
            },
            {
                "function": "transfer_funds",
                "description": "Transfer funds between accounts",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "from_account": {"type": "string"},
                        "to_account": {"type": "string"},
                        "amount": {"type": "number"}
                    },
                    "required": ["from_account", "to_account", "amount"]
                }
            }
        ]
        
        result = SwmlRenderer.render_swml(
            prompt="You are a banking assistant. Help users with their account needs.",
            post_prompt="Summarize the conversation and any actions taken.",
            post_prompt_url="https://bank.example.com/conversation-summary",
            swaig_functions=functions,
            startup_hook_url="https://bank.example.com/call-start",
            hangup_hook_url="https://bank.example.com/call-end",
            default_webhook_url="https://bank.example.com/functions",
            params={"temperature": 0.7, "max_tokens": 150}
        )
        
        parsed = json.loads(result)
        ai_verb = parsed["sections"]["main"][0]
        
        # Verify all components are present
        assert ai_verb["ai"]["prompt"]["text"] == "You are a banking assistant. Help users with their account needs."
        assert ai_verb["ai"]["post_prompt"]["text"] == "Summarize the conversation and any actions taken."
        assert ai_verb["ai"]["post_prompt_url"] == "https://bank.example.com/conversation-summary"
        
        # Verify SWAIG configuration
        swaig = ai_verb["ai"]["SWAIG"]
        assert "defaults" in swaig
        assert swaig["defaults"]["web_hook_url"] == "https://bank.example.com/functions"
        
        assert "functions" in swaig
        function_names = [f["function"] for f in swaig["functions"]]
        assert "startup_hook" in function_names
        assert "hangup_hook" in function_names
        assert "get_account_balance" in function_names
        assert "transfer_funds" in function_names
        
        # Verify parameters are in the AI params
        assert "params" in ai_verb["ai"]
        assert ai_verb["ai"]["params"]["temperature"] == 0.7
        assert ai_verb["ai"]["params"]["max_tokens"] == 150
    
    def test_pom_based_agent_swml(self):
        """Test rendering POM-based agent SWML"""
        pom_sections = [
            {
                "title": "Role",
                "body": "You are a customer service representative for TechCorp."
            },
            {
                "title": "Guidelines",
                "bullets": [
                    "Always be polite and professional",
                    "Ask clarifying questions when needed",
                    "Escalate complex issues to human agents"
                ]
            },
            {
                "title": "Available Actions",
                "body": "You can help with account inquiries, technical support, and billing questions."
            }
        ]
        
        result = SwmlRenderer.render_swml(
            prompt=pom_sections,
            prompt_is_pom=True,
            post_prompt="Provide a brief summary of how you helped the customer."
        )
        
        parsed = json.loads(result)
        ai_verb = parsed["sections"]["main"][0]
        
        assert "pom" in ai_verb["ai"]["prompt"]
        assert ai_verb["ai"]["prompt"]["pom"] == pom_sections
        assert ai_verb["ai"]["post_prompt"]["text"] == "Provide a brief summary of how you helped the customer."
    
    def test_function_response_workflow(self):
        """Test function response workflow"""
        # Simulate a function returning data and actions
        response_text = "I found your account balance: $1,234.56"
        # Use the correct action format (direct SWML verbs)
        actions = [
            {"play": {"url": "say:Is there anything else I can help you with?"}},
            {"wait_for_user": {"timeout": 30}}
        ]
        
        result = SwmlRenderer.render_function_response_swml(
            response_text,
            actions=actions
        )
        
        parsed = json.loads(result)
        main_section = parsed["sections"]["main"]
        
        # Should have initial response plus actions
        assert len(main_section) == 3
        
        # Verify the sequence
        assert "play" in main_section[0]  # Initial response
        assert "play" in main_section[1]  # Follow-up question
        assert "wait_for_user" in main_section[2]  # Wait for user
    
    @patch('yaml.dump')
    def test_yaml_output_format(self, mock_yaml_dump):
        """Test YAML output format"""
        mock_yaml_dump.return_value = "version: 1.0.0\nsections:\n  main: []"
        
        result = SwmlRenderer.render_swml(
            "You are helpful",
            swaig_functions=[{
                "function": "test",
                "description": "Test function"
            }],
            format="yaml"
        )
        
        # Should be valid YAML
        assert "version: 1.0.0" in result
        assert "sections:" in result
        assert "main:" in result
        mock_yaml_dump.assert_called_once() 