"""
SignalWire AI Agents SDK
=======================

A package for building AI agents using SignalWire's AI and SWML capabilities.
"""

__version__ = "0.1.0"

# Import core classes for easier access
from signalwire_agents.core.agent_base import AgentBase
from signalwire_agents.agent_server import AgentServer
from signalwire_agents.core.swml_service import SWMLService
from signalwire_agents.core.swml_builder import SWMLBuilder
from signalwire_agents.core.state import StateManager, FileStateManager

__all__ = ["AgentBase", "AgentServer", "SWMLService", "SWMLBuilder", "StateManager", "FileStateManager"]
