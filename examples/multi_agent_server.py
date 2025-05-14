#!/usr/bin/env python3
"""
Example of using the AgentServer with multiple prefab agents
"""

import os
import sys
import json
from datetime import datetime

# Add the parent directory to the path so we can import the package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signalwire_agents import AgentServer
from signalwire_agents.prefabs import InfoGathererAgent
from signalwire_agents.core.function_result import SwaigFunctionResult, SwaigActionTypes


class CustomInfoGatherer(InfoGathererAgent):
    """
    Custom information gatherer that adds a save_info tool
    and overrides on_summary to do something with the collected data
    """
    
    def __init__(self):
        # Initialize with field definitions
        super().__init__(
            name="registration",
            route="/register",
            fields=[
                {"name": "full_name", "prompt": "What is your full name?"},
                {"name": "email", "prompt": "What is your email address?"},
                {"name": "phone", "prompt": "What is your phone number?"}
            ],
            confirmation_template="Thanks {full_name}! We've recorded your contact info: {email} and {phone}."
        )
        
        # Add a tool for saving info to CRM
        self.define_tool(
            name="save_to_crm",
            description="Save customer information to the CRM system",
            parameters={
                "name": {"type": "string", "description": "Customer name"},
                "email": {"type": "string", "description": "Customer email"},
                "phone": {"type": "string", "description": "Customer phone"}
            },
            handler=self.save_to_crm
        )
    
    def save_to_crm(self, name, email, phone):
        """
        Tool handler for saving info to CRM
        
        In a real implementation, this would call a CRM API
        """
        print(f"Saving to CRM: {name}, {email}, {phone}")
        
        # Simulate CRM save
        with open("customer_data.json", "a") as f:
            f.write(json.dumps({
                "name": name,
                "email": email,
                "phone": phone,
                "timestamp": datetime.now().isoformat()
            }) + "\n")
        
        # Return success response
        return (
            SwaigFunctionResult("I've saved your information to our system.")
            .add_action(SwaigActionTypes.SEND_SMS, 
                       to=phone, 
                       message=f"Thanks {name} for registering!")
        )
    
    def on_summary(self, summary):
        """Override to do something with the collected data"""
        print(f"Registration completed: {json.dumps(summary, indent=2)}")
        
        # Additional processing could happen here


class SupportInfoGatherer(InfoGathererAgent):
    """
    Support ticket information gatherer
    """
    
    def __init__(self):
        # Initialize with ticket field definitions
        super().__init__(
            name="support",
            route="/support",
            fields=[
                {"name": "name", "prompt": "What is your name?"},
                {"name": "issue", "prompt": "Please describe the issue you're experiencing."},
                {"name": "urgency", "prompt": "On a scale of 1-5, how urgent is this issue?", 
                 "validation": "Must be a number between 1 and 5"}
            ],
            confirmation_template="Thanks {name}. We've recorded your {urgency}-priority issue and will respond soon.",
            summary_format={
                "customer": {
                    "name": "%{name}"
                },
                "ticket": {
                    "description": "%{issue}",
                    "priority": "%{urgency}"
                }
            }
        )
    
    def on_summary(self, summary):
        """Handle the ticket data"""
        print(f"Support ticket created: {json.dumps(summary, indent=2)}")


def main():
    """Run the multi-agent server"""
    # Create the server
    server = AgentServer(host="0.0.0.0", port=3000)
    
    # Create and register agents
    registration_agent = CustomInfoGatherer()
    support_agent = SupportInfoGatherer()
    
    # Register them with the server
    server.register(registration_agent)  # Uses /register from the agent
    server.register(support_agent)       # Uses /support from the agent
    
    # Set up SIP routing
    server.setup_sip_routing(route="/sip", auto_map=True)
    
    # Register custom SIP username mappings
    server.register_sip_username("register", "/register")
    server.register_sip_username("signup", "/register")
    server.register_sip_username("help", "/support")
    
    # Add a health check endpoint (built into AgentServer)
    print("Starting multi-agent server with the following agents:")
    print("- Registration agent at /register")
    print("- Support agent at /support")
    print("- Health check at /health")
    print("- SIP routing at /sip")
    print("\nThe following SIP usernames are registered:")
    print("- 'registration' or 'register' or 'signup' → Registration agent")
    print("- 'support' or 'help' → Support agent")
    
    # Start the server
    try:
        server.run()
    except KeyboardInterrupt:
        print("\nShutting down server.")


if __name__ == "__main__":
    main() 