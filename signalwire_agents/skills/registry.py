"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

import os
import importlib
import importlib.util
import inspect
import sys
from typing import Dict, List, Type, Optional
from pathlib import Path

from signalwire_agents.core.skill_base import SkillBase
from signalwire_agents.core.logging_config import get_logger

class SkillRegistry:
    """Global registry for on-demand skill loading"""
    
    def __init__(self):
        self._skills: Dict[str, Type[SkillBase]] = {}
        self.logger = get_logger("skill_registry")
        # Remove _discovered flag since we're not doing discovery anymore
    
    def _load_skill_on_demand(self, skill_name: str) -> Optional[Type[SkillBase]]:
        """Load a skill on-demand by name"""
        if skill_name in self._skills:
            return self._skills[skill_name]
            
        # Try to load the skill from its expected directory
        skills_dir = Path(__file__).parent
        skill_dir = skills_dir / skill_name
        skill_file = skill_dir / "skill.py"
        
        if not skill_file.exists():
            self.logger.debug(f"Skill '{skill_name}' not found at {skill_file}")
            return None
            
        try:
            # Import the skill module
            module_name = f"signalwire_agents.skills.{skill_name}.skill"
            spec = importlib.util.spec_from_file_location(module_name, skill_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find SkillBase subclasses in the module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, SkillBase) and 
                    obj != SkillBase and
                    obj.SKILL_NAME == skill_name):  # Match exact skill name
                    
                    self.register_skill(obj)
                    return obj
                    
            self.logger.warning(f"No skill class found with name '{skill_name}' in {skill_file}")
            return None
                    
        except Exception as e:
            self.logger.error(f"Failed to load skill '{skill_name}' from {skill_file}: {e}")
            return None
    
    def discover_skills(self) -> None:
        """Deprecated: Skills are now loaded on-demand"""
        # Keep this method for backwards compatibility but make it a no-op
        pass
    
    def _load_skill_from_directory(self, skill_dir: Path) -> None:
        """Deprecated: Skills are now loaded on-demand"""
        # Keep this method for backwards compatibility but make it a no-op
        pass
    
    def register_skill(self, skill_class: Type[SkillBase]) -> None:
        """Register a skill class"""
        if skill_class.SKILL_NAME in self._skills:
            self.logger.warning(f"Skill '{skill_class.SKILL_NAME}' already registered")
            return
            
        self._skills[skill_class.SKILL_NAME] = skill_class
        self.logger.debug(f"Registered skill '{skill_class.SKILL_NAME}'")
    
    def get_skill_class(self, skill_name: str) -> Optional[Type[SkillBase]]:
        """Get skill class by name, loading on-demand if needed"""
        # First check if already loaded
        if skill_name in self._skills:
            return self._skills[skill_name]
        
        # Try to load on-demand
        return self._load_skill_on_demand(skill_name)
    
    def list_skills(self) -> List[Dict[str, str]]:
        """List all available skills by scanning directories (only when explicitly requested)"""
        # Only scan when this method is explicitly called (e.g., for CLI tools)
        skills_dir = Path(__file__).parent
        available_skills = []
        
        for item in skills_dir.iterdir():
            if item.is_dir() and not item.name.startswith('__'):
                skill_file = item / "skill.py"
                if skill_file.exists():
                    # Try to load the skill to get its metadata
                    skill_class = self._load_skill_on_demand(item.name)
                    if skill_class:
                        available_skills.append({
                            "name": skill_class.SKILL_NAME,
                            "description": skill_class.SKILL_DESCRIPTION,
                            "version": skill_class.SKILL_VERSION,
                            "required_packages": skill_class.REQUIRED_PACKAGES,
                            "required_env_vars": skill_class.REQUIRED_ENV_VARS,
                            "supports_multiple_instances": skill_class.SUPPORTS_MULTIPLE_INSTANCES
                        })
        
        return available_skills

# Global registry instance
skill_registry = SkillRegistry() 