"""
SwaigFunctionResult class for handling the response format of SWAIG function calls
"""

from typing import Dict, List, Any, Optional, Union


class SwaigActionTypes:
    """Constants for standard SWAIG action types"""
    PLAY = "play"
    TRANSFER = "transfer"
    SEND_SMS = "send_sms"
    JOIN_ROOM = "join_room"
    RETURN = "return"
    HANG_UP = "hang_up"
    RECORD = "record"
    COLLECT = "collect"


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
