#!/usr/bin/env python3
"""
SWAIG Features Example

This example demonstrates the enhanced SWAIG features of the SignalWire AI Agent SDK:
- Default webhook URL for all functions (using defaults object)
- Properly structured parameters (with type:object and properties)
- Speech fillers for functions (to provide feedback during processing)

The resulting SWAIG array in SWML will have the following structure:
[
  {
    "defaults": {
      "web_hook_url": "https://developer:seekret@tatooine.cantina.cloud/ai/swaig.cgi"
    }
  },
  {
    "function": "get_time",
    "description": "Get the current time",
    "parameters": {
      "type": "object",
      "properties": {}
    },
    "fillers": {
      "en-US": ["Let me check the time for you", "..."]
    }
  },
  {
    "function": "get_weather",
    "description": "Get the current weather...",
    "parameters": {
      "type": "object",
      "properties": {
        "location": {
          "type": "string",
          "description": "The city or location to get weather for"
        }
      }
    },
    "fillers": {
      "en-US": ["I am checking the weather for you", "..."],
      "es": ["Estoy consultando el clima para ti", "..."]
    }
  }
]
"""

import os
import sys
from datetime import datetime

# Add the parent directory to the path so we can import the package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult


class SwaigFeaturesAgent(AgentBase):
    """
    An agent that demonstrates the enhanced SWAIG features
    """
    
    # Define the prompt sections declaratively
    PROMPT_SECTIONS = {
        "Personality": "You are a friendly and helpful assistant.",
        "Goal": "Demonstrate advanced SWAIG features.",
        "Instructions": [
            "Be concise and direct in your responses.",
            "Use the get_weather function when asked about weather.",
            "Use the get_time function when asked about the current time."
        ]
    }
    
    def __init__(self):
        # Initialize the agent with a name, route, and default webhook URL
        super().__init__(
            name="swaig_features",
            route="/swaig_features",
            host="0.0.0.0",
            port=3000,
            # Set a default webhook URL for all functions
            # This will create a defaults object in the SWAIG array
            default_webhook_url="https://developer:seekret@tatooine.cantina.cloud/ai/swaig.cgi"
        )
        
        # Add a post-prompt for summary
        self.set_post_prompt("""
        Return a JSON summary of the conversation:
        {
            "topic": "MAIN_TOPIC",
            "functions_used": ["list", "of", "functions", "used"]
        }
        """)
    
    @AgentBase.tool(
        name="get_time",
        description="Get the current time",
        parameters={},
        # Add fillers that will be spoken while processing
        fillers={
            "en-US": [
                "Let me check the time for you",
                "One moment while I check the current time"
            ]
        }
    )
    def get_time(self):
        """Get the current time"""
        now = datetime.now()
        formatted_time = now.strftime("%H:%M:%S")
        return SwaigFunctionResult(f"The current time is {formatted_time}")
    
    @AgentBase.tool(
        name="get_weather",
        description="Get the current weather for a location (including starwars planets)",
        # Note: parameters will be automatically wrapped with type:object and properties
        parameters={
            "location": {
                "type": "string",
                "description": "The city or location to get weather for"
            }
        },
        # Add fillers in multiple languages
        fillers={
            "en-US": [
                "I am checking the weather for you",
                "Let me look up the weather information"
            ],
            "es": [
                "Estoy consultando el clima para ti",
                "Permíteme verificar el clima"
            ]
        }
    )
    def get_weather(self, location):
        """Get the current weather for a location"""
        # In a real implementation, this would call a weather API
        weather_data = {
            "tatooine": "Hot and dry, with occasional sandstorms. Twin suns at their peak.",
            "hoth": "Extremely cold with blizzard conditions. High of -20°C.",
            "endor": "Mild forest weather. Partly cloudy with a high of 22°C.",
            "default": "It's sunny and 72°F"
        }
        
        result = weather_data.get(location.lower(), weather_data["default"])
        return SwaigFunctionResult(f"The weather in {location}: {result}")
    
    # This function also uses the default webhook URL
    @AgentBase.tool(
        name="get_forecast",
        description="Get a 3-day weather forecast for a location",
        parameters={
            "location": {
                "type": "string", 
                "description": "The city or location"
            },
            "units": {
                "type": "string",
                "description": "Temperature units (celsius or fahrenheit)",
                "enum": ["celsius", "fahrenheit"]
            }
        }
    )
    def get_forecast(self, location, units="fahrenheit"):
        """Get a weather forecast for a location"""
        # This would normally call a weather API
        # For demo purposes, we're returning mock data
        forecast = [
            {"day": "Today", "temp": 72, "condition": "Sunny"},
            {"day": "Tomorrow", "temp": 68, "condition": "Partly Cloudy"},
            {"day": "Day After", "temp": 75, "condition": "Clear"}
        ]
        
        # Format the forecast response
        if units == "celsius":
            for day in forecast:
                day["temp"] = round((day["temp"] - 32) * 5/9)
        
        forecast_text = "\n".join([f"{d['day']}: {d['temp']}°{'C' if units == 'celsius' else 'F'}, {d['condition']}" for d in forecast])
        return SwaigFunctionResult(f"3-day forecast for {location}:\n{forecast_text}")


if __name__ == "__main__":
    agent = SwaigFeaturesAgent()
    print("Starting the SWAIG features demo agent. Press Ctrl+C to stop.")
    print(f"Agent is accessible at: http://localhost:3000/swaig_features")
    
    try:
        agent.serve()
    except KeyboardInterrupt:
        print("\nStopping the agent.")
        agent.stop() 