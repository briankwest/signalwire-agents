#!/usr/bin/env python3
"""
Example of using the AgentServer with multiple prefab agents

This example demonstrates how to:
1. Set up a single server hosting multiple AI agents
2. Create custom extensions of prefab agents
3. Configure SIP routing for voice calls to different agents
4. Map multiple SIP usernames to specific agents
"""

import os
import sys
import json
from datetime import datetime

# Add the parent directory to the path so we can import the package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signalwire_agents import AgentServer
from signalwire_agents.prefabs import InfoGathererAgent
from signalwire_agents.core.function_result import SwaigFunctionResult


class CustomInfoGatherer(InfoGathererAgent):
    """
    Custom information gatherer that adds a save_info tool
    and overrides on_summary to do something with the collected data
    
    This demonstrates how to extend a prefab agent with:
    1. Custom SWAIG functions to perform additional actions
    2. Custom summary handling to process collected information
    3. Action integration (SMS sending) as part of the agent response
    """
    
    def __init__(self):
        #------------------------------------------------------------------------
        # PREFAB CONFIGURATION
        # Configure the base InfoGathererAgent with our specific requirements
        #------------------------------------------------------------------------
        
        # Initialize with field definitions
        # The InfoGathererAgent prefab will automatically create an agent that:
        # - Collects these specific pieces of information
        # - Validates that the data matches required formats
        # - Handles clarifications and corrections
        # - Provides a confirmation once all data is collected
        super().__init__(
            name="registration",           # Agent identifier and logging name
            route="/register",             # HTTP endpoint path
            fields=[                       # Information to collect
                {"name": "full_name", "prompt": "What is your full name?"},
                {"name": "email", "prompt": "What is your email address?"},
                {"name": "phone", "prompt": "What is your phone number?"}
            ],
            # Template uses {field_name} to insert collected data
            confirmation_template="Thanks {full_name}! We've recorded your contact info: {email} and {phone}."
        )
        
        #------------------------------------------------------------------------
        # CUSTOM TOOL DEFINITION
        # Add additional capabilities not included in the base prefab
        #------------------------------------------------------------------------
        
        # Add a tool for saving info to CRM
        # This is a custom extension not part of the base InfoGathererAgent
        self.define_tool(
            name="save_to_crm",           # Function name the AI will use
            description="Save customer information to the CRM system",  # Description for the AI
            parameters={                   # Parameter schema
                "name": {"type": "string", "description": "Customer name"},
                "email": {"type": "string", "description": "Customer email"},
                "phone": {"type": "string", "description": "Customer phone"}
            },
            handler=self.save_to_crm       # Method to call when the function is invoked
        )
    
    def save_to_crm(self, args, raw_data):
        """
        Tool handler for saving info to CRM
        
        This function demonstrates how to:
        1. Process collected information
        2. Integrate with external systems
        3. Return actions that trigger additional behaviors
        
        Args:
            args: Dictionary with name, email, and phone parameters
            raw_data: Complete request data
            
        Returns:
            SwaigFunctionResult with confirmation and SMS action
        """
        # Extract parameters from the args dictionary
        name = args.get("name", "")
        email = args.get("email", "")
        phone = args.get("phone", "")
        
        print(f"Saving to CRM: {name}, {email}, {phone}")
        
        # Simulate CRM save by writing to a local file
        # In a real implementation, this would call a CRM API
        with open("customer_data.json", "a") as f:
            f.write(json.dumps({
                "name": name,
                "email": email,
                "phone": phone,
                "timestamp": datetime.now().isoformat()
            }) + "\n")
        
        # Return success response with an additional action
        # This demonstrates how to trigger SMS sending as part of the function result
        return (
            SwaigFunctionResult("I've saved your information to our system.")
            .add_action("send_sms", 
                       {"to": phone,                # Phone number to send to
                       "message": f"Thanks {name} for registering!"})  # SMS content
        )
    
    def on_summary(self, summary, raw_data=None):
        """
        Process the conversation summary data
        
        This method is called after all information has been collected and the post-prompt
        has generated a summary. It allows for final processing of the data.
        
        Args:
            summary: JSON structure containing the collected information
            raw_data: Complete request data
        """
        print(f"Registration completed: {json.dumps(summary, indent=2)}")
        
        # Additional processing could happen here
        # For example:
        # - Saving to a database
        # - Sending confirmation emails
        # - Triggering workflow events


class SupportInfoGatherer(InfoGathererAgent):
    """
    Support ticket information gatherer
    
    This agent demonstrates:
    1. Using validation rules in field definitions
    2. Customizing the structure of the summary data
    3. Simple processing of submitted support tickets
    """
    
    def __init__(self):
        #------------------------------------------------------------------------
        # PREFAB CONFIGURATION
        # Configure the InfoGathererAgent for support ticket collection
        #------------------------------------------------------------------------
        
        # Initialize with ticket field definitions
        super().__init__(
            name="support",
            route="/support",
            fields=[
                {"name": "name", "prompt": "What is your name?"},
                {"name": "issue", "prompt": "Please describe the issue you're experiencing."},
                # This field includes validation to ensure the value is a number between 1-5
                {"name": "urgency", "prompt": "On a scale of 1-5, how urgent is this issue?", 
                 "validation": "Must be a number between 1 and 5"}
            ],
            confirmation_template="Thanks {name}. We've recorded your {urgency}-priority issue and will respond soon.",
            # Define a custom structure for the summary data
            # The %{field_name} syntax inserts the collected data into the specified structure
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
    
    def on_summary(self, summary, raw_data=None):
        """
        Process the ticket data after collection is complete
        
        This method is called when the conversation has ended
        and all required information has been collected.
        
        Args:
            summary: The structured ticket data as configured in summary_format
            raw_data: Complete request data
        """
        print(f"Support ticket created: {json.dumps(summary, indent=2)}")
        
        # In a real implementation, you might:
        # - Create a ticket in a ticketing system
        # - Send a notification to support staff
        # - Add the ticket to a queue based on priority


def main():
    """
    Run the multi-agent server
    
    This function:
    1. Creates an AgentServer instance
    2. Creates and registers multiple agents
    3. Configures SIP routing
    4. Starts the server
    """
    #------------------------------------------------------------------------
    # SERVER INITIALIZATION
    # Create the AgentServer to host multiple agents
    #------------------------------------------------------------------------
    
    # Create the server that will host all our agents
    # AgentServer provides a single FastAPI application that can host
    # multiple agents on different routes
    server = AgentServer(host="0.0.0.0", port=3000)
    
    #------------------------------------------------------------------------
    # AGENT REGISTRATION
    # Create and register different agent types
    #------------------------------------------------------------------------
    
    # Create agent instances
    registration_agent = CustomInfoGatherer()  # Registration agent
    support_agent = SupportInfoGatherer()      # Support agent
    
    # Register them with the server
    # The server will use each agent's route to determine the URL path
    server.register(registration_agent)  # Uses /register from the agent
    server.register(support_agent)       # Uses /support from the agent
    
    #------------------------------------------------------------------------
    # SIP ROUTING CONFIGURATION
    # Configure voice call routing to the appropriate agents
    #------------------------------------------------------------------------
    
    # Set up SIP routing on the /sip endpoint
    # auto_map=True creates default SIP mappings based on agent names
    # This means voice calls to "registration@domain" will route to the registration agent
    # and calls to "support@domain" will route to the support agent
    server.setup_sip_routing(route="/sip", auto_map=True)
    
    # Register additional SIP username mappings for alternative names
    # These let callers use multiple usernames to reach the same agent
    server.register_sip_username("register", "/register")  # register@domain → registration agent
    server.register_sip_username("signup", "/register")    # signup@domain → registration agent
    server.register_sip_username("help", "/support")       # help@domain → support agent
    
    #------------------------------------------------------------------------
    # SERVER STARTUP
    # Print info and start the server
    #------------------------------------------------------------------------
    
    # Print information about the available endpoints
    # The /health endpoint is automatically added by AgentServer
    print("Starting multi-agent server with the following agents:")
    print("- Registration agent at /register")
    print("- Support agent at /support")
    print("- Health check at /health")
    print("- SIP routing at /sip")
    print("\nThe following SIP usernames are registered:")
    print("- 'registration' or 'register' or 'signup' → Registration agent")
    print("- 'support' or 'help' → Support agent")
    
    # Start the server with the configured agents
    # This runs uvicorn with the FastAPI application
    try:
        server.run()
    except KeyboardInterrupt:
        print("\nShutting down server.")


if __name__ == "__main__":
    main() 