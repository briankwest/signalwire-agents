"""
Unit tests for AgentBase class
"""

import pytest
import json
import uuid
import os
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List, Optional

from signalwire_agents.core.agent_base import AgentBase, EphemeralAgentConfig


class TestEphemeralAgentConfig:
    """Test EphemeralAgentConfig class"""
    
    def test_initialization(self):
        """Test EphemeralAgentConfig initialization"""
        config = EphemeralAgentConfig()
        
        assert config._hints == []
        assert config._languages == []
        assert config._pronounce == []
        assert config._params == {}
        assert config._global_data == {}
        assert config._prompt_sections == []
        assert config._raw_prompt is None
        assert config._post_prompt is None
        assert config._function_includes == []
        assert config._native_functions == []
    
    def test_add_hint(self):
        """Test adding hints"""
        config = EphemeralAgentConfig()
        
        result = config.add_hint("Test hint")
        
        assert result is config  # Should return self for chaining
        assert config._hints == ["Test hint"]
        
        # Test empty hint
        config.add_hint("")
        assert config._hints == ["Test hint"]  # Should not add empty
        
        # Test non-string hint
        config.add_hint(123)
        assert config._hints == ["Test hint"]  # Should not add non-string
    
    def test_add_hints(self):
        """Test adding multiple hints"""
        config = EphemeralAgentConfig()
        
        hints = ["Hint 1", "Hint 2", "Hint 3"]
        result = config.add_hints(hints)
        
        assert result is config
        assert config._hints == hints
        
        # Test with empty list
        config.add_hints([])
        assert config._hints == hints  # Should not change
        
        # Test with None
        config.add_hints(None)
        assert config._hints == hints  # Should not change
    
    def test_add_language(self):
        """Test adding language configuration"""
        config = EphemeralAgentConfig()
        
        result = config.add_language("English", "en", "alice", engine="neural", model="gpt-4")
        
        assert result is config
        assert len(config._languages) == 1
        
        language = config._languages[0]
        assert language["name"] == "English"
        assert language["code"] == "en"
        assert language["voice"] == "alice"
        assert language["engine"] == "neural"
        assert language["model"] == "gpt-4"
    
    def test_add_pronunciation(self):
        """Test adding pronunciation rules"""
        config = EphemeralAgentConfig()
        
        result = config.add_pronunciation("AI", "Artificial Intelligence", ignore_case=True)
        
        assert result is config
        assert len(config._pronounce) == 1
        
        rule = config._pronounce[0]
        assert rule["replace"] == "AI"
        assert rule["with"] == "Artificial Intelligence"
        assert rule["ignore_case"] is True
        
        # Test without ignore_case
        config.add_pronunciation("ML", "Machine Learning")
        rule2 = config._pronounce[1]
        assert "ignore_case" not in rule2
    
    def test_set_param(self):
        """Test setting parameters"""
        config = EphemeralAgentConfig()
        
        result = config.set_param("temperature", 0.7)
        
        assert result is config
        assert config._params["temperature"] == 0.7
        
        # Test empty key
        config.set_param("", "value")
        assert "" not in config._params
    
    def test_set_params(self):
        """Test setting multiple parameters"""
        config = EphemeralAgentConfig()
        
        params = {"temperature": 0.7, "max_tokens": 100}
        result = config.set_params(params)
        
        assert result is config
        assert config._params == params
    
    def test_set_global_data(self):
        """Test setting global data"""
        config = EphemeralAgentConfig()
        
        data = {"user_id": "123", "session": "abc"}
        result = config.set_global_data(data)
        
        assert result is config
        assert config._global_data == data
    
    def test_update_global_data(self):
        """Test updating global data"""
        config = EphemeralAgentConfig()
        config._global_data = {"existing": "value"}
        
        new_data = {"new_key": "new_value"}
        result = config.update_global_data(new_data)
        
        assert result is config
        assert config._global_data == {"existing": "value", "new_key": "new_value"}
    
    def test_set_prompt_text(self):
        """Test setting prompt text"""
        config = EphemeralAgentConfig()
        
        result = config.set_prompt_text("You are a helpful assistant")
        
        assert result is config
        assert config._raw_prompt == "You are a helpful assistant"
    
    def test_set_post_prompt(self):
        """Test setting post-prompt text"""
        config = EphemeralAgentConfig()
        
        result = config.set_post_prompt("End of conversation")
        
        assert result is config
        assert config._post_prompt == "End of conversation"
    
    def test_prompt_add_section(self):
        """Test adding prompt sections"""
        config = EphemeralAgentConfig()
        
        result = config.prompt_add_section("Instructions", "Follow these rules", ["Rule 1", "Rule 2"])
        
        assert result is config
        assert len(config._prompt_sections) == 1
        
        section = config._prompt_sections[0]
        assert section["title"] == "Instructions"
        assert section["body"] == "Follow these rules"
        assert section["bullets"] == ["Rule 1", "Rule 2"]
    
    def test_add_function_include(self):
        """Test adding function includes"""
        config = EphemeralAgentConfig()
        
        result = config.add_function_include("http://example.com", ["func1", "func2"], {"key": "value"})
        
        assert result is config
        assert len(config._function_includes) == 1
        
        include = config._function_includes[0]
        assert include["url"] == "http://example.com"
        assert include["functions"] == ["func1", "func2"]
        assert include["meta_data"] == {"key": "value"}
    
    def test_extract_config(self):
        """Test extracting configuration"""
        config = EphemeralAgentConfig()
        config.add_hint("Test hint")
        config.set_param("temperature", 0.7)
        config.set_global_data({"key": "value"})
        
        result = config.extract_config()
        
        assert "hints" in result
        assert "params" in result
        assert "global_data" in result
        assert result["hints"] == ["Test hint"]
        assert result["params"] == {"temperature": 0.7}
        assert result["global_data"] == {"key": "value"}


class TestAgentBaseInitialization:
    """Test AgentBase initialization"""
    
    def _create_mock_agent(self, **kwargs):
        """Helper to create a properly mocked agent"""
        with patch('signalwire_agents.core.agent_base.SWMLService') as mock_swml_service, \
             patch('signalwire_agents.core.agent_base.SessionManager') as mock_session_manager, \
             patch('signalwire_agents.core.agent_base.FileStateManager') as mock_state_manager, \
             patch('signalwire_agents.core.agent_base.SkillManager') as mock_skill_manager, \
             patch('signalwire_agents.core.agent_base.SchemaUtils') as mock_schema_utils:
            
            # Create mock instances
            mock_swml_instance = Mock()
            mock_swml_instance.schema_utils = Mock(schema_path=None, schema=None)
            mock_swml_instance.log = Mock()
            mock_swml_service.return_value = mock_swml_instance
            
            mock_session_manager.return_value = Mock()
            mock_state_manager.return_value = Mock()
            mock_skill_manager.return_value = Mock()
            mock_schema_utils.return_value = Mock(schema_path=None, schema=None)
            
            # Create agent with proper inheritance
            agent = AgentBase(**kwargs)
            
            # Set required attributes that would normally come from SWMLService
            agent.schema_utils = Mock(schema_path=None, schema=None)
            agent.log = Mock()
            
            return agent
    
    def test_basic_initialization(self):
        """Test basic AgentBase initialization"""
        agent = self._create_mock_agent(name="test_agent")
        
        assert agent.get_name() == "test_agent"
        assert agent.agent_id is not None
        assert agent._auto_answer is True
        assert agent._record_call is False
        assert agent._use_pom is True
        assert agent.native_functions == []
    
    def test_initialization_with_custom_params(self):
        """Test AgentBase initialization with custom parameters"""
        agent = self._create_mock_agent(
            name="custom_agent",
            route="/custom",
            host="127.0.0.1",
            port=8080,
            basic_auth=("user", "pass"),
            use_pom=False,
            enable_state_tracking=True,
            auto_answer=False,
            record_call=True,
            agent_id="custom-id",
            native_functions=["func1", "func2"]
        )
        
        assert agent.get_name() == "custom_agent"
        assert agent.agent_id == "custom-id"
        assert agent._auto_answer is False
        assert agent._record_call is True
        assert agent._use_pom is False
        assert agent.pom is None
        assert agent.native_functions == ["func1", "func2"]
    
    def test_initialization_with_pom_import_error(self):
        """Test AgentBase initialization with POM import error"""
        with patch('builtins.__import__', side_effect=ImportError("No module named 'signalwire_pom'")):
            with pytest.raises(ImportError, match="No module named 'signalwire_pom'"):
                self._create_mock_agent(name="test_agent", use_pom=True)


class TestAgentBasePromptMethods:
    """Test AgentBase prompt-related methods"""
    
    def setup_method(self):
        """Set up test fixtures"""
        with patch('signalwire_agents.core.agent_base.SWMLService') as mock_swml_service, \
             patch('signalwire_agents.core.agent_base.SessionManager'), \
             patch('signalwire_agents.core.agent_base.FileStateManager'), \
             patch('signalwire_agents.core.agent_base.SkillManager'), \
             patch('signalwire_agents.core.agent_base.SchemaUtils'):
            
            # Create mock instance
            mock_swml_instance = Mock()
            mock_swml_instance.schema_utils = Mock(schema_path=None, schema=None)
            mock_swml_instance.log = Mock()
            mock_swml_service.return_value = mock_swml_instance
            
            self.agent = AgentBase("test_agent", use_pom=False)
            self.agent.schema_utils = Mock(schema_path=None, schema=None)
            self.agent.log = Mock()
    
    def test_set_prompt_text(self):
        """Test setting prompt text"""
        result = self.agent.set_prompt_text("You are a helpful assistant")
        
        assert result is self.agent  # Should return self for chaining
        assert self.agent._raw_prompt == "You are a helpful assistant"
    
    def test_set_post_prompt(self):
        """Test setting post-prompt text"""
        result = self.agent.set_post_prompt("End of conversation")
        
        assert result is self.agent
        assert self.agent._post_prompt == "End of conversation"
    
    def test_get_prompt_with_raw_text(self):
        """Test get_prompt with raw text"""
        self.agent.set_prompt_text("Raw prompt text")
        
        result = self.agent.get_prompt()
        
        assert result == "Raw prompt text"
    
    def test_get_prompt_without_text(self):
        """Test get_prompt without any text set"""
        result = self.agent.get_prompt()
        
        assert result == "You are test_agent, a helpful AI assistant."
    
    def test_get_post_prompt(self):
        """Test get_post_prompt"""
        self.agent.set_post_prompt("Post prompt text")
        
        result = self.agent.get_post_prompt()
        
        assert result == "Post prompt text"
    
    def test_get_post_prompt_none(self):
        """Test get_post_prompt when none set"""
        result = self.agent.get_post_prompt()
        
        assert result is None


class TestAgentBaseConfigurationMethods:
    """Test AgentBase configuration methods"""
    
    def setup_method(self):
        """Set up test fixtures"""
        with patch('signalwire_agents.core.agent_base.SWMLService') as mock_swml_service, \
             patch('signalwire_agents.core.agent_base.SessionManager'), \
             patch('signalwire_agents.core.agent_base.FileStateManager'), \
             patch('signalwire_agents.core.agent_base.SkillManager'), \
             patch('signalwire_agents.core.agent_base.SchemaUtils'):
            
            # Create mock instance
            mock_swml_instance = Mock()
            mock_swml_instance.schema_utils = Mock(schema_path=None, schema=None)
            mock_swml_instance.log = Mock()
            mock_swml_service.return_value = mock_swml_instance
            
            self.agent = AgentBase("test_agent")
            self.agent.schema_utils = Mock(schema_path=None, schema=None)
            self.agent.log = Mock()
    
    def test_add_hint(self):
        """Test adding hints"""
        result = self.agent.add_hint("Test hint")
        
        assert result is self.agent
        assert "Test hint" in self.agent._hints
    
    def test_add_hints(self):
        """Test adding multiple hints"""
        hints = ["Hint 1", "Hint 2"]
        result = self.agent.add_hints(hints)
        
        assert result is self.agent
        assert all(hint in self.agent._hints for hint in hints)
    
    def test_add_language(self):
        """Test adding language configuration"""
        result = self.agent.add_language("English", "en", "alice")
        
        assert result is self.agent
        assert len(self.agent._languages) == 1
        
        language = self.agent._languages[0]
        assert language["name"] == "English"
        assert language["code"] == "en"
        assert language["voice"] == "alice"
    
    def test_add_pronunciation(self):
        """Test adding pronunciation rules"""
        result = self.agent.add_pronunciation("AI", "Artificial Intelligence")
        
        assert result is self.agent
        assert len(self.agent._pronounce) == 1
        
        rule = self.agent._pronounce[0]
        assert rule["replace"] == "AI"
        assert rule["with"] == "Artificial Intelligence"
    
    def test_set_param(self):
        """Test setting parameters"""
        result = self.agent.set_param("temperature", 0.7)
        
        assert result is self.agent
        assert self.agent._params["temperature"] == 0.7
    
    def test_set_params(self):
        """Test setting multiple parameters"""
        params = {"temperature": 0.7, "max_tokens": 100}
        result = self.agent.set_params(params)
        
        assert result is self.agent
        assert self.agent._params == params
    
    def test_set_global_data(self):
        """Test setting global data"""
        data = {"user_id": "123"}
        result = self.agent.set_global_data(data)
        
        assert result is self.agent
        assert self.agent._global_data == data
    
    def test_update_global_data(self):
        """Test updating global data"""
        self.agent._global_data = {"existing": "value"}
        new_data = {"new_key": "new_value"}
        
        result = self.agent.update_global_data(new_data)
        
        assert result is self.agent
        assert self.agent._global_data == {"existing": "value", "new_key": "new_value"}
    
    def test_set_native_functions(self):
        """Test setting native functions"""
        functions = ["func1", "func2"]
        result = self.agent.set_native_functions(functions)
        
        assert result is self.agent
        assert self.agent.native_functions == functions
    
    def test_add_function_include(self):
        """Test adding function includes"""
        result = self.agent.add_function_include("http://example.com", ["func1"])
        
        assert result is self.agent
        assert len(self.agent._function_includes) == 1
        
        include = self.agent._function_includes[0]
        assert include["url"] == "http://example.com"
        assert include["functions"] == ["func1"]


class TestAgentBaseToolMethods:
    """Test AgentBase tool-related methods"""
    
    def setup_method(self):
        """Set up test fixtures"""
        with patch('signalwire_agents.core.agent_base.SWMLService') as mock_swml_service, \
             patch('signalwire_agents.core.agent_base.SessionManager'), \
             patch('signalwire_agents.core.agent_base.FileStateManager'), \
             patch('signalwire_agents.core.agent_base.SkillManager'), \
             patch('signalwire_agents.core.agent_base.SchemaUtils'), \
             patch('signalwire_agents.core.agent_base.SWAIGFunction') as mock_swaig_function:
            
            # Create mock instance
            mock_swml_instance = Mock()
            mock_swml_instance.schema_utils = Mock(schema_path=None, schema=None)
            mock_swml_instance.log = Mock()
            mock_swml_service.return_value = mock_swml_instance
            
            # Mock SWAIGFunction
            mock_function_instance = Mock()
            mock_function_instance.name = "test_tool"
            mock_function_instance.description = "Test description"
            mock_swaig_function.return_value = mock_function_instance
            
            self.agent = AgentBase("test_agent")
            self.agent.schema_utils = Mock(schema_path=None, schema=None)
            self.agent.log = Mock()
    
    def test_define_tool(self):
        """Test defining a tool"""
        def test_handler(arg1: str, arg2: int) -> str:
            return f"{arg1}_{arg2}"
        
        parameters = {
            "type": "object",
            "properties": {
                "arg1": {"type": "string"},
                "arg2": {"type": "integer"}
            }
        }
        
        result = self.agent.define_tool("test_tool", "Test description", parameters, test_handler)
        
        assert result is self.agent
        assert "test_tool" in self.agent._swaig_functions
    
    def test_register_swaig_function(self):
        """Test registering SWAIG function from dictionary"""
        function_dict = {
            "function": "test_func",
            "description": "Test function",
            "parameters": {"type": "object"},
            "handler": lambda: "test"
        }
        
        with patch('signalwire_agents.core.agent_base.SWAIGFunction') as mock_swaig:
            mock_instance = Mock()
            mock_instance.name = "test_func"
            mock_swaig.return_value = mock_instance
            
            result = self.agent.register_swaig_function(function_dict)
            
            assert result is self.agent
            assert "test_func" in self.agent._swaig_functions
    
    def test_define_tools(self):
        """Test define_tools method"""
        # Add a tool first
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        self.agent._swaig_functions["test_tool"] = mock_tool
        
        tools = self.agent.define_tools()
        
        assert isinstance(tools, list)
        assert len(tools) == 1
        assert tools[0].name == "test_tool"
    
    def test_on_function_call(self):
        """Test on_function_call method"""
        result = self.agent.on_function_call("test_func", {"arg": "value"})
        
        assert result == {"response": "Function 'test_func' not found"}
    
    def test_on_summary(self):
        """Test on_summary method"""
        # This is a hook method that should be overridden by subclasses
        # Should not raise any exceptions
        self.agent.on_summary({"summary": "test"})


class TestAgentBaseAuthMethods:
    """Test AgentBase authentication methods"""
    
    def setup_method(self):
        """Set up test fixtures"""
        with patch('signalwire_agents.core.agent_base.SWMLService') as mock_swml_service, \
             patch('signalwire_agents.core.agent_base.SessionManager'), \
             patch('signalwire_agents.core.agent_base.FileStateManager'), \
             patch('signalwire_agents.core.agent_base.SkillManager'), \
             patch('signalwire_agents.core.agent_base.SchemaUtils'):
            
            # Create mock instance
            mock_swml_instance = Mock()
            mock_swml_instance.schema_utils = Mock(schema_path=None, schema=None)
            mock_swml_instance.log = Mock()
            mock_swml_service.return_value = mock_swml_instance
            
            self.agent = AgentBase("test_agent", basic_auth=("user", "pass"))
            self.agent.schema_utils = Mock(schema_path=None, schema=None)
            self.agent.log = Mock()
    
    def test_validate_basic_auth_success(self):
        """Test successful basic auth validation"""
        result = self.agent.validate_basic_auth("user", "pass")
        
        assert result is True
    
    def test_validate_basic_auth_failure(self):
        """Test failed basic auth validation"""
        result = self.agent.validate_basic_auth("wrong", "creds")
        
        assert result is False
    
    def test_validate_basic_auth_no_auth_configured(self):
        """Test basic auth validation when no auth is configured"""
        with patch('signalwire_agents.core.agent_base.SWMLService') as mock_swml_service, \
             patch('signalwire_agents.core.agent_base.SessionManager'), \
             patch('signalwire_agents.core.agent_base.FileStateManager'), \
             patch('signalwire_agents.core.agent_base.SkillManager'), \
             patch('signalwire_agents.core.agent_base.SchemaUtils'):
            
            # Create mock instance
            mock_swml_instance = Mock()
            mock_swml_instance.schema_utils = Mock(schema_path=None, schema=None)
            mock_swml_instance.log = Mock()
            mock_swml_service.return_value = mock_swml_instance
            
            agent = AgentBase("test_agent")  # No basic_auth
            agent.schema_utils = Mock(schema_path=None, schema=None)
            agent.log = Mock()
            agent._basic_auth = (None, None)  # Explicitly set no auth
        
        result = agent.validate_basic_auth("any", "creds")
        
        assert result is False
    
    def test_get_basic_auth_credentials(self):
        """Test getting basic auth credentials"""
        username, password = self.agent.get_basic_auth_credentials()
        
        assert username == "user"
        assert password == "pass"
    
    def test_get_basic_auth_credentials_with_source(self):
        """Test getting basic auth credentials with source"""
        username, password, source = self.agent.get_basic_auth_credentials(include_source=True)
        
        assert username == "user"
        assert password == "pass"
        assert source == "provided"


class TestAgentBaseURLMethods:
    """Test AgentBase URL-related methods"""
    
    def setup_method(self):
        """Set up test fixtures"""
        with patch('signalwire_agents.core.agent_base.SWMLService') as mock_swml_service, \
             patch('signalwire_agents.core.agent_base.SessionManager'), \
             patch('signalwire_agents.core.agent_base.FileStateManager'), \
             patch('signalwire_agents.core.agent_base.SkillManager'), \
             patch('signalwire_agents.core.agent_base.SchemaUtils'):
            
            # Create mock instance
            mock_swml_instance = Mock()
            mock_swml_instance.schema_utils = Mock(schema_path=None, schema=None)
            mock_swml_instance.log = Mock()
            mock_swml_service.return_value = mock_swml_instance
            
            self.agent = AgentBase("test_agent", host="localhost", port=3000, route="/test")
            self.agent.schema_utils = Mock(schema_path=None, schema=None)
            self.agent.log = Mock()
    
    def test_get_full_url_basic(self):
        """Test getting full URL without auth"""
        url = self.agent.get_full_url()
        
        assert url == "http://localhost:3000/test"
    
    def test_get_full_url_with_auth(self):
        """Test getting full URL with auth"""
        with patch('signalwire_agents.core.agent_base.SWMLService') as mock_swml_service, \
             patch('signalwire_agents.core.agent_base.SessionManager'), \
             patch('signalwire_agents.core.agent_base.FileStateManager'), \
             patch('signalwire_agents.core.agent_base.SkillManager'), \
             patch('signalwire_agents.core.agent_base.SchemaUtils'):
            
            # Create mock instance
            mock_swml_instance = Mock()
            mock_swml_instance.schema_utils = Mock(schema_path=None, schema=None)
            mock_swml_instance.log = Mock()
            mock_swml_service.return_value = mock_swml_instance
            
            agent = AgentBase("test_agent", host="localhost", port=3000, route="/test", 
                            basic_auth=("user", "pass"))
            agent.schema_utils = Mock(schema_path=None, schema=None)
            agent.log = Mock()
        
        url = agent.get_full_url(include_auth=True)
        
        assert url == "http://user:pass@localhost:3000/test"
    
    def test_set_web_hook_url(self):
        """Test setting webhook URL"""
        result = self.agent.set_web_hook_url("http://example.com/webhook")
        
        assert result is self.agent
        assert self.agent._web_hook_url_override == "http://example.com/webhook"
    
    def test_set_post_prompt_url(self):
        """Test setting post-prompt URL"""
        result = self.agent.set_post_prompt_url("http://example.com/post")
        
        assert result is self.agent
        assert self.agent._post_prompt_url_override == "http://example.com/post"
    
    def test_manual_set_proxy_url(self):
        """Test manually setting proxy URL"""
        result = self.agent.manual_set_proxy_url("http://proxy.example.com")
        
        assert result is self.agent
        assert self.agent._proxy_url_base == "http://proxy.example.com"


class TestAgentBaseSkillMethods:
    """Test AgentBase skill-related methods"""
    
    def setup_method(self):
        """Set up test fixtures"""
        with patch('signalwire_agents.core.agent_base.SWMLService') as mock_swml_service, \
             patch('signalwire_agents.core.agent_base.SessionManager'), \
             patch('signalwire_agents.core.agent_base.FileStateManager'), \
             patch('signalwire_agents.core.agent_base.SkillManager') as mock_skill_manager, \
             patch('signalwire_agents.core.agent_base.SchemaUtils'):
            
            # Create mock instance
            mock_swml_instance = Mock()
            mock_swml_instance.schema_utils = Mock(schema_path=None, schema=None)
            mock_swml_instance.log = Mock()
            mock_swml_service.return_value = mock_swml_instance
            
            self.mock_skill_manager_instance = Mock()
            mock_skill_manager.return_value = self.mock_skill_manager_instance
            
            self.agent = AgentBase("test_agent")
            self.agent.schema_utils = Mock(schema_path=None, schema=None)
            self.agent.log = Mock()
    
    def test_add_skill(self):
        """Test adding a skill"""
        self.mock_skill_manager_instance.load_skill.return_value = (True, None)
        
        result = self.agent.add_skill("test_skill", {"param": "value"})
        
        assert result is self.agent
        self.mock_skill_manager_instance.load_skill.assert_called_once_with("test_skill", params={"param": "value"})
    
    def test_remove_skill(self):
        """Test removing a skill"""
        result = self.agent.remove_skill("test_skill")
        
        assert result is self.agent
        self.mock_skill_manager_instance.unload_skill.assert_called_once_with("test_skill")
    
    def test_list_skills(self):
        """Test listing skills"""
        self.mock_skill_manager_instance.list_loaded_skills.return_value = ["skill1", "skill2"]
        
        result = self.agent.list_skills()
        
        assert result == ["skill1", "skill2"]
        self.mock_skill_manager_instance.list_loaded_skills.assert_called_once()
    
    def test_has_skill(self):
        """Test checking if skill exists"""
        self.mock_skill_manager_instance.has_skill.return_value = True
        
        result = self.agent.has_skill("test_skill")
        
        assert result is True
        self.mock_skill_manager_instance.has_skill.assert_called_once_with("test_skill")


class TestAgentBaseTokenMethods:
    """Test AgentBase token-related methods"""
    
    def setup_method(self):
        """Set up test fixtures"""
        with patch('signalwire_agents.core.agent_base.SWMLService') as mock_swml_service, \
             patch('signalwire_agents.core.agent_base.SessionManager') as mock_session_manager, \
             patch('signalwire_agents.core.agent_base.FileStateManager'), \
             patch('signalwire_agents.core.agent_base.SkillManager'), \
             patch('signalwire_agents.core.agent_base.SchemaUtils'):
            
            # Create mock instance
            mock_swml_instance = Mock()
            mock_swml_instance.schema_utils = Mock(schema_path=None, schema=None)
            mock_swml_instance.log = Mock()
            mock_swml_service.return_value = mock_swml_instance
            
            self.mock_session_manager_instance = Mock()
            mock_session_manager.return_value = self.mock_session_manager_instance
            
            self.agent = AgentBase("test_agent")
            self.agent.schema_utils = Mock(schema_path=None, schema=None)
            self.agent.log = Mock()
    
    def test_create_tool_token(self):
        """Test creating tool token"""
        self.mock_session_manager_instance.create_tool_token.return_value = "test_token"
        
        token = self.agent._create_tool_token("test_tool", "call_123")
        
        assert token == "test_token"
        self.mock_session_manager_instance.create_tool_token.assert_called_once_with("test_tool", "call_123")
    
    def test_validate_tool_token(self):
        """Test validating tool token"""
        # Add a mock function to the agent
        mock_func = Mock()
        mock_func.secure = True
        self.agent._swaig_functions["test_tool"] = mock_func
        
        self.mock_session_manager_instance.validate_tool_token.return_value = True
        
        result = self.agent.validate_tool_token("test_tool", "test_token", "call_123")
        
        assert result is True
        self.mock_session_manager_instance.validate_tool_token.assert_called_once_with("test_tool", "test_token", "call_123")


class TestAgentBaseMiscMethods:
    """Test miscellaneous AgentBase methods"""
    
    def setup_method(self):
        """Set up test fixtures"""
        with patch('signalwire_agents.core.agent_base.SWMLService') as mock_swml_service, \
             patch('signalwire_agents.core.agent_base.SessionManager'), \
             patch('signalwire_agents.core.agent_base.FileStateManager'), \
             patch('signalwire_agents.core.agent_base.SkillManager'), \
             patch('signalwire_agents.core.agent_base.SchemaUtils'):
            
            # Create mock instance
            mock_swml_instance = Mock()
            mock_swml_instance.schema_utils = Mock(schema_path=None, schema=None)
            mock_swml_instance.log = Mock()
            mock_swml_service.return_value = mock_swml_instance
            
            self.agent = AgentBase("test_agent")
            self.agent.schema_utils = Mock(schema_path=None, schema=None)
            self.agent.log = Mock()
    
    def test_get_name(self):
        """Test getting agent name"""
        name = self.agent.get_name()
        
        assert name == "test_agent"
    
    def test_set_dynamic_config_callback(self):
        """Test setting dynamic config callback"""
        def callback(request_data, call_data, meta_data, config):
            pass
        
        result = self.agent.set_dynamic_config_callback(callback)
        
        assert result is self.agent
        assert self.agent._dynamic_config_callback == callback
    
    def test_on_request(self):
        """Test on_request method"""
        # This is a hook method that should be overridden by subclasses
        result = self.agent.on_request({"test": "data"})
        
        # Default implementation should return None
        assert result is None
    
    def test_on_swml_request(self):
        """Test on_swml_request method"""
        # This is a hook method that should be overridden by subclasses
        result = self.agent.on_swml_request({"test": "data"})
        
        # Default implementation should return None
        assert result is None


class TestAgentBaseDeclarativePrompts:
    """Test AgentBase declarative prompt sections"""
    
    def test_process_prompt_sections_dict(self):
        """Test processing declarative prompt sections from dict"""
        class TestAgent(AgentBase):
            PROMPT_SECTIONS = {
                "Instructions": "Follow these rules",
                "Rules": ["Rule 1", "Rule 2"],
                "Complex": {
                    "body": "Complex section",
                    "bullets": ["Bullet 1", "Bullet 2"],
                    "numbered": True
                }
            }
        
        with patch('signalwire_agents.core.agent_base.SWMLService') as mock_swml_service, \
             patch('signalwire_agents.core.agent_base.SessionManager'), \
             patch('signalwire_agents.core.agent_base.FileStateManager'), \
             patch('signalwire_agents.core.agent_base.SkillManager'), \
             patch('signalwire_agents.core.agent_base.SchemaUtils'), \
             patch.object(TestAgent, 'prompt_add_section') as mock_add_section:
            
            # Create mock instance
            mock_swml_instance = Mock()
            mock_swml_instance.schema_utils = Mock(schema_path=None, schema=None)
            mock_swml_instance.log = Mock()
            mock_swml_service.return_value = mock_swml_instance
            
            agent = TestAgent("test_agent")
            agent.schema_utils = Mock(schema_path=None, schema=None)
            agent.log = Mock()
            
            # Should have called prompt_add_section for each section
            assert mock_add_section.call_count == 3
    
    def test_process_prompt_sections_no_pom(self):
        """Test processing prompt sections when POM is disabled"""
        class TestAgent(AgentBase):
            PROMPT_SECTIONS = {"Test": "Content"}
        
        with patch('signalwire_agents.core.agent_base.SWMLService') as mock_swml_service, \
             patch('signalwire_agents.core.agent_base.SessionManager'), \
             patch('signalwire_agents.core.agent_base.FileStateManager'), \
             patch('signalwire_agents.core.agent_base.SkillManager'), \
             patch('signalwire_agents.core.agent_base.SchemaUtils'), \
             patch.object(TestAgent, 'prompt_add_section') as mock_add_section:
            
            # Create mock instance
            mock_swml_instance = Mock()
            mock_swml_instance.schema_utils = Mock(schema_path=None, schema=None)
            mock_swml_instance.log = Mock()
            mock_swml_service.return_value = mock_swml_instance
            
            agent = TestAgent("test_agent", use_pom=False)
            agent.schema_utils = Mock(schema_path=None, schema=None)
            agent.log = Mock()
            
            # Should not call prompt_add_section when POM is disabled
            mock_add_section.assert_not_called() 