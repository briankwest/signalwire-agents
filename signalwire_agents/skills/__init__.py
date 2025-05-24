"""
SignalWire Agent Skills Package

This package contains built-in skills for SignalWire agents.
Skills are automatically discovered from subdirectories.
"""

# Import the registry to make it available
from .registry import skill_registry

# Trigger skill discovery on import
skill_registry.discover_skills()

__all__ = ["skill_registry"] 