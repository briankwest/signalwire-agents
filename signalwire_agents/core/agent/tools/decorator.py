"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

"""Tool decorator functionality."""

from functools import wraps
from typing import Callable, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ToolDecorator:
    """Handles tool decoration logic."""
    
    @staticmethod
    def create_instance_decorator(registry):
        """
        Create instance tool decorator.
        
        Args:
            registry: ToolRegistry instance to register with
            
        Returns:
            Decorator function
        """
        def decorator(name=None, **kwargs):
            """
            Decorator for defining SWAIG tools in a class.
            
            Used as:
            
            @agent.tool(name="example_function", parameters={...})
            def example_function(self, param1):
                # ...
            """
            def inner_decorator(func):
                nonlocal name
                if name is None:
                    name = func.__name__
                    
                parameters = kwargs.pop("parameters", {})
                description = kwargs.pop("description", func.__doc__ or f"Function {name}")
                secure = kwargs.pop("secure", True)
                fillers = kwargs.pop("fillers", None)
                webhook_url = kwargs.pop("webhook_url", None)
                
                registry.define_tool(
                    name=name,
                    description=description,
                    parameters=parameters,
                    handler=func,
                    secure=secure,
                    fillers=fillers,
                    webhook_url=webhook_url,
                    **kwargs  # Pass through any additional swaig_fields
                )
                return func
            return inner_decorator
        return decorator
    
    @classmethod
    def create_class_decorator(cls):
        """
        Create class tool decorator.
        
        Returns:
            Decorator function
        """
        def tool(name=None, **kwargs):
            """
            Class method decorator for defining SWAIG tools.
            
            Used as:
            
            @AgentBase.tool(name="example_function", parameters={...})
            def example_function(self, param1):
                # ...
            """
            def decorator(func):
                # Mark the function as a tool
                func._is_tool = True
                func._tool_name = name if name else func.__name__
                func._tool_params = kwargs
                
                # Return the original function
                return func
            return decorator
        return tool