"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

"""
SignalWire AI Agents SDK
=======================

A package for building AI agents using SignalWire's AI and SWML capabilities.
"""

__version__ = "0.1.9"

# Import core classes for easier access
from signalwire_agents.core.agent_base import AgentBase
from signalwire_agents.agent_server import AgentServer
from signalwire_agents.core.swml_service import SWMLService
from signalwire_agents.core.swml_builder import SWMLBuilder
from signalwire_agents.core.state import StateManager, FileStateManager
from signalwire_agents.core.function_result import SwaigFunctionResult
from signalwire_agents.core.swaig_function import SWAIGFunction
from .core.data_map import DataMap, create_simple_api_tool, create_expression_tool

# Import skills to trigger discovery
import signalwire_agents.skills

# Import convenience functions from the CLI (if available)
try:
    from signalwire_agents.cli.helpers import start_agent, run_agent, list_skills
except ImportError:
    # CLI helpers not available, define minimal versions
    def start_agent(*args, **kwargs):
        raise NotImplementedError("CLI helpers not available")
    def run_agent(*args, **kwargs):
        raise NotImplementedError("CLI helpers not available")
    def list_skills(*args, **kwargs):
        raise NotImplementedError("CLI helpers not available")

__all__ = [
    "AgentBase",
    "AgentServer", 
    "SWMLService",
    "SWMLBuilder",
    "StateManager",
    "FileStateManager",
    "SwaigFunctionResult",
    "SWAIGFunction",
    "DataMap",
    "create_simple_api_tool", 
    "create_expression_tool",
    "start_agent",
    "run_agent",
    "list_skills"
]
