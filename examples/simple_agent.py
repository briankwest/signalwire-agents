#!/usr/bin/env python3
"""
Simple example of using the SignalWire AI Agent SDK

This example demonstrates three different approaches to building agent prompts:

1. SimpleAgent - Uses the declarative PROMPT_SECTIONS class attribute
   This is the most concise and recommended approach for most use cases.
   
2. SimpleAgentWithRawPrompt - Uses raw text prompt
   This approach is good for migrating existing prompts or when you don't
   need the structure of POM.
   
3. SimpleAgentWithProgrammaticPOM - Uses programmatic POM API
   This approach gives you the most control and allows for dynamic
   prompt generation based on runtime conditions.
   
All three approaches produce equivalent agents with the same functionality.
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
    
    # Define the prompt sections declaratively
    PROMPT_SECTIONS = {
        "Personality": "You are a friendly and helpful assistant.",
        "Goal": "Help users with basic tasks and answer questions.",
        "Instructions": [
            "Be concise and direct in your responses.",
            "If you don't know something, say so clearly.",
            "Use the get_time function when asked about the current time."
        ],
        "Examples": {
            "subsections": [
                {
                    "title": "Time request",
                    "body": "User: What time is it?\nAssistant: Let me check for you. [call get_time]"
                }
            ]
        }
    }
    
    def __init__(self):
        # Initialize the agent with a name and route
        super().__init__(
            name="simple",
            route="/simple",
            host="0.0.0.0",
            port=3000
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
    def get_time(self, args=None):
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
    def get_weather(self, args, raw_data=None):
        """Get the current weather for a location"""
        # Extract location from the args dictionary 
        location = args.get("location", "Unknown location")
        
        # Log the full raw POST data for debugging (optional)
        print(f"DEBUG: Full POST data received: {raw_data}")
        
        # Access other parts of the raw request if needed
        # For example: call_id = raw_data.get("call_id") if raw_data else None
        
        # In a real implementation, this would call a weather API
        return SwaigFunctionResult(f"It's sunny and 72°F in {location}.")
    
    def on_summary(self, summary):
        """Handle the conversation summary"""
        print(f"Conversation summary received: {summary}")


class SimpleAgentWithRawPrompt(AgentBase):
    """
    A simple agent that demonstrates using raw text prompt
    instead of structured prompt sections
    """
    
    def __init__(self):
        # Initialize the agent with a name and route
        super().__init__(
            name="simple_raw",
            route="/simple_raw",
            host="0.0.0.0",
            port=3001
        )
        
        # Set raw text prompt directly
        self.set_prompt_text("""
        You are a friendly and helpful assistant.
        
        Your goal is to help users with basic tasks and answer questions.
        
        Instructions:
        - Be concise and direct in your responses.
        - If you don't know something, say so clearly.
        - Use the get_time function when asked about the current time.
        
        Example: Time request
        User: What time is it?
        Assistant: Let me check for you. [call get_time]
        """)
        
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
    def get_time(self, args=None):
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
    def get_weather(self, args, raw_data=None):
        """Get the current weather for a location"""
        # Extract location from the args dictionary 
        location = args.get("location", "Unknown location")
        
        # Log the full raw POST data for debugging (optional)
        print(f"DEBUG: Full POST data received: {raw_data}")
        
        # Access other parts of the raw request if needed
        # For example: call_id = raw_data.get("call_id") if raw_data else None
        
        # In a real implementation, this would call a weather API
        return SwaigFunctionResult(f"It's sunny and 72°F in {location}.")
    
    def on_summary(self, summary):
        """Handle the conversation summary"""
        print(f"Conversation summary received: {summary}")


class SimpleAgentWithProgrammaticPOM(AgentBase):
    """
    A simple agent that demonstrates building a prompt programmatically
    using the POM API
    """
    
    def __init__(self):
        # Initialize the agent with a name and route
        super().__init__(
            name="simple_pom",
            route="/simple_pom",
            host="0.0.0.0",
            port=3002
        )
        
        # Build the prompt programmatically using POM methods
        self.prompt_add_section(
            "Personality", 
            body="You are a friendly and helpful assistant."
        )
        
        self.prompt_add_section(
            "Goal", 
            body="Help users with basic tasks and answer questions."
        )
        
        # Add a section with bullet points
        self.prompt_add_section(
            "Instructions", 
            bullets=[
                "Be concise and direct in your responses.",
                "If you don't know something, say so clearly.",
                "Use the get_time function when asked about the current time."
            ]
        )
        
        # Add a section with subsections
        self.prompt_add_section("Examples")
        self.prompt_add_subsection(
            "Examples",
            "Time request", 
            body="User: What time is it?\nAssistant: Let me check for you. [call get_time]"
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
    def get_time(self, args=None):
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
    def get_weather(self, args, raw_data=None):
        """Get the current weather for a location"""
        # Extract location from the args dictionary 
        location = args.get("location", "Unknown location")
        
        # Log the full raw POST data for debugging (optional)
        print(f"DEBUG: Full POST data received: {raw_data}")
        
        # Access other parts of the raw request if needed
        # For example: call_id = raw_data.get("call_id") if raw_data else None
        
        # In a real implementation, this would call a weather API
        return SwaigFunctionResult(f"It's sunny and 72°F in {location}.")
    
    def on_summary(self, summary):
        """Handle the conversation summary"""
        print(f"Conversation summary received: {summary}")


if __name__ == "__main__":
    # Choose which agent to run:
    agent = SimpleAgent()  # Declarative approach
    # agent = SimpleAgentWithRawPrompt()  # Raw text approach
    # agent = SimpleAgentWithProgrammaticPOM()  # Programmatic POM approach
    
    print("Starting the agent. Press Ctrl+C to stop.")
    
    try:
        agent.serve()
    except KeyboardInterrupt:
        print("\nStopping the agent.")
        agent.stop() 