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
from typing import Dict, List, Type, Optional
from pathlib import Path
import logging

from signalwire_agents.core.skill_base import SkillBase

class SkillRegistry:
    """Global registry for discovering and managing skills"""
    
    def __init__(self):
        self._skills: Dict[str, Type[SkillBase]] = {}
        self.logger = logging.getLogger("skill_registry")
        self._discovered = False
    
    def discover_skills(self) -> None:
        """Discover skills from the skills directory"""
        if self._discovered:
            return
            
        # Get the skills directory path
        skills_dir = Path(__file__).parent
        
        # Scan for skill directories
        for item in skills_dir.iterdir():
            if item.is_dir() and not item.name.startswith('__'):
                self._load_skill_from_directory(item)
        
        self._discovered = True
        self.logger.info(f"Discovered {len(self._skills)} skills")
    
    def _load_skill_from_directory(self, skill_dir: Path) -> None:
        """Load a skill from a directory"""
        skill_file = skill_dir / "skill.py"
        if not skill_file.exists():
            return
            
        try:
            # Import the skill module
            module_name = f"signalwire_agents.skills.{skill_dir.name}.skill"
            spec = importlib.util.spec_from_file_location(module_name, skill_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find SkillBase subclasses in the module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, SkillBase) and 
                    obj != SkillBase and
                    obj.SKILL_NAME is not None):
                    
                    self.register_skill(obj)
                    
        except Exception as e:
            self.logger.error(f"Failed to load skill from {skill_dir}: {e}")
    
    def register_skill(self, skill_class: Type[SkillBase]) -> None:
        """Register a skill class"""
        if skill_class.SKILL_NAME in self._skills:
            self.logger.warning(f"Skill '{skill_class.SKILL_NAME}' already registered")
            return
            
        self._skills[skill_class.SKILL_NAME] = skill_class
        self.logger.debug(f"Registered skill '{skill_class.SKILL_NAME}'")
    
    def get_skill_class(self, skill_name: str) -> Optional[Type[SkillBase]]:
        """Get skill class by name"""
        self.discover_skills()  # Ensure skills are discovered
        return self._skills.get(skill_name)
    
    def list_skills(self) -> List[Dict[str, str]]:
        """List all registered skills with metadata"""
        self.discover_skills()
        return [
            {
                "name": skill_class.SKILL_NAME,
                "description": skill_class.SKILL_DESCRIPTION,
                "version": skill_class.SKILL_VERSION,
                "required_packages": skill_class.REQUIRED_PACKAGES,
                "required_env_vars": skill_class.REQUIRED_ENV_VARS
            }
            for skill_class in self._skills.values()
        ]

# Global registry instance
skill_registry = SkillRegistry() 