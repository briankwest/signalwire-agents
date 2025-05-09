#!/usr/bin/env python3
"""
Simple example of using the SignalWire AI Agent SDK
"""

import os
import sys
from datetime import datetime

# Add the parent directory to the path so we can import the package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult


class SimpleAgent(AgentBase):
    """
    A simple agent that demonstrates the basic functionality of the SDK
    """
    
    def __init__(self):
        # Initialize the agent with a name and route
        super().__init__(
            name="simple",
            route="/simple",
            host="0.0.0.0",
            port=3000
        )
        
        # Build the prompt using POM structure
        self.set_personality("You are a friendly and helpful assistant.")
        self.set_goal("Help users with basic tasks and answer questions.")
        
        # Add instructions
        self.add_instruction("Be concise and direct in your responses.")
        self.add_instruction("If you don't know something, say so clearly.")
        self.add_instruction("Use the get_time function when asked about the current time.")
        
        # Add example interactions
        self.add_example(
            "Time request",
            "User: What time is it?\nAssistant: Let me check for you. [call get_time]"
        )
        
        # Add a post-prompt for summary
        self.set_post_prompt("""
        Return a JSON summary of the conversation:
        {
            "topic": "MAIN_TOPIC",
            "satisfied": true/false,
            "follow_up_needed": true/false
        }
        """)
    
    @AgentBase.tool(
        name="get_time",
        description="Get the current time",
        parameters={}
    )
    def get_time(self):
        """Get the current time"""
        now = datetime.now()
        formatted_time = now.strftime("%H:%M:%S")
        return SwaigFunctionResult(f"The current time is {formatted_time}")
    
    @AgentBase.tool(
        name="get_weather",
        description="Get the current weather for a location",
        parameters={
            "location": {
                "type": "string",
                "description": "The city or location to get weather for"
            }
        }
    )
    def get_weather(self, location):
        """Get the current weather for a location"""
        # In a real implementation, this would call a weather API
        return SwaigFunctionResult(f"It's sunny and 72°F in {location}.")
    
    def on_summary(self, summary):
        """Handle the conversation summary"""
        print(f"Conversation summary received: {summary}")


if __name__ == "__main__":
    # Create and start the agent
    agent = SimpleAgent()
    print("Starting the agent. Press Ctrl+C to stop.")
    
    try:
        agent.serve()
    except KeyboardInterrupt:
        print("\nStopping the agent.")
        agent.stop() 