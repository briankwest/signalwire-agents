#!/usr/bin/env python3
"""
AWS Lambda deployment example for SignalWire AI Agents

This example shows how to deploy a SignalWire AI Agent to AWS Lambda using Mangum.
Mangum is included in requirements.txt, so no additional installation is needed.

Requirements:
    - signalwire-agents (includes mangum>=0.19.0)

Usage:
    1. Deploy this file to AWS Lambda
    2. Configure API Gateway to route all requests to this function  
    3. Set environment variables:
       - SWML_BASIC_AUTH_USER (optional, defaults to 'dev')
       - SWML_BASIC_AUTH_PASSWORD (optional, defaults to 'w00t')

Features:
    - Full SignalWire AI agent functionality in serverless
    - Same routing, authentication, SWAIG functions as regular deployment
    - Health checks work (/health, /ready)
    - Structured logging compatible with CloudWatch
    - Environment-based configuration
"""

import os
import sys

# Add the signalwire_agents module to the path if needed
# (not needed if installed via pip)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from signalwire_agents import AgentBase

# Import Mangum for Lambda/API Gateway integration
try:
    from mangum import Mangum
except ImportError:
    print("ERROR: Mangum not installed. Run: pip install mangum")
    sys.exit(1)


class HealthCheckAgent(AgentBase):
    """
    Example agent for Lambda deployment
    
    This agent demonstrates all the standard AgentBase features:
    - SWAIG functions
    - Basic auth
    - Health endpoints
    - Structured logging
    """
    
    def initialize(self):
        # Add some SWAIG functions
        self.add_function("greet_user", self.greet_user)
        self.add_function("get_time", self.get_time)
        self.add_function("health_status", self.health_status)
        
    def get_prompt(self):
        return """You are a helpful AI assistant running in AWS Lambda.
        
You have access to these functions:
- greet_user: Greet a user by name
- get_time: Get the current time
- health_status: Check the system health

Always be friendly and helpful!"""
    
    def greet_user(self, name: str = "friend"):
        """
        Greet a user by name
        
        Args:
            name: Name of the user to greet
        """
        return f"Hello {name}! I'm running in AWS Lambda!"
    
    def get_time(self):
        """Get the current time"""
        import datetime
        return f"Current time: {datetime.datetime.now().isoformat()}"
    
    def health_status(self):
        """Check the health status of the Lambda function"""
        return {
            "status": "healthy",
            "platform": "AWS Lambda",
            "agent": self.get_name(),
            "functions": len(self._swaig_functions)
        }


# Create the agent instance
# This works exactly the same as local development!
agent = HealthCheckAgent(
    name="lambda-agent",
    route="/",  # Lambda usually serves from root
)

# Get the FastAPI app from the agent
app = agent.get_app()

# Create the Lambda handler using Mangum
# This handles all the API Gateway <-> FastAPI translation
handler = Mangum(app)

def lambda_handler(event, context):
    """
    AWS Lambda entry point
    
    This function receives API Gateway events and returns responses.
    Mangum handles all the translation between Lambda/API Gateway format
    and FastAPI's expected format.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        dict: API Gateway response format
    """
    return handler(event, context)


# For local testing (optional)
if __name__ == "__main__":
    print("TESTING: Testing Lambda agent locally...")
    print("NOTE: This runs FastAPI directly, not via Lambda")
    print()
    
    # Run locally for testing (same as agent.serve())
    agent.serve(host="0.0.0.0", port=8080) 