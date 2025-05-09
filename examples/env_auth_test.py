#!/usr/bin/env python3
"""
Test script to verify environment variable authentication
"""

import os
import sys
from datetime import datetime

# Add the parent directory to the path so we can import the package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult

# Set environment variables programmatically for testing ONLY if not already set
if not os.environ.get('SWML_BASIC_AUTH_USER'):
    os.environ['SWML_BASIC_AUTH_USER'] = 'test_user'
    print(f"Setting default SWML_BASIC_AUTH_USER: test_user")

if not os.environ.get('SWML_BASIC_AUTH_PASSWORD'):
    os.environ['SWML_BASIC_AUTH_PASSWORD'] = 'test_password'
    print(f"Setting default SWML_BASIC_AUTH_PASSWORD: test_password")

print(f"Environment variables:")
print(f"SWML_BASIC_AUTH_USER: {os.environ.get('SWML_BASIC_AUTH_USER')}")
print(f"SWML_BASIC_AUTH_PASSWORD: {os.environ.get('SWML_BASIC_AUTH_PASSWORD')}")
print("-" * 50)

class SimpleTestAgent(AgentBase):
    """
    A minimal agent for testing environment variable authentication
    """
    
    # Define prompt structure declaratively
    PROMPT_SECTIONS = {
        "Personality": "Test agent for environment variables"
    }
    
    def __init__(self):
        # Initialize the agent
        super().__init__(
            name="env_test",
            route="/test",
            host="0.0.0.0",
            port=3000
        )

if __name__ == "__main__":
    agent = SimpleTestAgent()
    print("\nAgent initialized.")
    print("-" * 50)
    
    username, password, source = agent.get_basic_auth_credentials(include_source=True)
    print(f"Final credentials from agent object:")
    print(f"Username: {username}")
    print(f"Password: {password}")
    print(f"Source: {source}")
    
    if source == "environment":
        print("✅ SUCCESS: Environment variables are being used correctly.")
    else:
        print(f"❌ FAILURE: Credentials are coming from '{source}' instead of environment variables.")
    
    print("\nStarting server to verify printed credentials...")
    try:
        agent.serve()
    except KeyboardInterrupt:
        print("\nServer stopped.") 