#!/usr/bin/env python3
"""
Declarative Agent Example

This example demonstrates how to create an agent using the declarative PROMPT_SECTIONS 
approach, which allows defining the entire prompt structure as a class attribute.
"""

import os
import sys
import json
from datetime import datetime

# Add the parent directory to the path so we can import the package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult


class DeclarativeAgent(AgentBase):
    """
    A simple agent defined using the declarative PROMPT_SECTIONS approach
    
    Instead of calling set_personality(), add_instruction(), etc. in __init__,
    we define the entire prompt structure as a class attribute.
    """
    
    # Define the entire prompt structure declaratively as a class attribute
    PROMPT_SECTIONS = {
        "Personality": "You are a friendly and helpful AI assistant who responds in a casual, conversational tone.",
        
        "Goal": "Help users with their questions about time and weather.",
        
        "Instructions": [
            "Be concise and direct in your responses.",
            "If you don't know something, say so clearly.",
            "Use the get_time function when asked about the current time.",
            "Use the get_weather function when asked about the weather."
        ],
        
        "Examples": {
            "body": "Here are examples of how to respond to common requests:",
            "subsections": [
                {
                    "title": "Time request",
                    "body": "User: What time is it?\nAssistant: Let me check for you. [call get_time]"
                },
                {
                    "title": "Weather request",
                    "body": "User: What's the weather like in Paris?\nAssistant: Let me check the weather for you. [call get_weather with {\"location\": \"Paris\"}]"
                }
            ]
        }
    }
    
    def __init__(self):
        # Initialize the agent with a name and route
        super().__init__(
            name="declarative",
            route="/declarative",
            host="0.0.0.0",
            port=3000
        )
        
        # Notice we don't need any prompt building calls here - they're handled
        # automatically by the declarative PROMPT_SECTIONS
        
        # Just add a post-prompt for summary
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
        """Get the current weather for a location"""
        # Extract location from the args dictionary
        location = args.get("location", "Unknown location")
        
        # In a real implementation, this would call a weather API
        return SwaigFunctionResult(f"It's sunny and 72°F in {location}.")
    
    def on_summary(self, summary):
        """Handle the conversation summary"""
        print(f"Conversation summary received: {json.dumps(summary, indent=2)}")


# Alternative example using the POM format directly
class PomFormatAgent(AgentBase):
    """
    An agent using the direct POM format for PROMPT_SECTIONS
    
    This approach uses the raw POM dictionary format directly.
    """
    
    # Define the prompt using the direct POM format (list of sections)
    PROMPT_SECTIONS = [
        {
            "title": "Assistant Role",
            "body": "You are a technical support agent for SignalWire products.",
            "numbered": True
        },
        {
            "title": "Knowledge Base",
            "bullets": [
                "You know about SignalWire Voice, Video, and Messaging APIs.",
                "You can help with SWML (SignalWire Markup Language) issues.",
                "You can provide code examples in Python, JavaScript, and Ruby."
            ]
        },
        {
            "title": "Response Format",
            "body": "When providing code examples, use markdown code blocks with the language specified.",
            "subsections": [
                {
                    "title": "Example Format",
                    "body": "```python\n# Python example\nfrom signalwire.rest import Client\n```"
                }
            ]
        }
    ]
    
    def __init__(self):
        super().__init__(
            name="pom_format",
            route="/pom_format",
            host="0.0.0.0",
            port=3001
        )


if __name__ == "__main__":
    # Create and start the agent
    agent = DeclarativeAgent()
    print("\nStarting the declarative agent. Press Ctrl+C to stop.")
    print("The prompt is automatically built from the PROMPT_SECTIONS class attribute.")
    
    # Print the rendered markdown prompt for demonstration
    print("\nGenerated Prompt:")
    print("-" * 50)
    
    # Get the formatted prompt from the agent's POM
    try:
        # Try to use pom directly (modern approach)
        if agent.pom:
            print(agent.pom.render_markdown())
        # Fallback for older implementations that might use _pom_builder
        elif hasattr(agent, '_pom_builder') and agent._pom_builder:
            print(agent._pom_builder.render_markdown())
        else:
            print(agent.get_prompt())
    except Exception as e:
        print(f"Could not render prompt: {e}")
        
    print("-" * 50)
    
    try:
        agent.serve()
    except KeyboardInterrupt:
        print("\nStopping the agent.")
        agent.stop() 