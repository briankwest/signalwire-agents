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
            .add_action("transfer", dest="support")
        )
    """
    def __init__(self, response: Optional[str] = None):
        """
        Initialize a new SWAIG function result
        
        Args:
            response: Optional natural language response to include
        """
        self.response = response or ""
        self.actions: List[Dict[str, Any]] = []
    
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
    
    def add_action(self, action_type: str, **kwargs) -> 'SwaigFunctionResult':
        """
        Add a structured action to the response
        
        Args:
            action_type: The type of action (play, transfer, etc)
            **kwargs: Action-specific parameters
            
        Returns:
            Self for method chaining
        """
        self.actions.append({"type": action_type, **kwargs})
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to the JSON structure expected by SWAIG
        
        Returns:
            Dictionary in SWAIG function response format
        """
        return {
            "status": "ok",
            "result": {
                "response": self.response,
                "action": self.actions
            }
        }
