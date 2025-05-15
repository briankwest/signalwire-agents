"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

"""
File-based implementation of the StateManager interface
"""

import os
import json
import tempfile
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from .state_manager import StateManager


class FileStateManager(StateManager):
    """
    File-based state manager implementation
    
    This implementation stores state data as JSON files in a directory.
    Each call's state is stored in a separate file named by call_id.
    Files older than expiry_days are automatically cleaned up.
    
    This is suitable for development and low-volume deployments.
    For production, consider using database or Redis implementations.
    """
    
    def __init__(
        self,
        storage_dir: Optional[str] = None,
        expiry_days: float = 1.0
    ):
        """
        Initialize the file state manager
        
        Args:
            storage_dir: Directory to store state files (default: system temp dir)
            expiry_days: Days after which state files are considered expired
        """
        self.storage_dir = storage_dir or os.path.join(tempfile.gettempdir(), "signalwire_state")
        self.expiry_days = expiry_days
        
        # Create storage directory if it doesn't exist
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
    
    def _get_file_path(self, call_id: str) -> str:
        """Get the file path for a call_id"""
        # Sanitize call_id to ensure it's safe for a filename
        sanitized_id = "".join(c for c in call_id if c.isalnum() or c in "-_.")
        return os.path.join(self.storage_dir, f"{sanitized_id}.json")
    
    def store(self, call_id: str, data: Dict[str, Any]) -> bool:
        """
        Store state data for a call
        
        Args:
            call_id: Unique identifier for the call
            data: Dictionary of state data to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add metadata including timestamp
            state_data = {
                "call_id": call_id,
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "data": data
            }
            
            file_path = self._get_file_path(call_id)
            with open(file_path, "w") as f:
                json.dump(state_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error storing state for call {call_id}: {e}")
            return False
    
    def retrieve(self, call_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve state data for a call
        
        Args:
            call_id: Unique identifier for the call
            
        Returns:
            Dictionary of state data or None if not found
        """
        file_path = self._get_file_path(call_id)
        if not os.path.exists(file_path):
            return None
            
        try:
            with open(file_path, "r") as f:
                state_data = json.load(f)
            
            # Check if the file is expired
            created_at = datetime.fromisoformat(state_data["created_at"])
            if (datetime.now() - created_at) > timedelta(days=self.expiry_days):
                # Expired, so delete it and return None
                os.remove(file_path)
                return None
                
            return state_data["data"]
        except Exception as e:
            print(f"Error retrieving state for call {call_id}: {e}")
            return None
    
    def update(self, call_id: str, data: Dict[str, Any]) -> bool:
        """
        Update state data for a call
        
        Args:
            call_id: Unique identifier for the call
            data: Dictionary of state data to update (merged with existing)
            
        Returns:
            True if successful, False otherwise
        """
        file_path = self._get_file_path(call_id)
        if not os.path.exists(file_path):
            # If no existing data, just store new data
            return self.store(call_id, data)
            
        try:
            # Read existing data
            with open(file_path, "r") as f:
                state_data = json.load(f)
                
            # Update the data (deep merge)
            existing_data = state_data["data"]
            self._deep_update(existing_data, data)
            
            # Update metadata
            state_data["last_updated"] = datetime.now().isoformat()
            state_data["data"] = existing_data
            
            # Write back to file
            with open(file_path, "w") as f:
                json.dump(state_data, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error updating state for call {call_id}: {e}")
            return False
    
    def delete(self, call_id: str) -> bool:
        """
        Delete state data for a call
        
        Args:
            call_id: Unique identifier for the call
            
        Returns:
            True if successful, False otherwise
        """
        file_path = self._get_file_path(call_id)
        if not os.path.exists(file_path):
            return False
            
        try:
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"Error deleting state for call {call_id}: {e}")
            return False
    
    def cleanup_expired(self) -> int:
        """
        Clean up expired state files
        
        Returns:
            Number of expired files cleaned up
        """
        count = 0
        try:
            # Get all state files
            for filename in os.listdir(self.storage_dir):
                if not filename.endswith(".json"):
                    continue
                    
                file_path = os.path.join(self.storage_dir, filename)
                
                try:
                    # Read the file to check creation time
                    with open(file_path, "r") as f:
                        state_data = json.load(f)
                        
                    # Check if the file is expired
                    created_at = datetime.fromisoformat(state_data["created_at"])
                    if (datetime.now() - created_at) > timedelta(days=self.expiry_days):
                        os.remove(file_path)
                        count += 1
                except Exception:
                    # Skip files that can't be processed
                    continue
                    
            return count
        except Exception as e:
            print(f"Error cleaning up expired state files: {e}")
            return count
    
    def _deep_update(self, d: Dict, u: Dict) -> None:
        """Recursively update a nested dictionary"""
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._deep_update(d[k], v)
            else:
                d[k] = v 