#!/usr/bin/env python3
"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

# -*- coding: utf-8 -*-
"""
Basic Receptionist Transfer Agent Example

This example demonstrates creating a receptionist agent that:
1. Greets callers
2. Collects basic information about their needs
3. Transfers them to the appropriate department
"""

import os
import sys
import json
from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult

class ReceptionistAgent(AgentBase):
    """
    A basic receptionist agent that can transfer callers to the appropriate department
    """
    
    def __init__(
        self, 
        name="receptionist",
        route="/receptionist",
        **kwargs
    ):
        """
        Initialize the receptionist agent
        
        Args:
            name: Agent name for the route
            route: HTTP route for this agent
            **kwargs: Additional arguments for AgentBase
        """
        # Initialize the base agent
        super().__init__(
            name=name,
            route=route,
            use_pom=True,
            **kwargs
        )
        
        # Build the prompt
        self._build_prompt()
        
        # Configure agent settings
        self._configure_agent_settings()
        
        # Define available departments
        self.set_global_data({
            "departments": [
                {"name": "sales", "description": "For product inquiries, pricing, and purchasing"},
                {"name": "support", "description": "For technical help and troubleshooting"},
                {"name": "billing", "description": "For invoice questions and payment issues"},
                {"name": "general", "description": "For all other inquiries"}
            ],
            "caller_info": {}
        })
        
    def _build_prompt(self):
        """Build the agent's prompt with personality, goals, and instructions"""
        
        # Set personality
        self.prompt_add_section(
            "Personality", 
            body="You are a friendly and professional receptionist. You speak clearly and efficiently while maintaining a warm, helpful tone."
        )
        
        # Set goal
        self.prompt_add_section(
            "Goal", 
            body="Your goal is to greet callers, collect their basic information, and transfer them to the appropriate department."
        )
        
        # Set instructions
        self.prompt_add_section(
            "Instructions", 
            bullets=[
                "Begin by greeting the caller and asking how you can help them.",
                "Collect their name and a brief description of their needs.",
                "Based on their needs, determine which department would be most appropriate.",
                "Use the collect_caller_info function when you have their name and reason for calling.",
                "Use the transfer_call function to transfer them to the appropriate department.",
                "Before transferring, always confirm with the caller that they're being transferred to the right department.",
                "If a caller's request doesn't clearly match a department, ask follow-up questions to clarify."
            ]
        )
        
        # Add a post-prompt for summary generation
        self.set_post_prompt("""
        Return a JSON summary of the conversation:
        {
            "caller_name": "CALLER'S NAME",
            "reason": "REASON FOR CALLING",
            "department": "DEPARTMENT TRANSFERRED TO",
            "satisfaction": "high/medium/low (estimated caller satisfaction)"
        }
        """)
        
    def _configure_agent_settings(self):
        """Configure additional agent settings"""
        
        # Set AI behavior parameters
        self.set_params({
            "end_of_speech_timeout": 700,
            "speech_event_timeout": 1000,
            "transfer_summary": True  # Enable call summary transfer between agents
        })
        
        # Set English language with voice
        self.add_language(
            name="English",
            code="en-US",
            voice="elevenlabs.josh",
            speech_fillers=["Let me get that information for you...", "One moment please..."],
            function_fillers=["I'm processing that...", "Let me check which department can help you best..."]
        )
        
    @AgentBase.tool(
        name="collect_caller_info",
        description="Collect the caller's information for routing",
        parameters={
            "name": {
                "type": "string",
                "description": "The caller's name"
            },
            "reason": {
                "type": "string",
                "description": "The reason for the call"
            }
        }
    )
    def collect_caller_info(self, args, raw_data):
        """
        Collect and store the caller's information
        
        Args:
            args: The arguments from the SWAIG function call
            raw_data: Raw data from the request
            
        Returns:
            SwaigFunctionResult with confirmation and updated global data
        """
        # Get the caller info
        name = args.get("name", "")
        reason = args.get("reason", "")
        
        # Create response with global data update
        result = SwaigFunctionResult(
            f"Thank you, {name}. I've noted that you're calling about {reason}."
        )
        
        # Update global data with caller info
        result.add_actions([
            {"set_global_data": {
                "caller_info": {
                    "name": name,
                    "reason": reason
                }
            }}
        ])
        
        return result
    
    @AgentBase.tool(
        name="transfer_call",
        description="Transfer the caller to the appropriate department",
        parameters={
            "department": {
                "type": "string",
                "description": "The department to transfer to (sales, support, billing, or general)",
                "enum": ["sales", "support", "billing", "general"]
            }
        }
    )
    def transfer_call(self, args, raw_data):
        """
        Transfer the call to the specified department
        
        Args:
            args: The arguments from the SWAIG function call
            raw_data: Raw data from the request
            
        Returns:
            SwaigFunctionResult with SWML for call transfer
        """
        # Get the department
        department = args.get("department", "general")
        
        # Get global data
        global_data = raw_data.get("global_data", {})
        caller_info = global_data.get("caller_info", {})
        name = caller_info.get("name", "the caller")
        
        # Department transfer details (in a real system, these would be actual numbers)
        transfer_numbers = {
            "sales": "+15551235555",
            "support": "+15551236666",
            "billing": "+15551237777",
            "general": "+15551238888"
        }
        
        # Get transfer number (default to general)
        transfer_number = transfer_numbers.get(department, transfer_numbers["general"])
        
        # Create message for caller
        message = f"I'll transfer you to our {department} department now. Thank you for calling, {name}!"
        
        # Create result with transfer SWML
        result = SwaigFunctionResult(message)
        
        # Add the SWML to execute the transfer
        result.add_swml([
            {
                "play": {
                    "url": f"say:{message}"
                }
            },
            {
                "connect": {
                    "to": transfer_number
                }
            }
        ])
        
        return result
    
    def on_summary(self, summary, raw_data=None):
        """
        Process the conversation summary
        
        Args:
            summary: Summary data from the conversation
            raw_data: The complete raw POST data from the request
        """
        # In a real system, you might log this to a CRM or tracking system
        if summary:
            print(f"Call Summary: {json.dumps(summary, indent=2)}")
        
        # You could also get data from global_data
        if raw_data and "global_data" in raw_data:
            global_data = raw_data.get("global_data", {})
            caller_info = global_data.get("caller_info", {})
            print(f"Caller Information: {json.dumps(caller_info, indent=2)}")


def main():
    """Run the Receptionist Agent example"""
    
    # Create an agent
    agent = ReceptionistAgent()
    
    # Get basic auth credentials for display
    username, password = agent.get_basic_auth_credentials()
    
    # Print information about the agent
    print("Starting the Receptionist Agent")
    print("----------------------------------------")
    print(f"URL: http://localhost:3000{agent.route}")
    print(f"Basic Auth: {username}:{password}")
    print("----------------------------------------")
    print("Press Ctrl+C to stop the agent")
    
    # Start the agent server
    agent.serve()

if __name__ == "__main__":
    main() 