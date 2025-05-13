#!/usr/bin/env python3
"""
Simple example of using the SignalWire AI Agent SDK

This example demonstrates creating an agent using explicit methods
to manipulate the POM (Prompt Object Model) structure directly.

This uses the refactored AgentBase class that internally uses SWMLService.
"""

from datetime import datetime
import json
import traceback
import logging
import sys
from typing import Optional
import os

# Import structlog for proper structured logging
import structlog

from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult
from fastapi import FastAPI, Request, Response, APIRouter
import uvicorn

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

# Create a direct FastAPI app instead of using the AgentBase serve method
app = FastAPI(
    # Disable automatic redirection for trailing slashes
    redirect_slashes=False
)

class SimpleAgent(AgentBase):
    """
    A simple agent that demonstrates using explicit methods
    to manipulate the POM structure directly
    
    This example shows:
    
    1. How to create an agent with a structured prompt using POM
    2. How to define SWAIG functions that the AI can call
    3. How to return results from SWAIG functions
    """
    
    def __init__(self):
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
                logger.info(f"Found schema.json at: {schema_path}")
                break
                
        if not schema_path:
            logger.warning("Could not find schema.json in expected locations")
            
        # Initialize the agent with a name and route
        super().__init__(
            name="simple",
            route="/simple",
            host="0.0.0.0",
            port=3000,
            use_pom=True,  # Ensure we're using POM
            schema_path=schema_path  # Pass the explicit schema path
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
    
    def on_summary(self, summary):
        """Handle the conversation summary"""
        logger.info("conversation_summary_received", summary=summary)


# Create a global instance of the agent
agent = SimpleAgent()

# Root endpoints - support both with and without trailing slash, and both GET and POST
@app.get("/simple")
@app.post("/simple")
@app.get("/simple/")
@app.post("/simple/")
async def handle_root(request: Request):
    req_logger = logger.bind(
        endpoint="root",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else "unknown"
    )
    
    req_logger.info("endpoint_called")
    
    try:
        # Check auth
        if not agent._check_basic_auth(request):
            req_logger.warning("unauthorized_access_attempt")
            return Response(
                content=json.dumps({"error": "Unauthorized"}),
                status_code=401,
                headers={"WWW-Authenticate": "Basic"},
                media_type="application/json"
            )
        
        # Try to parse request body for POST
        body = {}
        if request.method == "POST":
            try:
                body = await request.json()
                req_logger.debug("request_body_received", body_size=len(str(body)))
            except Exception as e:
                req_logger.warning("error_parsing_request_body", error=str(e))
                try:
                    body_text = await request.body()
                    req_logger.debug("raw_request_body", size=len(body_text))
                except:
                    pass
                    
            # Get call_id from body if present
            call_id = body.get("call_id")
        else:
            # Get call_id from query params for GET
            call_id = request.query_params.get("call_id")
            
        # Add call_id to logger if present
        if call_id:
            req_logger = req_logger.bind(call_id=call_id)
        
        # Render SWML
        swml = agent._render_swml(call_id)
        req_logger.debug("swml_rendered", swml_size=len(swml))
        
        # Return as JSON
        req_logger.info("request_successful")
        return Response(
            content=swml,
            media_type="application/json"
        )
    except Exception as e:
        req_logger.error("request_failed", 
                        error=str(e), 
                        traceback=traceback.format_exc())
        return Response(
            content=json.dumps({"error": str(e)}),
            status_code=500,
            media_type="application/json"
        )

# Debug endpoint - support both with and without trailing slash
@app.get("/simple/debug")
@app.get("/simple/debug/")
async def get_debug(request: Request):
    req_logger = logger.bind(
        endpoint="debug",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else "unknown"
    )
    
    req_logger.info("endpoint_called")
    
    try:
        # Check auth
        if not agent._check_basic_auth(request):
            req_logger.warning("unauthorized_access_attempt")
            return Response(
                content=json.dumps({"error": "Unauthorized"}),
                status_code=401,
                headers={"WWW-Authenticate": "Basic"},
                media_type="application/json"
            )
        
        # Render SWML
        swml = agent._render_swml()
        req_logger.debug("swml_rendered", swml_size=len(swml))
        
        # Return as JSON
        req_logger.info("request_successful")
        return Response(
            content=swml,
            media_type="application/json",
            headers={"X-Debug": "true"}
        )
    except Exception as e:
        req_logger.error("request_failed", 
                        error=str(e), 
                        traceback=traceback.format_exc())
        return Response(
            content=json.dumps({"error": str(e)}),
            status_code=500,
            media_type="application/json"
        )

# Function endpoint - support both with and without trailing slash
@app.post("/simple/swaig/")
@app.post("/simple/swaig")
async def post_swaig(request: Request):
    req_logger = logger.bind(
        endpoint="swaig",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else "unknown"
    )
    
    req_logger.info("endpoint_called")
    
    try:
        # Check auth
        if not agent._check_basic_auth(request):
            req_logger.warning("unauthorized_access_attempt")
            return Response(
                content=json.dumps({"error": "Unauthorized"}),
                status_code=401,
                headers={"WWW-Authenticate": "Basic"},
                media_type="application/json"
            )
        
        # Parse request
        try:
            body = await request.json()
            req_logger.debug("request_body_received", body_size=len(str(body)))
        except Exception:
            req_logger.warning("error_parsing_request_body")
            body = {}
        
        # Extract function name
        function_name = body.get("function")
        if not function_name:
            req_logger.warning("missing_function_name")
            return Response(
                content=json.dumps({"error": "Missing function name"}),
                status_code=400,
                media_type="application/json"
            )
        
        # Add function info to logger
        req_logger = req_logger.bind(function=function_name)
        
        # Extract arguments
        args = {}
        if "argument" in body and isinstance(body["argument"], dict):
            if "parsed" in body["argument"] and isinstance(body["argument"]["parsed"], list) and body["argument"]["parsed"]:
                args = body["argument"]["parsed"][0]
                req_logger.debug("function_args_parsed", args=args)
        
        # Call the function
        result = agent.on_function_call(function_name, args, body)
        
        # Convert result to dict if needed
        if isinstance(result, SwaigFunctionResult):
            result_dict = result.to_dict()
        elif isinstance(result, dict):
            result_dict = result
        else:
            result_dict = {"response": str(result)}
        
        req_logger.info("function_executed_successfully")
        return result_dict
    except Exception as e:
        req_logger.error("function_execution_failed", 
                        error=str(e), 
                        traceback=traceback.format_exc())
        return Response(
            content=json.dumps({"error": str(e)}),
            status_code=500,
            media_type="application/json"
        )

# Post-prompt endpoint - support both with and without trailing slash
@app.post("/simple/post_prompt/")
@app.post("/simple/post_prompt")
async def post_post_prompt(request: Request):
    req_logger = logger.bind(
        endpoint="post_prompt",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else "unknown"
    )
    
    req_logger.info("endpoint_called")
    
    try:
        # Check auth
        if not agent._check_basic_auth(request):
            req_logger.warning("unauthorized_access_attempt")
            return Response(
                content=json.dumps({"error": "Unauthorized"}),
                status_code=401,
                headers={"WWW-Authenticate": "Basic"},
                media_type="application/json"
            )
        
        # Parse request
        try:
            body = await request.json()
            req_logger.debug("request_body_received", body_size=len(str(body)))
        except Exception as e:
            req_logger.warning("error_parsing_request_body", error=str(e))
            body = {}
        
        # Extract summary from the request
        ai_response = body.get("ai_response", {})
        summary = ai_response.get("summary")
        
        # Call the summary handler
        if summary:
            req_logger.debug("summary_received", summary=summary)
            agent.on_summary(summary)
        else:
            req_logger.warning("summary_missing")
        
        # Return success
        req_logger.info("request_successful")
        return {"success": True}
    except Exception as e:
        req_logger.error("request_failed", 
                        error=str(e), 
                        traceback=traceback.format_exc())
        return Response(
            content=json.dumps({"error": str(e)}),
            status_code=500,
            media_type="application/json"
        )

# Log all registered routes
logger.info("routes_registered", routes=[f"{route.methods} {route.path}" for route in app.routes])

if __name__ == "__main__":
    # Print the auth credentials
    username, password, _ = agent.get_basic_auth_credentials(include_source=True)
    
    print("Starting the agent. Press Ctrl+C to stop.")
    print(f"Agent 'simple' is available at:")
    print(f"URL: http://localhost:3000/simple")
    print(f"Basic Auth: {username}:{password}")
    
    try:
        # Configure Uvicorn for production
        uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
        uvicorn_log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        uvicorn_log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=3000,
            log_config=uvicorn_log_config
        )
    except KeyboardInterrupt:
        logger.info("server_shutdown")
        print("\nStopping the agent.") 