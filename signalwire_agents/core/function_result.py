"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

"""
SwaigFunctionResult class for handling the response format of SWAIG function calls
"""

from typing import Dict, List, Any, Optional, Union


class SwaigFunctionResult:
    """
    Wrapper around SWAIG function responses that handles proper formatting
    of response text and actions.
    
    Example:
        return SwaigFunctionResult("Found your order")
        
        # With actions
        return (
            SwaigFunctionResult("I'll transfer you to support")
            .add_action("transfer", {"dest": "support"})
        )
        
        # With simple action value
        return (
            SwaigFunctionResult("I'll confirm that")
            .add_action("confirm", True)
        )
        
        # With multiple actions
        return (
            SwaigFunctionResult("Processing your request")
            .add_actions([
                {"set_global_data": {"key": "value"}},
                {"play": {"url": "music.mp3"}}
            ])
        )
    """
    def __init__(self, response: Optional[str] = None):
        """
        Initialize a new SWAIG function result
        
        Args:
            response: Optional natural language response to include
        """
        self.response = response or ""
        self.action: List[Dict[str, Any]] = []
    
    def set_response(self, response: str) -> 'SwaigFunctionResult':
        """
        Set the natural language response text
        
        Args:
            response: The text the AI should say
            
        Returns:
            Self for method chaining
        """
        self.response = response
        return self
    
    def add_action(self, name: str, data: Any) -> 'SwaigFunctionResult':
        """
        Add a structured action to the response
        
        Args:
            name: The name/type of the action (e.g., "play", "transfer")
            data: The data for the action - can be a string, boolean, object, or array
            
        Returns:
            Self for method chaining
        """
        self.action.append({name: data})
        return self
    
    def add_actions(self, actions: List[Dict[str, Any]]) -> 'SwaigFunctionResult':
        """
        Add multiple structured actions to the response
        
        Args:
            actions: List of action objects to add to the response
            
        Returns:
            Self for method chaining
        """
        self.action.extend(actions)
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to the JSON structure expected by SWAIG
        
        The result must have at least one of:
        - 'response': Text to be spoken by the AI
        - 'action': Array of action objects
        
        Returns:
            Dictionary in SWAIG function response format
        """
        # Create the result object
        result = {}
        
        # Add response if present
        if self.response:
            result["response"] = self.response
            
        # Add action if present
        if self.action:
            result["action"] = self.action
            
        # Ensure we have at least one of response or action
        if not result:
            # Default response if neither is present
            result["response"] = "Action completed."
            
        return result
