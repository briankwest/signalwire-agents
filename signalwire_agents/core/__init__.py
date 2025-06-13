"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

"""
Core components for SignalWire AI Agents
"""

from signalwire_agents.core.agent_base import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult
from signalwire_agents.core.swaig_function import SWAIGFunction
from signalwire_agents.core.swml_service import SWMLService
from signalwire_agents.core.swml_handler import SWMLVerbHandler, VerbHandlerRegistry
from signalwire_agents.core.swml_builder import SWMLBuilder

__all__ = [
    'AgentBase', 
    'SwaigFunctionResult', 
    'SWAIGFunction',
    'SWMLService',
    'SWMLVerbHandler',
    'VerbHandlerRegistry',
    'SWMLBuilder'
]
