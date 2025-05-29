"""
Unit tests for skills registry module
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any, Optional

from signalwire_agents.skills.registry import SkillRegistry, skill_registry
from signalwire_agents.core.skill_base import SkillBase


class MockSkill(SkillBase):
    """Mock skill for testing"""
    SKILL_NAME = "mock_skill"
    SKILL_DESCRIPTION = "A mock skill for testing"
    SKILL_VERSION = "1.0.0"
    REQUIRED_PACKAGES = ["requests"]
    REQUIRED_ENV_VARS = ["API_KEY"]
    SUPPORTS_MULTIPLE_INSTANCES = True
    
    def setup(self):
        pass
    
    def register_tools(self):
        pass


class AnotherMockSkill(SkillBase):
    """Another mock skill for testing"""
    SKILL_NAME = "another_mock_skill"
    SKILL_DESCRIPTION = "Another mock skill"
    SKILL_VERSION = "2.0.0"
    REQUIRED_PACKAGES = []
    REQUIRED_ENV_VARS = []
    SUPPORTS_MULTIPLE_INSTANCES = False
    
    def setup(self):
        pass
    
    def register_tools(self):
        pass


class InvalidSkill(SkillBase):
    """Invalid skill without SKILL_NAME"""
    SKILL_NAME = None
    
    def setup(self):
        pass
    
    def register_tools(self):
        pass


class TestSkillRegistry:
    """Test SkillRegistry functionality"""
    
    def test_basic_initialization(self):
        """Test basic SkillRegistry initialization"""
        registry = SkillRegistry()
        
        assert registry._skills == {}
        assert registry._discovered is False
        assert registry.logger is not None
    
    def test_register_skill_basic(self):
        """Test basic skill registration"""
        registry = SkillRegistry()
        
        registry.register_skill(MockSkill)
        
        assert "mock_skill" in registry._skills
        assert registry._skills["mock_skill"] == MockSkill
    
    def test_register_skill_duplicate(self):
        """Test registering duplicate skill"""
        registry = SkillRegistry()
        
        registry.register_skill(MockSkill)
        
        # Register the same skill again
        with patch.object(registry.logger, 'warning') as mock_warning:
            registry.register_skill(MockSkill)
            mock_warning.assert_called_once_with("Skill 'mock_skill' already registered")
        
        # Should still only have one instance
        assert len(registry._skills) == 1
    
    def test_register_multiple_skills(self):
        """Test registering multiple skills"""
        registry = SkillRegistry()
        
        registry.register_skill(MockSkill)
        registry.register_skill(AnotherMockSkill)
        
        assert len(registry._skills) == 2
        assert "mock_skill" in registry._skills
        assert "another_mock_skill" in registry._skills
    
    def test_get_skill_class_existing(self):
        """Test getting existing skill class"""
        registry = SkillRegistry()
        registry.register_skill(MockSkill)
        
        # Mock discovery to prevent loading real skills
        with patch.object(registry, 'discover_skills'):
            skill_class = registry.get_skill_class("mock_skill")
        
        assert skill_class == MockSkill
    
    def test_get_skill_class_nonexistent(self):
        """Test getting nonexistent skill class"""
        registry = SkillRegistry()
        
        # Mock discovery to prevent loading real skills
        with patch.object(registry, 'discover_skills'):
            skill_class = registry.get_skill_class("nonexistent_skill")
        
        assert skill_class is None
    
    @patch.object(SkillRegistry, 'discover_skills')
    def test_get_skill_class_triggers_discovery(self, mock_discover):
        """Test that get_skill_class triggers skill discovery"""
        registry = SkillRegistry()
        
        registry.get_skill_class("some_skill")
        
        mock_discover.assert_called_once()
    
    def test_list_skills_empty(self):
        """Test listing skills when registry is empty"""
        registry = SkillRegistry()
        
        # Mock discovery to prevent loading real skills
        with patch.object(registry, 'discover_skills'):
            skills = registry.list_skills()
        
        assert skills == []
    
    def test_list_skills_with_skills(self):
        """Test listing skills with registered skills"""
        registry = SkillRegistry()
        registry.register_skill(MockSkill)
        registry.register_skill(AnotherMockSkill)
        
        # Mock discovery to prevent loading real skills
        with patch.object(registry, 'discover_skills'):
            skills = registry.list_skills()
        
        assert len(skills) == 2
        
        # Check first skill
        mock_skill_info = next(s for s in skills if s["name"] == "mock_skill")
        assert mock_skill_info["description"] == "A mock skill for testing"
        assert mock_skill_info["version"] == "1.0.0"
        assert mock_skill_info["required_packages"] == ["requests"]
        assert mock_skill_info["required_env_vars"] == ["API_KEY"]
        assert mock_skill_info["supports_multiple_instances"] is True
        
        # Check second skill
        another_skill_info = next(s for s in skills if s["name"] == "another_mock_skill")
        assert another_skill_info["description"] == "Another mock skill"
        assert another_skill_info["version"] == "2.0.0"
        assert another_skill_info["required_packages"] == []
        assert another_skill_info["required_env_vars"] == []
        assert another_skill_info["supports_multiple_instances"] is False
    
    @patch.object(SkillRegistry, 'discover_skills')
    def test_list_skills_triggers_discovery(self, mock_discover):
        """Test that list_skills triggers skill discovery"""
        registry = SkillRegistry()
        
        registry.list_skills()
        
        mock_discover.assert_called_once()


class TestSkillDiscovery:
    """Test skill discovery functionality"""
    
    def test_discover_skills_idempotent(self):
        """Test that discover_skills is idempotent"""
        registry = SkillRegistry()
        
        with patch.object(registry, '_load_skill_from_directory') as mock_load:
            registry.discover_skills()
            registry.discover_skills()  # Call again
            
            # Should only be called once due to _discovered flag
            assert mock_load.call_count > 0  # Called at least once from first call
            
            # Reset and call again to verify idempotency
            mock_load.reset_mock()
            registry.discover_skills()
            mock_load.assert_not_called()
    
    @patch('signalwire_agents.skills.registry.Path')
    def test_discover_skills_scans_directory(self, mock_path):
        """Test that discover_skills scans the skills directory"""
        registry = SkillRegistry()
        
        # Mock the skills directory structure
        mock_skills_dir = Mock()
        mock_path.return_value.parent = mock_skills_dir
        
        mock_skill_dir1 = Mock()
        mock_skill_dir1.is_dir.return_value = True
        mock_skill_dir1.name = "test_skill"
        
        mock_skill_dir2 = Mock()
        mock_skill_dir2.is_dir.return_value = True
        mock_skill_dir2.name = "__pycache__"  # Should be skipped
        
        mock_file = Mock()
        mock_file.is_dir.return_value = False
        
        mock_skills_dir.iterdir.return_value = [mock_skill_dir1, mock_skill_dir2, mock_file]
        
        with patch.object(registry, '_load_skill_from_directory') as mock_load:
            registry.discover_skills()
            
            # Should only load from test_skill directory (not __pycache__ or files)
            mock_load.assert_called_once_with(mock_skill_dir1)
    
    @patch('sys.argv', ['test', '--raw'])
    def test_discover_skills_raw_mode_suppresses_logging(self):
        """Test that raw mode suppresses logging"""
        registry = SkillRegistry()
        
        with patch.object(registry.logger, 'info') as mock_info:
            with patch.object(registry, '_load_skill_from_directory'):
                registry.discover_skills()
                
                # Should not log in raw mode
                mock_info.assert_not_called()
    
    @patch('sys.argv', ['test'])
    def test_discover_skills_normal_mode_logs(self):
        """Test that normal mode logs discovery"""
        registry = SkillRegistry()
        
        with patch.object(registry.logger, 'info') as mock_info:
            with patch.object(registry, '_load_skill_from_directory'):
                registry.discover_skills()
                
                # Should log in normal mode
                mock_info.assert_called_once()


class TestSkillLoading:
    """Test skill loading functionality"""
    
    def test_load_skill_from_directory_no_skill_file(self):
        """Test loading from directory without skill.py"""
        registry = SkillRegistry()
        
        mock_dir = Mock()
        mock_skill_file = Mock()
        mock_skill_file.exists.return_value = False
        mock_dir.__truediv__ = Mock(return_value=mock_skill_file)
        
        # Should return early without error
        registry._load_skill_from_directory(mock_dir)
        
        # No skills should be registered
        assert len(registry._skills) == 0
    
    @patch('importlib.util.spec_from_file_location')
    @patch('importlib.util.module_from_spec')
    @patch('inspect.getmembers')
    def test_load_skill_from_directory_success(self, mock_getmembers, mock_module_from_spec, mock_spec_from_file):
        """Test successful skill loading"""
        registry = SkillRegistry()
        
        # Mock directory and file
        mock_dir = Mock()
        mock_dir.name = "test_skill"
        mock_skill_file = Mock()
        mock_skill_file.exists.return_value = True
        mock_dir.__truediv__ = Mock(return_value=mock_skill_file)
        
        # Mock importlib components
        mock_spec = Mock()
        mock_loader = Mock()
        mock_spec.loader = mock_loader
        mock_spec_from_file.return_value = mock_spec
        
        mock_module = Mock()
        mock_module_from_spec.return_value = mock_module
        
        # Mock inspect.getmembers to return our mock skill
        mock_getmembers.return_value = [
            ("MockSkill", MockSkill),
            ("SomeOtherClass", str),  # Should be ignored
            ("InvalidSkill", InvalidSkill),  # Should be ignored (SKILL_NAME is None)
        ]
        
        with patch.object(registry, 'register_skill') as mock_register:
            registry._load_skill_from_directory(mock_dir)
            
            # Should only register the valid skill
            mock_register.assert_called_once_with(MockSkill)
    
    @patch('importlib.util.spec_from_file_location')
    def test_load_skill_from_directory_import_error(self, mock_spec_from_file):
        """Test skill loading with import error"""
        registry = SkillRegistry()
        
        # Mock directory and file
        mock_dir = Mock()
        mock_dir.name = "test_skill"
        mock_skill_file = Mock()
        mock_skill_file.exists.return_value = True
        mock_dir.__truediv__ = Mock(return_value=mock_skill_file)
        
        # Mock import error
        mock_spec_from_file.side_effect = ImportError("Module not found")
        
        with patch.object(registry.logger, 'error') as mock_error:
            registry._load_skill_from_directory(mock_dir)
            
            # Should log the error
            mock_error.assert_called_once()
            assert "Failed to load skill" in mock_error.call_args[0][0]
    
    @patch('importlib.util.spec_from_file_location')
    @patch('importlib.util.module_from_spec')
    @patch('inspect.getmembers')
    def test_load_skill_from_directory_execution_error(self, mock_getmembers, mock_module_from_spec, mock_spec_from_file):
        """Test skill loading with module execution error"""
        registry = SkillRegistry()
        
        # Mock directory and file
        mock_dir = Mock()
        mock_dir.name = "test_skill"
        mock_skill_file = Mock()
        mock_skill_file.exists.return_value = True
        mock_dir.__truediv__ = Mock(return_value=mock_skill_file)
        
        # Mock importlib components
        mock_spec = Mock()
        mock_loader = Mock()
        mock_loader.exec_module.side_effect = RuntimeError("Execution failed")
        mock_spec.loader = mock_loader
        mock_spec_from_file.return_value = mock_spec
        
        mock_module = Mock()
        mock_module_from_spec.return_value = mock_module
        
        with patch.object(registry.logger, 'error') as mock_error:
            registry._load_skill_from_directory(mock_dir)
            
            # Should log the error
            mock_error.assert_called_once()
            assert "Failed to load skill" in mock_error.call_args[0][0]


class TestGlobalRegistry:
    """Test global registry instance"""
    
    def test_global_registry_exists(self):
        """Test that global registry instance exists"""
        assert skill_registry is not None
        assert isinstance(skill_registry, SkillRegistry)
    
    def test_global_registry_singleton_behavior(self):
        """Test that global registry behaves like a singleton"""
        # Import again to get the same instance
        from signalwire_agents.skills.registry import skill_registry as registry2
        
        assert skill_registry is registry2


class TestSkillRegistryIntegration:
    """Test integration scenarios"""
    
    def test_complete_skill_workflow(self):
        """Test complete skill registration and retrieval workflow"""
        registry = SkillRegistry()
        
        # Register skills
        registry.register_skill(MockSkill)
        registry.register_skill(AnotherMockSkill)
        
        # Mock discovery to prevent loading real skills
        with patch.object(registry, 'discover_skills'):
            # List all skills
            skills = registry.list_skills()
            assert len(skills) == 2
            
            # Get specific skills
            mock_skill = registry.get_skill_class("mock_skill")
            assert mock_skill == MockSkill
            
            another_skill = registry.get_skill_class("another_mock_skill")
            assert another_skill == AnotherMockSkill
            
            # Try to get nonexistent skill
            nonexistent = registry.get_skill_class("nonexistent")
            assert nonexistent is None
    
    def test_skill_metadata_completeness(self):
        """Test that skill metadata is complete and correct"""
        registry = SkillRegistry()
        registry.register_skill(MockSkill)
        
        # Mock discovery to prevent loading real skills
        with patch.object(registry, 'discover_skills'):
            skills = registry.list_skills()
            skill_info = skills[0]
            
            # Verify all expected fields are present
            expected_fields = [
                "name", "description", "version", 
                "required_packages", "required_env_vars", 
                "supports_multiple_instances"
            ]
            
            for field in expected_fields:
                assert field in skill_info
            
            # Verify field values
            assert skill_info["name"] == "mock_skill"
            assert skill_info["description"] == "A mock skill for testing"
            assert skill_info["version"] == "1.0.0"
            assert skill_info["required_packages"] == ["requests"]
            assert skill_info["required_env_vars"] == ["API_KEY"]
            assert skill_info["supports_multiple_instances"] is True
    
    def test_registry_state_isolation(self):
        """Test that different registry instances are isolated"""
        registry1 = SkillRegistry()
        registry2 = SkillRegistry()
        
        registry1.register_skill(MockSkill)
        
        # registry2 should not have the skill
        assert len(registry1._skills) == 1
        assert len(registry2._skills) == 0
        
        # But both should be able to register skills independently
        registry2.register_skill(AnotherMockSkill)
        
        assert "mock_skill" in registry1._skills
        assert "mock_skill" not in registry2._skills
        assert "another_mock_skill" not in registry1._skills
        assert "another_mock_skill" in registry2._skills
    
    def test_error_recovery(self):
        """Test that registry can recover from errors"""
        registry = SkillRegistry()
        
        # Register a valid skill
        registry.register_skill(MockSkill)
        
        # Try to load from a bad directory (should not affect existing skills)
        mock_bad_dir = Mock()
        mock_bad_dir.name = "bad_skill"
        mock_skill_file = Mock()
        mock_skill_file.exists.return_value = True
        mock_bad_dir.__truediv__ = Mock(return_value=mock_skill_file)
        
        with patch('importlib.util.spec_from_file_location', side_effect=Exception("Bad import")):
            with patch.object(registry.logger, 'error'):
                registry._load_skill_from_directory(mock_bad_dir)
        
        # Original skill should still be there
        assert "mock_skill" in registry._skills
        
        # Mock discovery to prevent loading real skills
        with patch.object(registry, 'discover_skills'):
            assert registry.get_skill_class("mock_skill") == MockSkill
        
        # Should still be able to register new skills
        registry.register_skill(AnotherMockSkill)
        assert len(registry._skills) == 2 