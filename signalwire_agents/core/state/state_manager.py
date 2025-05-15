"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

"""
Abstract base class for state management
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class StateManager(ABC):
    """
    Abstract base class for state management
    
    This defines the interface that all state manager implementations
    must follow. State managers are responsible for storing, retrieving,
    and managing call-specific state data.
    """
    
    @abstractmethod
    def store(self, call_id: str, data: Dict[str, Any]) -> bool:
        """
        Store state data for a call
        
        Args:
            call_id: Unique identifier for the call
            data: Dictionary of state data to store
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def retrieve(self, call_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve state data for a call
        
        Args:
            call_id: Unique identifier for the call
            
        Returns:
            Dictionary of state data or None if not found
        """
        pass
    
    @abstractmethod
    def update(self, call_id: str, data: Dict[str, Any]) -> bool:
        """
        Update state data for a call
        
        Args:
            call_id: Unique identifier for the call
            data: Dictionary of state data to update (merged with existing)
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def delete(self, call_id: str) -> bool:
        """
        Delete state data for a call
        
        Args:
            call_id: Unique identifier for the call
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def cleanup_expired(self) -> int:
        """
        Clean up expired state data
        
        Returns:
            Number of expired items cleaned up
        """
        pass
    
    def exists(self, call_id: str) -> bool:
        """
        Check if state exists for a call
        
        Args:
            call_id: Unique identifier for the call
            
        Returns:
            True if state exists, False otherwise
        """
        return self.retrieve(call_id) is not None 