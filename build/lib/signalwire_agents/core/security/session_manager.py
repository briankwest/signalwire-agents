"""
Session manager for handling call sessions and security tokens
"""

from typing import Dict, Any, Optional, Tuple
import secrets
import time
from datetime import datetime


class CallSession:
    """
    Represents a single call session with associated tokens and state
    """
    def __init__(self, call_id: str):
        self.call_id = call_id
        self.tokens: Dict[str, str] = {}  # function_name -> token
        self.state = "pending"  # pending, active, expired
        self.started_at = datetime.now()
        self.metadata: Dict[str, Any] = {}  # Custom state for the call


class SessionManager:
    """
    Manages call sessions and their associated security tokens
    """
    def __init__(self, token_expiry_secs: int = 600):
        """
        Initialize the session manager
        
        Args:
            token_expiry_secs: Seconds until tokens expire (default: 10 minutes)
        """
        self._active_calls: Dict[str, CallSession] = {}
        self.token_expiry_secs = token_expiry_secs
    
    def create_session(self, call_id: Optional[str] = None) -> str:
        """
        Create a new call session
        
        Args:
            call_id: Optional call ID, generated if not provided
            
        Returns:
            The call_id for the new session
        """
        # Generate call_id if not provided
        if not call_id:
            call_id = secrets.token_urlsafe(16)
        
        # Create new session
        self._active_calls[call_id] = CallSession(call_id)
        return call_id
    
    def generate_token(self, function_name: str, call_id: str) -> str:
        """
        Generate a secure token for a function call
        
        Args:
            function_name: Name of the function to generate a token for
            call_id: Call session ID
            
        Returns:
            A secure random token
            
        Raises:
            ValueError: If the call session does not exist
        """
        if call_id not in self._active_calls:
            raise ValueError(f"No active session for call_id: {call_id}")
        
        token = secrets.token_urlsafe(24)
        self._active_calls[call_id].tokens[function_name] = token
        return token
    
    def validate_token(self, call_id: str, function_name: str, token: str) -> bool:
        """
        Validate a function call token
        
        Args:
            call_id: Call session ID
            function_name: Name of the function being called
            token: Token to validate
            
        Returns:
            True if valid, False otherwise
        """
        session = self._active_calls.get(call_id)
        if not session or session.state != "active":
            return False
        
        # Check if token matches and is not expired
        expected_token = session.tokens.get(function_name)
        if not expected_token or expected_token != token:
            return False
            
        # Check expiry
        now = datetime.now()
        seconds_elapsed = (now - session.started_at).total_seconds()
        if seconds_elapsed > self.token_expiry_secs:
            session.state = "expired"
            return False
            
        return True
    
    def activate_session(self, call_id: str) -> bool:
        """
        Activate a call session (called by startup_hook)
        
        Args:
            call_id: Call session ID
            
        Returns:
            True if successful, False otherwise
        """
        session = self._active_calls.get(call_id)
        if not session:
            return False
            
        session.state = "active"
        return True
    
    def end_session(self, call_id: str) -> bool:
        """
        End a call session (called by hangup_hook)
        
        Args:
            call_id: Call session ID
            
        Returns:
            True if successful, False otherwise
        """
        if call_id in self._active_calls:
            del self._active_calls[call_id]
            return True
        return False
    
    def get_session_metadata(self, call_id: str) -> Optional[Dict[str, Any]]:
        """
        Get custom metadata for a call session
        
        Args:
            call_id: Call session ID
            
        Returns:
            Metadata dict or None if session not found
        """
        session = self._active_calls.get(call_id)
        if not session:
            return None
        return session.metadata
    
    def set_session_metadata(self, call_id: str, key: str, value: Any) -> bool:
        """
        Set custom metadata for a call session
        
        Args:
            call_id: Call session ID
            key: Metadata key
            value: Metadata value
            
        Returns:
            True if successful, False otherwise
        """
        session = self._active_calls.get(call_id)
        if not session:
            return False
            
        session.metadata[key] = value
        return True
