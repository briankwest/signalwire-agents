"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, TYPE_CHECKING, Optional
import logging

if TYPE_CHECKING:
    from signalwire_agents.core.agent_base import AgentBase

class SkillBase(ABC):
    """Abstract base class for all agent skills"""
    
    # Subclasses must define these
    SKILL_NAME: str = None           # Required: unique identifier
    SKILL_DESCRIPTION: str = None    # Required: human-readable description
    SKILL_VERSION: str = "1.0.0"     # Semantic version
    REQUIRED_PACKAGES: List[str] = [] # Python packages needed
    REQUIRED_ENV_VARS: List[str] = [] # Environment variables needed
    
    def __init__(self, agent: 'AgentBase', params: Optional[Dict[str, Any]] = None):
        if self.SKILL_NAME is None:
            raise ValueError(f"{self.__class__.__name__} must define SKILL_NAME")
        if self.SKILL_DESCRIPTION is None:
            raise ValueError(f"{self.__class__.__name__} must define SKILL_DESCRIPTION")
            
        self.agent = agent
        self.params = params or {}
        self.logger = logging.getLogger(f"skill.{self.SKILL_NAME}")
        
        # Extract swaig_fields from params for merging into tool definitions
        self.swaig_fields = self.params.pop('swaig_fields', {})
        
    @abstractmethod
    def setup(self) -> bool:
        """
        Setup the skill (validate env vars, initialize APIs, etc.)
        Returns True if setup successful, False otherwise
        """
        pass
        
    @abstractmethod
    def register_tools(self) -> None:
        """Register SWAIG tools with the agent"""
        pass
        
    def define_tool_with_swaig_fields(
        self, 
        name: str, 
        description: str, 
        parameters: Dict[str, Any], 
        handler,
        **additional_kwargs
    ):
        """
        Helper method to define a tool with swaig_fields merged in
        
        Args:
            name: Function name
            description: Function description
            parameters: Function parameters schema
            handler: Function handler
            **additional_kwargs: Additional keyword arguments for define_tool
            
        This method automatically merges the swaig_fields from skill params
        into the tool definition, allowing the skill loader to customize
        SWAIG function properties.
        """
        # Start with the additional kwargs passed to this method
        tool_kwargs = additional_kwargs.copy()
        
        # Merge in the swaig_fields from params (swaig_fields take precedence)
        tool_kwargs.update(self.swaig_fields)
        
        # Call the agent's define_tool with all parameters
        self.agent.define_tool(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            **tool_kwargs
        )
        
    def get_hints(self) -> List[str]:
        """Return speech recognition hints for this skill"""
        return []
        
    def get_global_data(self) -> Dict[str, Any]:
        """Return data to add to agent's global context"""
        return {}
        
    def get_prompt_sections(self) -> List[Dict[str, Any]]:
        """Return prompt sections to add to agent"""
        return []
        
    def cleanup(self) -> None:
        """Cleanup when skill is removed or agent shuts down"""
        pass
        
    def validate_env_vars(self) -> bool:
        """Check if all required environment variables are set"""
        import os
        missing = [var for var in self.REQUIRED_ENV_VARS if not os.getenv(var)]
        if missing:
            self.logger.error(f"Missing required environment variables: {missing}")
            return False
        return True
        
    def validate_packages(self) -> bool:
        """Check if all required packages are available"""
        import importlib
        missing = []
        for package in self.REQUIRED_PACKAGES:
            try:
                importlib.import_module(package)
            except ImportError:
                missing.append(package)
        if missing:
            self.logger.error(f"Missing required packages: {missing}")
            return False
        return True 