"""
SwaigFunction class for defining and managing SWAIG function interfaces
"""

from typing import Dict, Any, Optional, Callable, List, Type, Union
import inspect


class SWAIGFunction:
    """
    Represents a SWAIG function for AI integration
    """
    def __init__(
        self, 
        name: str, 
        handler: Callable, 
        description: str,
        parameters: Dict[str, Dict] = None,
        secure: bool = False,
        fillers: Optional[Dict[str, List[str]]] = None
    ):
        """
        Initialize a new SWAIG function
        
        Args:
            name: Name of the function to appear in SWML
            handler: Function to call when this SWAIG function is invoked
            description: Human-readable description of the function
            parameters: Dictionary of parameters, keys are parameter names, values are param definitions
            secure: Whether this function requires token validation
            fillers: Optional dictionary of filler phrases by language code
        """
        self.name = name
        self.handler = handler
        self.description = description
        self.parameters = parameters or {}
        self.secure = secure
        self.fillers = fillers
        
    def _ensure_parameter_structure(self) -> Dict:
        """
        Ensure the parameters are correctly structured for SWML
        
        Returns:
            Parameters dict with correct structure
        """
        if not self.parameters:
            return {"type": "object", "properties": {}}
            
        # Check if we already have the correct structure 
        if "type" in self.parameters and "properties" in self.parameters:
            return self.parameters
            
        # Otherwise, wrap the parameters in the expected structure
        return {
            "type": "object",
            "properties": self.parameters
        }
        
    def __call__(self, *args, **kwargs):
        """
        Call the underlying handler function
        """
        return self.handler(*args, **kwargs)

    def execute(self, args: Dict[str, Any], raw_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the function with the given arguments
        
        Args:
            args: Parsed arguments for the function
            raw_data: Optional raw request data
            
        Returns:
            Function result as a dictionary with "response" and optional "actions"
        """
        try:
            # Inspect the function signature to determine parameter names
            sig = inspect.signature(self.handler)
            param_names = list(sig.parameters.keys())
            
            # Check which parameters the handler accepts
            handler_kwargs = {}
            
            # First parameter is always the 'self' instance
            param_count = len(param_names)
            
            if param_count >= 2:
                # At least one parameter after 'self', assume it's for args
                handler_kwargs[param_names[1]] = args
                
            if param_count >= 3 and raw_data is not None:
                # Has a third parameter, pass raw_data
                handler_kwargs[param_names[2]] = raw_data
                
            # Call the handler with the appropriate parameters
            result = self.handler(**handler_kwargs)
                
            # Convert the result to a dictionary if needed
            from signalwire_agents.core.function_result import SwaigFunctionResult
            if isinstance(result, SwaigFunctionResult):
                # If the result is already a SwaigFunctionResult, serialize it to dict
                return result.to_dict()
            elif not isinstance(result, dict):
                # If not a dict or SwaigFunctionResult, wrap it
                return {"response": str(result)}
                
            return result
        except Exception as e:
            # Return an error response
            return {"response": f"Error: {str(e)}"}
        
    def validate_args(self, args: Dict[str, Any]) -> bool:
        """
        Validate the arguments against the parameter schema
        
        Args:
            args: Arguments to validate
            
        Returns:
            True if valid, False otherwise
        """
        # TODO: Implement JSON Schema validation
        return True
        
    def to_swaig(self, base_url: str, token: Optional[str] = None, call_id: Optional[str] = None, include_auth: bool = True) -> Dict[str, Any]:
        """
        Convert this function to a SWAIG-compatible JSON object for SWML
        
        Args:
            base_url: Base URL for the webhook
            token: Optional auth token to include
            call_id: Optional call ID for session tracking
            include_auth: Whether to include auth credentials in URL
            
        Returns:
            Dictionary representation for the SWAIG array in SWML
        """
        # All functions use a single /swaig endpoint
        url = f"{base_url}/swaig"
        
        # Add token and call_id parameters if provided
        if token and call_id:
            url = f"{url}?token={token}&call_id={call_id}"
        
        # Create properly structured function definition
        function_def = {
            "function": self.name,
            "description": self.description,
            "parameters": self._ensure_parameter_structure(),
        }
        
        # Only add web_hook_url if not using defaults
        # This will be handled by the defaults section in the SWAIG array
        if url:
            function_def["web_hook_url"] = url
            
        # Add fillers if provided
        if self.fillers and len(self.fillers) > 0:
            function_def["fillers"] = self.fillers
            
        return function_def
