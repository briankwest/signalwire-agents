#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple example of using the SignalWire AI Agent SDK

This example demonstrates creating an agent using explicit methods
to manipulate the POM (Prompt Object Model) structure directly.

This uses the refactored AgentBase class that internally uses SWMLService.
"""

from datetime import datetime
import os
import logging
import sys
import json
import argparse
import fastapi

# Import structlog for proper structured logging
import structlog

from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Set up the root logger with structlog
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

# Create structured logger
logger = structlog.get_logger("simple_agent")

class SimpleAgent(AgentBase):
    """
    A simple agent that demonstrates using explicit methods
    to manipulate the POM structure directly
    
    This example shows:
    
    1. How to create an agent with a structured prompt using POM
    2. How to define SWAIG functions that the AI can call
    3. How to return results from SWAIG functions
    4. How to configure various AI verb parameters
    5. How to configure SWAIG with native functions and remote includes
    """
    
    def __init__(self, suppress_logs=False):
        # Find schema.json in the current directory or parent directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        
        # Try to find schema.json in several locations
        schema_locations = [
            os.path.join(current_dir, "schema.json"),
            os.path.join(parent_dir, "schema.json"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "schema.json")
        ]
        
        schema_path = None
        for loc in schema_locations:
            if os.path.exists(loc):
                schema_path = loc
                logger.info("schema_found", path=schema_path)
                break
                
        if not schema_path:
            logger.warning("schema_not_found", locations=schema_locations)
            
        # Initialize the agent with a name and route
        super().__init__(
            name="simple",
            route="/simple",
            host="0.0.0.0",
            port=3000,
            use_pom=True,  # Ensure we're using POM
            schema_path=schema_path,  # Pass the explicit schema path
            suppress_logs=suppress_logs  # Suppress extra logs
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
        
        # Configure hints to help the AI understand certain words
        self.add_hints([
            "SignalWire", 
            "SWML", 
            "SWAIG"
        ])
        
        # Add a pattern hint for pronunciation
        self.add_pattern_hint(
            hint="AI Agent", 
            pattern="AI\\s+Agent", 
            replace="A.I. Agent", 
            ignore_case=True
        )
        
        # Add pronunciation rules
        self.add_pronunciation("API", "A P I", ignore_case=False)
        self.add_pronunciation("SIP", "sip", ignore_case=True)
        
        # Configure language support
        # Example 1: Simple format
        self.add_language(
            name="English",
            code="en-US",
            voice="elevenlabs.josh",
            speech_fillers=["Let me think about that...", "One moment please..."],
            function_fillers=["I'm looking that up for you...", "Let me check that..."]
        )

        # Example 2: Explicit parameters with engine and model
        self.add_language(
            name="British English",
            code="en-GB",
            voice="emma",
            engine="elevenlabs",
            model="eleven_turbo_v2",
            speech_fillers=["Just a moment...", "Thinking..."]
        )

        # Example 3: Combined string format
        self.add_language(
            name="Spanish",
            code="es",
            voice="elevenlabs.antonio:eleven_multilingual_v2",
            speech_fillers=["Un momento por favor...", "Estoy pensando..."],
            function_fillers=["Estoy buscando esa información...", "Déjame verificar..."]
        )

        # Example 4: Rime engine with explicit parameters
        self.add_language(
            name="French",
            code="fr-FR",
            voice="claire",
            engine="rime",
            model="arcana"
        )

        # Example 5: Rime engine with combined format
        self.add_language(
            name="German",
            code="de-DE",
            voice="rime.hans:arcana"
        )
        
        # Set AI behavior parameters
        self.set_params({
            "wait_for_user": False,
            "end_of_speech_timeout": 1000,
            "ai_volume": 5,
            "languages_enabled": True,
            "local_tz": "America/Los_Angeles"
        })
        
        # Add global data available to the AI
        self.set_global_data({
            "company_name": "SignalWire",
            "product": "AI Agent SDK",
            "supported_features": [
                "Voice AI",
                "Telephone integration",
                "SWAIG functions"
            ]
        })
        
        # Configure native functions (built-in functions)
        self.set_native_functions([
            "check_time",
            "wait_seconds"
        ])
        
        # Add remote function includes
        self.add_function_include(
            url="https://api.example.com/remote-functions",
            functions=["get_weather_extended", "get_traffic", "get_news"],
            meta_data={
                "auth_type": "bearer",
                "region": "us-west"
            }
        )
        
        # Add another remote function include with a different URL
        self.add_function_include(
            url="https://ai-tools.example.org/functions",
            functions=["translate_text", "summarize_document"]
        )
        
        # Enable SIP routing for this agent
        self.enable_sip_routing(auto_map=True)
        
        # Register additional SIP usernames for this agent
        self.register_sip_username("simple_agent")
        self.register_sip_username("assistant")
        
        logger.info("agent_initialized", agent_name=self.name, route=self.route)
    
    def setPersonality(self, personality_text):
        """Set the AI personality description"""
        self.prompt_add_section("Personality", body=personality_text)
        return self
    
    def setGoal(self, goal_text):
        """Set the primary goal for the AI agent"""
        self.prompt_add_section("Goal", body=goal_text)
        return self
    
    def setInstructions(self, instructions_list):
        """Set the list of instructions for the AI agent"""
        if instructions_list:
            self.prompt_add_section("Instructions", bullets=instructions_list)
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
        logger.debug("get_time_called", time=formatted_time)
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
        data is in raw_data.
        
        Args:
            args: Dictionary containing parsed parameters (location)
            raw_data: Complete request data including call_id and other metadata
            
        Returns:
            SwaigFunctionResult containing the response text and optional actions
        """
        # Extract location from the args dictionary 
        location = args.get("location", "Unknown location")
        
        # Log the function call with structured data
        logger.debug("get_weather_called", location=location)
        
        # Create the result with a response
        result = SwaigFunctionResult(f"It's sunny and 72°F in {location}.")
        
        return result
    
    def on_summary(self, summary, raw_data=None):
        """
        Handle the conversation summary
        
        Args:
            summary: The summary object or None if no summary was found
            raw_data: The complete raw POST data from the request
        """
        # Print summary as properly formatted JSON (not Python dict representation)
        if summary:
            if isinstance(summary, (dict, list)):
                print("SUMMARY: " + json.dumps(summary))
            else:
                print(f"SUMMARY: {summary}")
        
        # Also directly print parsed array if available
        if raw_data and 'post_prompt_data' in raw_data:
            post_prompt_data = raw_data.get('post_prompt_data')
            if isinstance(post_prompt_data, dict) and 'parsed' in post_prompt_data:
                parsed = post_prompt_data.get('parsed')
                if parsed and len(parsed) > 0:
                    print("PARSED_SUMMARY: " + json.dumps(parsed[0]))
            
            # Print raw if available - this is already a JSON string, so print directly
            if isinstance(post_prompt_data, dict) and 'raw' in post_prompt_data:
                raw = post_prompt_data.get('raw')
                if isinstance(raw, str):
                    print(f"RAW_SUMMARY: {raw}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the SimpleAgent")
    parser.add_argument("--suppress-logs", action="store_true", help="Suppress extra logs")
    args = parser.parse_args()
    
    # Create an agent instance with log suppression if requested
    agent = SimpleAgent(suppress_logs=args.suppress_logs)
    
    # Print credentials
    username, password, source = agent.get_basic_auth_credentials(include_source=True)
    
    logger.info("starting_agent", 
               url=f"http://localhost:3000/simple", 
               username=username, 
               password_length=len(password),
               auth_source=source)
    
    print("Starting the agent. Press Ctrl+C to stop.")
    print(f"Agent 'simple' is available at:")
    print(f"URL: http://localhost:3000/simple")
    print(f"Basic Auth: {username}:{password}")
    
    try:
        # Start the agent's server using the built-in serve method
        agent.serve()
    except KeyboardInterrupt:
        logger.info("server_shutdown")
        print("\nStopping the agent.") 
