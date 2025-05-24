"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

from typing import Dict, List, Type, Any, Optional
import logging
from signalwire_agents.core.skill_base import SkillBase

class SkillManager:
    """Manages loading and lifecycle of agent skills"""
    
    def __init__(self, agent):
        self.agent = agent
        self.loaded_skills: Dict[str, SkillBase] = {}
        self.logger = logging.getLogger("skill_manager")
        
    def load_skill(self, skill_name: str, skill_class: Type[SkillBase] = None, params: Optional[Dict[str, Any]] = None) -> tuple[bool, str]:
        """
        Load and setup a skill by name
        
        Args:
            skill_name: Name of the skill to load
            skill_class: Optional skill class (if not provided, will try to find it)
            params: Optional parameters to pass to the skill
            
        Returns:
            tuple: (success, error_message) - error_message is empty string if successful
        """
        if skill_name in self.loaded_skills:
            self.logger.warning(f"Skill '{skill_name}' is already loaded")
            return True, ""
            
        # Get skill class from registry if not provided
        if skill_class is None:
            try:
                from signalwire_agents.skills.registry import skill_registry
                skill_class = skill_registry.get_skill_class(skill_name)
                if skill_class is None:
                    error_msg = f"Skill '{skill_name}' not found in registry"
                    self.logger.error(error_msg)
                    return False, error_msg
            except ImportError:
                error_msg = f"Skills registry not available. Cannot load skill '{skill_name}'"
                self.logger.error(error_msg)
                return False, error_msg
        
        try:
            # Create skill instance with parameters
            skill_instance = skill_class(self.agent, params)
            
            # Validate environment variables with specific error details
            import os
            missing_env_vars = [var for var in skill_instance.REQUIRED_ENV_VARS if not os.getenv(var)]
            if missing_env_vars:
                error_msg = f"Missing required environment variables: {missing_env_vars}"
                self.logger.error(error_msg)
                return False, error_msg
                
            # Validate packages with specific error details  
            import importlib
            missing_packages = []
            for package in skill_instance.REQUIRED_PACKAGES:
                try:
                    importlib.import_module(package)
                except ImportError:
                    missing_packages.append(package)
            if missing_packages:
                error_msg = f"Missing required packages: {missing_packages}"
                self.logger.error(error_msg)
                return False, error_msg
                
            # Setup the skill
            if not skill_instance.setup():
                error_msg = f"Failed to setup skill '{skill_name}'"
                self.logger.error(error_msg)
                return False, error_msg
                
            # Register tools with agent
            skill_instance.register_tools()
            
            # Add hints and global data to agent
            hints = skill_instance.get_hints()
            if hints:
                self.agent.add_hints(hints)
                
            global_data = skill_instance.get_global_data()
            if global_data:
                self.agent.update_global_data(global_data)
                
            # Add prompt sections
            prompt_sections = skill_instance.get_prompt_sections()
            for section in prompt_sections:
                self.agent.prompt_add_section(**section)
            
            # Store loaded skill
            self.loaded_skills[skill_name] = skill_instance
            self.logger.info(f"Successfully loaded skill '{skill_name}'")
            return True, ""
            
        except Exception as e:
            error_msg = f"Error loading skill '{skill_name}': {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def unload_skill(self, skill_name: str) -> bool:
        """Unload a skill and cleanup"""
        if skill_name not in self.loaded_skills:
            self.logger.warning(f"Skill '{skill_name}' is not loaded")
            return False
            
        try:
            skill_instance = self.loaded_skills[skill_name]
            skill_instance.cleanup()
            del self.loaded_skills[skill_name]
            self.logger.info(f"Successfully unloaded skill '{skill_name}'")
            return True
        except Exception as e:
            self.logger.error(f"Error unloading skill '{skill_name}': {e}")
            return False
    
    def list_loaded_skills(self) -> List[str]:
        """List names of currently loaded skills"""
        return list(self.loaded_skills.keys())
    
    def has_skill(self, skill_name: str) -> bool:
        """Check if skill is currently loaded"""
        return skill_name in self.loaded_skills
    
    def get_skill(self, skill_name: str) -> Optional[SkillBase]:
        """Get a loaded skill instance by name"""
        return self.loaded_skills.get(skill_name) 