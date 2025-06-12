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

# Configure logging before any other imports to ensure early initialization
from .core.logging_config import configure_logging
configure_logging()

__version__ = "0.1.21"

# Import core classes for easier access
from .core.agent_base import AgentBase
from .core.contexts import ContextBuilder, Context, Step, create_simple_context
from .core.data_map import DataMap, create_simple_api_tool, create_expression_tool
from .core.state import StateManager, FileStateManager
from signalwire_agents.agent_server import AgentServer
from signalwire_agents.core.swml_service import SWMLService
from signalwire_agents.core.swml_builder import SWMLBuilder
from signalwire_agents.core.function_result import SwaigFunctionResult
from signalwire_agents.core.swaig_function import SWAIGFunction

# Lazy import skills to avoid slow startup for CLI tools
# Skills are now loaded on-demand when requested
def _get_skill_registry():
    """Lazy import and return skill registry"""
    import signalwire_agents.skills
    return signalwire_agents.skills.skill_registry

# Lazy import convenience functions from the CLI (if available)
def start_agent(*args, **kwargs):
    """Start an agent (lazy import)"""
    try:
        from signalwire_agents.cli.helpers import start_agent as _start_agent
        return _start_agent(*args, **kwargs)
    except ImportError:
        raise NotImplementedError("CLI helpers not available")

def run_agent(*args, **kwargs):
    """Run an agent (lazy import)"""
    try:
        from signalwire_agents.cli.helpers import run_agent as _run_agent
        return _run_agent(*args, **kwargs)
    except ImportError:
        raise NotImplementedError("CLI helpers not available")

def list_skills(*args, **kwargs):
    """List available skills (lazy import)"""
    try:
        from signalwire_agents.cli.helpers import list_skills as _list_skills
        return _list_skills(*args, **kwargs)
    except ImportError:
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
    "ContextBuilder",
    "Context", 
    "Step",
    "create_simple_context",
    "start_agent",
    "run_agent",
    "list_skills"
]
