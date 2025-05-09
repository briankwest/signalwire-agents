"""
Prefab agents with specific functionality that can be used out-of-the-box
"""

from signalwire_agents.prefabs.info_gatherer import InfoGathererAgent
from signalwire_agents.prefabs.faq_bot import FAQBotAgent
from signalwire_agents.prefabs.concierge import ConciergeAgent
from signalwire_agents.prefabs.survey import SurveyAgent

__all__ = [
    "InfoGathererAgent",
    "FAQBotAgent",
    "ConciergeAgent",
    "SurveyAgent"
]
