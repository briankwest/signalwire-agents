"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

"""
Prefab agents with specific functionality that can be used out-of-the-box
"""

from signalwire_agents.prefabs.info_gatherer import InfoGathererAgent
from signalwire_agents.prefabs.faq_bot import FAQBotAgent
from signalwire_agents.prefabs.concierge import ConciergeAgent
from signalwire_agents.prefabs.survey import SurveyAgent
from signalwire_agents.prefabs.receptionist import ReceptionistAgent

__all__ = [
    "InfoGathererAgent",
    "FAQBotAgent",
    "ConciergeAgent",
    "SurveyAgent",
    "ReceptionistAgent"
]
