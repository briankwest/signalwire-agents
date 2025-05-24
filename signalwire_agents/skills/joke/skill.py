"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

from typing import List, Dict, Any

from signalwire_agents.core.skill_base import SkillBase
from signalwire_agents.core.data_map import DataMap
from signalwire_agents.core.function_result import SwaigFunctionResult


class JokeSkill(SkillBase):
    """Joke telling capability using API Ninjas with DataMap"""
    
    SKILL_NAME = "joke"
    SKILL_DESCRIPTION = "Tell jokes using the API Ninjas joke API"
    SKILL_VERSION = "1.0.0"
    REQUIRED_PACKAGES = []  # DataMap doesn't require local packages
    REQUIRED_ENV_VARS = []  # API key comes from parameters
    
    def setup(self) -> bool:
        """Setup the joke skill"""
        # Validate required parameters
        required_params = ['api_key']
        missing_params = [param for param in required_params if not self.params.get(param)]
        if missing_params:
            self.logger.error(f"Missing required parameters: {missing_params}")
            return False
            
        # Set parameters from config
        self.api_key = self.params['api_key']
        
        # Optional parameters with defaults
        self.tool_name = self.params.get('tool_name', 'get_joke')
        
        return True
        
    def register_tools(self) -> None:
        """Register joke tool using DataMap"""
        
        # Create DataMap tool for jokes - uses required enum parameter
        joke_tool = (DataMap(self.tool_name)
            .description('Get a random joke from API Ninjas')
            .parameter('type', 'string', 'Type of joke to get', 
                      required=True, enum=['jokes', 'dadjokes'])
            .webhook('GET', "https://api.api-ninjas.com/v1/${args.type}", 
                     headers={'X-Api-Key': self.api_key})
            .output(SwaigFunctionResult('Here\'s a joke: ${array[0].joke}'))
            .error_keys(['error'])
            .fallback_output(SwaigFunctionResult('Sorry, there is a problem with the joke service right now. Please try again later.'))
        )
        
        # Register the DataMap tool with the agent
        self.agent.register_swaig_function(joke_tool.to_swaig_function())
        
    def get_hints(self) -> List[str]:
        """Return speech recognition hints"""
        # Currently no hints are provided, but you could add them like:
        # return [
        #     "joke", "tell me a joke", "funny", "humor", "dad joke", 
        #     "regular joke", "make me laugh", "comedy"
        # ]
        return []
        
    def get_global_data(self) -> Dict[str, Any]:
        """Return global data to be available in DataMap variables"""
        return {
            "joke_skill_enabled": True
        }
        
    def get_prompt_sections(self) -> List[Dict[str, Any]]:
        """Return prompt sections to add to agent"""
        return [
            {
                "title": "Joke Telling", 
                "body": "You can tell jokes to entertain users.",
                "bullets": [
                    f"Use {self.tool_name} to tell jokes when users ask for humor",
                    "You can tell regular jokes or dad jokes",
                    "Be enthusiastic and fun when sharing jokes"
                ]
            }
        ] 