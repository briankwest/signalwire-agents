"""
SwaigFunction class for defining and managing SWAIG function interfaces
"""

from typing import Dict, Any, Optional, Callable, List, Type, Union


class SwaigFunction:
    """
    Represents a SWAIG function that can be called by an AI agent during a call.
    
    Each function defines its name, parameters schema, and handler function.
    """
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable,
        secure: bool = True,
        output_schema: Optional[Dict] = None
    ):
        """
        Initialize a new SWAIG function
        
        Args:
            name: Function name to be exposed to the AI
            description: Description of what the function does
            parameters: JSON Schema definition of parameters
            handler: Callable function that implements the logic
            secure: Whether this function requires token validation
            output_schema: Optional schema for the function's return value
        """
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler
        self.secure = secure
        self.output_schema = output_schema

    def validate_args(self, args: Dict[str, Any]) -> bool:
        """
        Validate that the provided arguments match the parameter schema
        
        Args:
            args: Dictionary of arguments to validate
            
        Returns:
            True if valid, False if not
        """
        # This would use a more sophisticated JSON Schema validation in full implementation
        return True
        
    def to_swaig(self, base_url: str, token: Optional[str] = None, call_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Convert this function to a SWAIG-compatible JSON object for SWML
        
        Args:
            base_url: Base URL for the webhook
            token: Optional auth token to include
            call_id: Optional call ID for session tracking
            
        Returns:
            Dictionary representation for the SWAIG array in SWML
        """
        # Build URL with auth token if provided
        url = f"{base_url}/tools/{self.name}"
        if token and call_id:
            url = f"{url}?token={token}&call_id={call_id}"
        
        return {
            "function": self.name,
            "arguments": self.parameters,
            "request": {
                "url": url,
                "method": "POST"
            }
        }

    def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the function handler with the provided arguments
        
        Args:
            args: Arguments to pass to the handler
            
        Returns:
            Handler result converted to a dictionary
        """
        from signalwire_agents.core.function_result import SwaigFunctionResult
        
        # Call the handler
        result = self.handler(**args)
        
        # If result is already a SwaigFunctionResult, convert to dict
        if hasattr(result, 'to_dict'):
            return result.to_dict()
        
        # If result is a string, wrap in a SwaigFunctionResult
        if isinstance(result, str):
            return SwaigFunctionResult(result).to_dict()
        
        # If result is already a dict, assume it's properly formatted
        if isinstance(result, dict) and "status" in result:
            return result
            
        # Default case - wrap in a result with empty response
        return SwaigFunctionResult().to_dict()
