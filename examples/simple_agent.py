#!/usr/bin/env python3
"""
Simple example of using the SignalWire AI Agent SDK

This example demonstrates creating an agent using explicit methods
to manipulate the POM (Prompt Object Model) structure directly.

Note: The SDK also supports these alternative approaches that are not shown here:
   
1. Raw text prompts: Using set_prompt_text() when you don't need structured prompts
   
2. Programmatic POM: Using prompt_add_section() and related methods when you need
   to build prompts dynamically at runtime
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
    A simple agent that demonstrates using explicit methods
    to manipulate the POM structure directly
    
    This example shows:
    
    1. How to create an agent with a structured prompt using POM
    2. How to define SWAIG functions that the AI can call
    3. How to return results from SWAIG functions
    
    SWAIG functions:
    - Are defined using the @AgentBase.tool decorator
    - Receive parameters in the 'args' dictionary
    - Can access the complete request data via 'raw_data' 
    - Return responses using SwaigFunctionResult
    - Can include optional actions in the response
    """
    
    def __init__(self):
        # Initialize the agent with a name and route
        super().__init__(
            name="simple",
            route="/simple",
            host="0.0.0.0",
            port=3000,
            use_pom=True  # Ensure we're using POM
        )
        
        # Initialize POM sections using explicit methods
        self.setPersonality("You are a friendly and helpful assistant.")
        self.setGoal("Help users with basic tasks and answer questions.")
        self.setInstructions([
            "Be concise and direct in your responses.",
            "If you don't know something, say so clearly.",
            "Use the get_time function when asked about the current time.",
            "Use the get_weather function when asked about the weather."
        ])
        
        # Add a post-prompt for summary
        self.set_post_prompt("""
        Return a JSON summary of the conversation:
        {
            "topic": "MAIN_TOPIC",
            "satisfied": true/false,
            "follow_up_needed": true/false
        }
        """)
    
    def setPersonality(self, personality_text):
        """Set the AI personality description"""
        self.pom.add_section("Personality", body=personality_text)
        return self
    
    def setGoal(self, goal_text):
        """Set the primary goal for the AI agent"""
        self.pom.add_section("Goal", body=goal_text)
        return self
    
    def setInstructions(self, instructions_list):
        """Set the list of instructions for the AI agent"""
        if instructions_list:
            self.pom.add_section("Instructions", bullets=instructions_list)
        return self
    
    @AgentBase.tool(
        name="get_time",
        description="Get the current time",
        parameters={}
    )
    def get_time(self, args, raw_data):
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
    def get_weather(self, args, raw_data):
        """
        Get the current weather for a location
        
        This SWAIG function is called by the AI when a user asks about weather.
        Parameters are passed in the args dictionary, while the complete request
        data is in raw_data. Authentication is handled via basic auth.
        
        Args:
            args: Dictionary containing parsed parameters (location)
            raw_data: Complete request data including call_id and other metadata
            
        Returns:
            SwaigFunctionResult containing the response text and optional actions
        """
        # Extract location from the args dictionary 
        location = args.get("location", "Unknown location")
        
        # Create the result with a response
        result = SwaigFunctionResult(f"It's sunny and 72°F in {location}.")
        
        # You could add actions if needed, examples:
        # Send a text message with the weather info
        # result.add_action("send_sms", {
        #     "to": "+1234567890",
        #     "message": f"Weather for {location}: Sunny, 72°F"
        # })
        
        # Or play a weather sound
        # result.add_action("play", f"https://example.com/sounds/sunny.wav")
        
        return result
    
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