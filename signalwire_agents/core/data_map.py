"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

"""
DataMap class for building SWAIG data_map configurations
"""

from typing import Dict, List, Any, Optional, Union, Pattern
import re
from .function_result import SwaigFunctionResult


class DataMap:
    """
    Builder class for creating SWAIG data_map configurations.
    
    This provides a fluent interface for building data_map tools that execute
    on the SignalWire server without requiring webhook endpoints. Works similar
    to SwaigFunctionResult but for building data_map structures.
    
    Example usage:
        # Simple API call
        data_map = (DataMap('get_weather')
            .purpose('Get current weather information')
            .parameter('location', 'string', 'City name', required=True)
            .webhook('GET', 'https://api.weather.com/v1/current?key=API_KEY&q=${location}')
            .output(SwaigFunctionResult('Weather in ${location}: ${response.current.condition.text}, ${response.current.temp_f}°F'))
        )
        
        # Expression-based responses (no API calls)
        data_map = (DataMap('file_control')
            .purpose('Control file playback')
            .parameter('command', 'string', 'Playback command')
            .parameter('filename', 'string', 'File to control', required=False)
            .expression(r'start.*', SwaigFunctionResult().add_action('start_playback', {'file': '${args.filename}'}))
            .expression(r'stop.*', SwaigFunctionResult().add_action('stop_playback', True))
        )
        
        # API with array processing
        data_map = (DataMap('search_docs')
            .purpose('Search documentation')
            .parameter('query', 'string', 'Search query', required=True)
            .webhook('POST', 'https://api.docs.com/search', headers={'Authorization': 'Bearer TOKEN'})
            .body({'query': '${query}', 'limit': 3})
            .foreach('${response.results}')
            .output(SwaigFunctionResult('Found: ${foreach.title} - ${foreach.summary}'))
        )
    """
    
    def __init__(self, function_name: str):
        """
        Initialize a new DataMap builder
        
        Args:
            function_name: Name of the SWAIG function this data_map will create
        """
        self.function_name = function_name
        self._purpose = ""
        self._parameters = {}
        self._expressions = []
        self._webhooks = []
        self._foreach = None
        self._output = None
        self._error_keys = []
        
    def purpose(self, description: str) -> 'DataMap':
        """
        Set the function description/purpose
        
        Args:
            description: Human-readable description of what this function does
            
        Returns:
            Self for method chaining
        """
        self._purpose = description
        return self
    
    def description(self, description: str) -> 'DataMap':
        """
        Set the function description (alias for purpose)
        
        Args:
            description: Human-readable description of what this function does
            
        Returns:
            Self for method chaining
        """
        return self.purpose(description)
    
    def parameter(self, name: str, param_type: str, description: str, 
                 required: bool = False, enum: Optional[List[str]] = None) -> 'DataMap':
        """
        Add a function parameter
        
        Args:
            name: Parameter name
            param_type: JSON schema type (string, number, boolean, array, object)
            description: Parameter description
            required: Whether parameter is required
            enum: Optional list of allowed values
            
        Returns:
            Self for method chaining
        """
        param_def = {
            "type": param_type,
            "description": description
        }
        
        if enum:
            param_def["enum"] = enum
            
        self._parameters[name] = param_def
        
        if required:
            if "required" not in self._parameters:
                self._parameters["required"] = []
            if name not in self._parameters["required"]:
                self._parameters["required"].append(name)
        
        return self
    
    def expression(self, pattern: Union[str, Pattern], output: SwaigFunctionResult) -> 'DataMap':
        """
        Add an expression pattern for pattern-based responses
        
        Args:
            pattern: Regex pattern string or compiled Pattern object
            output: SwaigFunctionResult to return when pattern matches
            
        Returns:
            Self for method chaining
        """
        if isinstance(pattern, Pattern):
            pattern_str = pattern.pattern
        else:
            pattern_str = str(pattern)
            
        self._expressions.append({
            "string": pattern_str,
            "output": output.to_dict()
        })
        return self
    
    def webhook(self, method: str, url: str, headers: Optional[Dict[str, str]] = None) -> 'DataMap':
        """
        Add a webhook API call
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: API endpoint URL (can include ${variable} substitutions)
            headers: Optional HTTP headers
            
        Returns:
            Self for method chaining
        """
        webhook_def = {
            "url": url,
            "method": method.upper()
        }
        
        if headers:
            webhook_def["headers"] = headers
            
        self._webhooks.append(webhook_def)
        return self
    
    def body(self, data: Dict[str, Any]) -> 'DataMap':
        """
        Set request body for the last added webhook (POST/PUT requests)
        
        Args:
            data: Request body data (can include ${variable} substitutions)
            
        Returns:
            Self for method chaining
        """
        if not self._webhooks:
            raise ValueError("Must add webhook before setting body")
            
        self._webhooks[-1]["body"] = data
        return self
    
    def foreach(self, array_path: str) -> 'DataMap':
        """
        Process an array from the webhook response
        
        Args:
            array_path: JSON path to array in response (e.g., '${response.results}')
            
        Returns:
            Self for method chaining
        """
        self._foreach = array_path
        return self
    
    def output(self, result: SwaigFunctionResult) -> 'DataMap':
        """
        Set the final output result
        
        Args:
            result: SwaigFunctionResult defining the final response
            
        Returns:
            Self for method chaining
        """
        self._output = result.to_dict()
        return self
    
    def error_keys(self, keys: List[str]) -> 'DataMap':
        """
        Set keys that indicate API errors
        
        Args:
            keys: List of JSON keys whose presence indicates an error
            
        Returns:
            Self for method chaining
        """
        self._error_keys = keys
        return self
    
    def to_swaig_function(self) -> Dict[str, Any]:
        """
        Convert this DataMap to a SWAIG function definition
        
        Returns:
            Dictionary with function definition and data_map instead of url
        """
        # Build parameter schema
        if self._parameters:
            # Extract required params without mutating original dict
            required_params = self._parameters.get("required", [])
            param_properties = {k: v for k, v in self._parameters.items() if k != "required"}
            
            param_schema = {
                "type": "object",
                "properties": param_properties
            }
            if required_params:
                param_schema["required"] = required_params
        else:
            param_schema = {"type": "object", "properties": {}}
        
        # Build data_map structure
        data_map = {}
        
        # Add expressions if present
        if self._expressions:
            data_map["expressions"] = self._expressions
            
        # Add webhooks if present  
        if self._webhooks:
            data_map["webhooks"] = self._webhooks
            
        # Add foreach if present
        if self._foreach:
            data_map["foreach"] = self._foreach
            
        # Add output if present
        if self._output:
            data_map["output"] = self._output
            
        # Add error_keys if present
        if self._error_keys:
            data_map["error_keys"] = self._error_keys
        
        # Build final function definition with correct field names
        function_def = {
            "function": self.function_name,
            "description": self._purpose or f"Execute {self.function_name}",
            "parameters": param_schema,
            "data_map": data_map
        }
        
        return function_def


def create_simple_api_tool(name: str, url: str, response_template: str, 
                          parameters: Optional[Dict[str, Dict]] = None,
                          method: str = "GET", headers: Optional[Dict[str, str]] = None,
                          body: Optional[Dict[str, Any]] = None,
                          error_keys: Optional[List[str]] = None) -> DataMap:
    """
    Create a simple API tool with minimal configuration
    
    Args:
        name: Function name
        url: API endpoint URL
        response_template: Template for formatting the response
        parameters: Optional parameter definitions
        method: HTTP method (default: GET)
        headers: Optional HTTP headers
        body: Optional request body (for POST/PUT)
        error_keys: Optional list of error indicator keys
        
    Returns:
        Configured DataMap object
    """
    data_map = DataMap(name)
    
    # Add parameters if provided
    if parameters:
        for param_name, param_def in parameters.items():
            required = param_def.get("required", False)
            data_map.parameter(
                param_name, 
                param_def.get("type", "string"),
                param_def.get("description", f"{param_name} parameter"),
                required=required
            )
    
    # Add webhook
    data_map.webhook(method, url, headers)
    
    # Add body if provided
    if body:
        data_map.body(body)
        
    # Add error keys if provided
    if error_keys:
        data_map.error_keys(error_keys)
    
    # Set output
    data_map.output(SwaigFunctionResult(response_template))
    
    return data_map


def create_expression_tool(name: str, patterns: Dict[Union[str, Pattern], SwaigFunctionResult],
                          parameters: Optional[Dict[str, Dict]] = None) -> DataMap:
    """
    Create an expression-based tool for pattern matching responses
    
    Args:
        name: Function name
        patterns: Dictionary mapping regex patterns to SwaigFunctionResult responses
        parameters: Optional parameter definitions
        
    Returns:
        Configured DataMap object
    """
    data_map = DataMap(name)
    
    # Add parameters if provided
    if parameters:
        for param_name, param_def in parameters.items():
            required = param_def.get("required", False)
            data_map.parameter(
                param_name,
                param_def.get("type", "string"), 
                param_def.get("description", f"{param_name} parameter"),
                required=required
            )
    
    # Add expressions
    for pattern, result in patterns.items():
        data_map.expression(pattern, result)
        
    return data_map 