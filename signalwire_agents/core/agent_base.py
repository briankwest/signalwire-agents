"""
AgentBase - Core foundation class for all SignalWire AI Agents
"""

import functools
import inspect
import os
import uuid
from typing import Dict, List, Any, Optional, Union, Callable, Tuple, Type, TypeVar
import base64
import secrets
from urllib.parse import urlparse
import json
from datetime import datetime

try:
    import fastapi
    from fastapi import FastAPI, APIRouter, Depends, HTTPException, Query, Body, Request, Response
    from fastapi.security import HTTPBasic, HTTPBasicCredentials
    from pydantic import BaseModel
except ImportError:
    raise ImportError(
        "fastapi is required. Install it with: pip install fastapi"
    )

from signalwire_agents.core.pom_builder import PomBuilder
from signalwire_agents.core.swaig_function import SWAIGFunction
from signalwire_agents.core.function_result import SwaigFunctionResult
from signalwire_agents.core.swml_renderer import SwmlRenderer
from signalwire_agents.core.security.session_manager import SessionManager
from signalwire_agents.core.state import StateManager, FileStateManager


class AgentBase:
    """
    Base class for all SignalWire AI Agents.
    
    This class provides core functionality for building agents including:
    - Prompt building and customization
    - SWML rendering
    - SWAIG function definition and execution
    - Web service for serving SWML and handling webhooks
    - Security and session management
    
    Subclassing options:
    1. Simple override of get_prompt() for raw text
    2. Using prompt_* methods for structured prompts
    3. Declarative PROMPT_SECTIONS class attribute
    """
    
    # Subclasses can define this to declaratively set prompt sections
    PROMPT_SECTIONS = None
    
    def __init__(
        self,
        name: str,
        route: str = "/",
        host: str = "0.0.0.0",
        port: int = 3000,
        basic_auth: Optional[Tuple[str, str]] = None,
        use_pom: bool = True,
        enable_state_tracking: bool = False,
        token_expiry_secs: int = 600,
        auto_answer: bool = True,
        record_call: bool = False,
        record_format: str = "mp4",
        record_stereo: bool = True,
        state_manager: Optional[StateManager] = None,
        default_webhook_url: Optional[str] = None,
        agent_id: Optional[str] = None,
        native_functions: Optional[List[str]] = None
    ):
        """
        Initialize a new agent
        
        Args:
            name: Agent name/identifier
            route: HTTP route path for this agent
            host: Host to bind the web server to
            port: Port to bind the web server to
            basic_auth: Optional (username, password) tuple for basic auth
            use_pom: Whether to use POM for prompt building
            enable_state_tracking: Whether to track state across a call lifecycle using startup_hook and hangup_hook
            token_expiry_secs: Seconds until tokens expire
            auto_answer: Whether to automatically answer calls
            record_call: Whether to record calls
            record_format: Recording format
            record_stereo: Whether to record in stereo
            state_manager: Optional state manager for this agent
            default_webhook_url: Optional default webhook URL for all SWAIG functions
            agent_id: Optional unique ID for this agent, generated if not provided
            native_functions: Optional list of native functions to include in the SWAIG object
        """
        self.name = name
        self.route = route.rstrip("/")  # Ensure no trailing slash
        self.host = host
        self.port = port
        self._default_webhook_url = default_webhook_url
        
        # Generate or use the provided agent ID
        self.agent_id = agent_id or str(uuid.uuid4())
        
        # Check for proxy URL base in environment
        self._proxy_url_base = os.environ.get('SWML_PROXY_URL_BASE')
        
        # Set basic auth credentials
        if basic_auth is not None:
            # Use provided credentials
            self._basic_auth = basic_auth
        else:
            # Check environment variables first - be explicit about getting them
            env_user = os.environ.get('SWML_BASIC_AUTH_USER')
            env_pass = os.environ.get('SWML_BASIC_AUTH_PASSWORD')
            
            if env_user and env_pass:
                # Use environment variables - create a new tuple to avoid reference issues
                self._basic_auth = (str(env_user), str(env_pass))
            else:
                # Generate random credentials as fallback
                username = f"user_{secrets.token_hex(4)}"
                password = secrets.token_urlsafe(16)
                self._basic_auth = (username, password)
        
        # Initialize prompt builder
        self._use_pom = use_pom
        self._pom_builder = PomBuilder() if use_pom else None
        self._raw_prompt = None
        self._post_prompt = None
        
        # Initialize tool registry
        self._swaig_functions: Dict[str, SWAIGFunction] = {}
        
        # Initialize session manager
        self._session_manager = SessionManager(token_expiry_secs=token_expiry_secs)
        self._enable_state_tracking = enable_state_tracking
        
        # Server state
        self._app = None
        self._router = None
        self._running = False
        
        # Register the tool decorator on this instance
        self.tool = self._tool_decorator
        
        # Call settings
        self._auto_answer = auto_answer
        self._record_call = record_call
        self._record_format = record_format
        self._record_stereo = record_stereo
        
        # Process declarative PROMPT_SECTIONS if defined in subclass
        self._process_prompt_sections()
        
        # Initialize state manager
        self._state_manager = state_manager or FileStateManager()
        
        # Process class-decorated tools (using @AgentBase.tool)
        self._register_class_decorated_tools()
        
        # Add native_functions parameter
        self.native_functions = native_functions or []
    
    def _process_prompt_sections(self):
        """
        Process declarative PROMPT_SECTIONS attribute from a subclass
        
        This auto-vivifies section methods and bootstraps the prompt
        from class declaration, allowing for declarative agents.
        """
        # Skip if no PROMPT_SECTIONS defined or not using POM
        cls = self.__class__
        if not hasattr(cls, 'PROMPT_SECTIONS') or cls.PROMPT_SECTIONS is None or not self._use_pom:
            return
            
        sections = cls.PROMPT_SECTIONS
        
        # If sections is a dictionary mapping section names to content
        if isinstance(sections, dict):
            for title, content in sections.items():
                # Handle different content types
                if isinstance(content, str):
                    # Plain text - add as body
                    self.prompt_add_section(title, body=content)
                elif isinstance(content, list):
                    # List of strings - add as bullets
                    self.prompt_add_section(title, bullets=content)
                elif isinstance(content, dict):
                    # Dictionary with body/bullets/subsections
                    body = content.get('body', '')
                    bullets = content.get('bullets', [])
                    numbered = content.get('numbered', False)
                    numbered_bullets = content.get('numberedBullets', False)
                    
                    # Create the section
                    self.prompt_add_section(
                        title, 
                        body=body, 
                        bullets=bullets,
                        numbered=numbered,
                        numbered_bullets=numbered_bullets
                    )
                    
                    # Process subsections if any
                    subsections = content.get('subsections', [])
                    for subsection in subsections:
                        if 'title' in subsection:
                            sub_title = subsection['title']
                            sub_body = subsection.get('body', '')
                            sub_bullets = subsection.get('bullets', [])
                            
                            self.prompt_add_subsection(
                                title, 
                                sub_title,
                                body=sub_body,
                                bullets=sub_bullets
                            )
        # If sections is a list of section objects
        elif isinstance(sections, list):
            # Use the POM format directly
            if self._pom_builder:
                self._pom_builder = PomBuilder.from_sections(sections)
    
    # ----------------------------------------------------------------------
    # Prompt Building Methods
    # ----------------------------------------------------------------------
    
    def set_prompt_text(self, text: str) -> 'AgentBase':
        """
        Set the prompt as raw text instead of using POM
        
        Args:
            text: The raw prompt text
            
        Returns:
            Self for method chaining
        """
        self._raw_prompt = text
        return self
    
    def set_prompt_pom(self, pom: List[Dict[str, Any]]) -> 'AgentBase':
        """
        Set the prompt as a POM dictionary
        
        Args:
            pom: POM dictionary structure
            
        Returns:
            Self for method chaining
        """
        if self._use_pom:
            self._pom_builder = PomBuilder.from_sections(pom)
        else:
            raise ValueError("use_pom must be True to use set_prompt_pom")
        return self
    
    def prompt_add_section(
        self, 
        title: str, 
        body: str = "", 
        bullets: Optional[List[str]] = None,
        numbered: bool = False,
        numbered_bullets: bool = False
    ) -> 'AgentBase':
        """
        Add a section to the prompt
        
        Args:
            title: Section title
            body: Optional section body text
            bullets: Optional list of bullet points
            numbered: Whether this section should be numbered
            numbered_bullets: Whether bullets should be numbered
            
        Returns:
            Self for method chaining
        """
        if self._use_pom and self._pom_builder:
            self._pom_builder.add_section(
                title=title,
                body=body,
                bullets=bullets,
                numbered=numbered,
                numbered_bullets=numbered_bullets
            )
        return self
        
    def prompt_add_to_section(
        self,
        title: str,
        body: Optional[str] = None,
        bullet: Optional[str] = None,
        bullets: Optional[List[str]] = None
    ) -> 'AgentBase':
        """
        Add content to an existing section (creating it if needed)
        
        Args:
            title: Section title
            body: Optional text to append to section body
            bullet: Optional single bullet point to add
            bullets: Optional list of bullet points to add
            
        Returns:
            Self for method chaining
        """
        if self._use_pom and self._pom_builder:
            self._pom_builder.add_to_section(
                title=title,
                body=body,
                bullet=bullet,
                bullets=bullets
            )
        return self
        
    def prompt_add_subsection(
        self,
        parent_title: str,
        title: str,
        body: str = "",
        bullets: Optional[List[str]] = None
    ) -> 'AgentBase':
        """
        Add a subsection to an existing section (creating parent if needed)
        
        Args:
            parent_title: Parent section title
            title: Subsection title
            body: Optional subsection body text
            bullets: Optional list of bullet points
            
        Returns:
            Self for method chaining
        """
        if self._use_pom and self._pom_builder:
            self._pom_builder.add_subsection(
                parent_title=parent_title,
                title=title,
                body=body,
                bullets=bullets
            )
        return self
    
    # ----------------------------------------------------------------------
    # Tool/Function Management
    # ----------------------------------------------------------------------
    
    def define_tool(
        self, 
        name: str, 
        description: str, 
        parameters: Dict[str, Any], 
        handler: Callable,
        secure: bool = True,
        fillers: Optional[Dict[str, List[str]]] = None
    ) -> 'AgentBase':
        """
        Define a SWAIG function that the AI can call
        
        Args:
            name: Function name (must be unique)
            description: Function description for the AI
            parameters: JSON Schema of parameters
            handler: Function to call when invoked
            secure: Whether to require token validation
            fillers: Optional dict mapping language codes to arrays of filler phrases
            
        Returns:
            Self for method chaining
        """
        if name in self._swaig_functions:
            raise ValueError(f"Tool with name '{name}' already exists")
            
        self._swaig_functions[name] = SWAIGFunction(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            secure=secure,
            fillers=fillers
        )
        return self
    
    def _tool_decorator(self, name=None, **kwargs):
        """
        Decorator for defining SWAIG tools in a class
        
        Used as:
        
        @agent.tool(name="example_function", parameters={...})
        def example_function(self, param1):
            # ...
        """
        def decorator(func):
            nonlocal name
            if name is None:
                name = func.__name__
                
            parameters = kwargs.get("parameters", {})
            description = kwargs.get("description", func.__doc__ or f"Function {name}")
            secure = kwargs.get("secure", True)
            fillers = kwargs.get("fillers", None)
            
            self.define_tool(
                name=name,
                description=description,
                parameters=parameters,
                handler=func,
                secure=secure,
                fillers=fillers
            )
            return func
        return decorator
    
    @classmethod
    def tool(cls, name=None, **kwargs):
        """
        Class method decorator for defining SWAIG tools
        
        Used as:
        
        @AgentBase.tool(name="example_function", parameters={...})
        def example_function(self, param1):
            # ...
        """
        def decorator(func):
            setattr(func, "_is_tool", True)
            setattr(func, "_tool_name", name or func.__name__)
            setattr(func, "_tool_params", kwargs)
            return func
        return decorator
    
    # ----------------------------------------------------------------------
    # Override Points for Subclasses
    # ----------------------------------------------------------------------
    
    def get_name(self) -> str:
        """
        Get the agent name
        
        Returns:
            Agent name/identifier
        """
        return self.name
    
    def get_prompt(self) -> Union[str, List[Dict[str, Any]]]:
        """
        Get the prompt for the agent
        
        Returns:
            Either a string prompt or POM structure
            
        This method can be overridden by subclasses.
        """
        if self._raw_prompt is not None:
            return self._raw_prompt
            
        if self._use_pom and self._pom_builder is not None:
            return self._pom_builder.to_dict()
            
        # Default minimal prompt if nothing else set
        return "You are a helpful AI assistant. Answer user questions clearly and concisely."
    
    def get_post_prompt(self) -> Optional[str]:
        """
        Get the post-prompt for the agent
        
        Returns:
            Post-prompt text or None
            
        This method can be overridden by subclasses.
        """
        return self._post_prompt
    
    def define_tools(self) -> List[SWAIGFunction]:
        """
        Define the tools this agent can use
        
        Returns:
            List of SWAIGFunction objects
            
        This method can be overridden by subclasses.
        """
        return list(self._swaig_functions.values())
    
    def on_summary(self, summary: Dict[str, Any]) -> None:
        """
        Handle the post-prompt summary result
        
        Args:
            summary: Summary data from post_prompt
            
        This method should be overridden by subclasses.
        """
        pass
    
    def on_function_call(self, name: str, args: Dict[str, Any], raw_data: Optional[Dict[str, Any]] = None) -> Any:
        """
        Handle a function call if not handled by a specific function
        
        Args:
            name: Function name
            args: Extracted function arguments
            raw_data: Optional raw request data
            
        Returns:
            Function result with "response" and optional "actions" keys
            
        This method can be overridden by subclasses.
        """
        if name not in self._swaig_functions:
            return SwaigFunctionResult(f"Function '{name}' not found").to_dict()
        
        # Get the function and handler
        func = self._swaig_functions[name]
        handler = func.handler
        
        # Check if the handler accepts a raw_data parameter
        sig = inspect.signature(handler)
        handler_params = list(sig.parameters.keys())
        
        # If handler has a raw_data parameter, pass the raw data
        if 'raw_data' in handler_params:
            result = func.execute(args, raw_data=raw_data)
        else:
            # Otherwise, just call with the extracted arguments
            result = func.execute(args)
            
        # Ensure the result is properly serialized
        if isinstance(result, SwaigFunctionResult):
            result = result.to_dict()
            
        # Ensure response has the right format
        if isinstance(result, dict):
            # Create a clean result with only the fields we need
            clean_result = {}
            
            # Extract response
            if "response" in result:
                clean_result["response"] = result["response"]
            elif "result" in result and isinstance(result["result"], dict) and "response" in result["result"]:
                clean_result["response"] = result["result"]["response"]
            else:
                clean_result["response"] = "Function executed successfully."
                
            # Extract actions if present
            if "actions" in result:
                clean_result["actions"] = result["actions"]
            elif "result" in result and isinstance(result["result"], dict) and "actions" in result["result"]:
                clean_result["actions"] = result["result"]["actions"]
                
            return clean_result
        else:
            # For non-dict results, wrap in a response
            return {"response": str(result)}
    
    def validate_basic_auth(self, username: str, password: str) -> bool:
        """
        Validate basic auth credentials
        
        Args:
            username: Username from request
            password: Password from request
            
        Returns:
            True if valid, False otherwise
            
        This method can be overridden by subclasses.
        """
        return (username, password) == self._basic_auth
    
    def validate_tool_token(self, function_name: str, token: str, call_id: str) -> bool:
        """
        Validate a tool token
        
        Args:
            function_name: Function name
            token: Token to validate
            call_id: Call session ID
            
        Returns:
            True if valid, False otherwise
            
        This method can be overridden by subclasses.
        """
        if not self._enable_state_tracking:
            # Simple token comparison if not using state tracking
            return token == self._basic_auth[1]
            
        # Use session manager for validation
        return self._session_manager.validate_token(call_id, function_name, token)
    
    # ----------------------------------------------------------------------
    # Web Server and Routing
    # ----------------------------------------------------------------------
    
    def get_basic_auth_credentials(self, include_source: bool = False) -> Union[Tuple[str, str], Tuple[str, str, str]]:
        """
        Get the basic auth credentials
        
        Args:
            include_source: Whether to include the source of the credentials
            
        Returns:
            If include_source is False:
                (username, password) tuple
            If include_source is True:
                (username, password, source) tuple, where source is one of:
                "provided", "environment", or "generated"
        """
        username, password = self._basic_auth
        
        if not include_source:
            return (username, password)
            
        # Determine source of credentials
        env_user = os.environ.get('SWML_BASIC_AUTH_USER')
        env_pass = os.environ.get('SWML_BASIC_AUTH_PASSWORD')
        
        # More robust source detection
        if env_user and env_pass and username == env_user and password == env_pass:
            source = "environment"
        elif username.startswith("user_") and len(password) > 20:  # Format of generated credentials
            source = "generated"
        else:
            source = "provided"
            
        return (username, password, source)
    
    def get_full_url(self, include_auth: bool = False) -> str:
        """
        Get the full URL for this agent's endpoint
        
        Args:
            include_auth: Whether to include authentication credentials in the URL
            
        Returns:
            Full URL including host, port, and route (with auth if requested)
        """
        # Start with the base URL (either proxy or local)
        if self._proxy_url_base:
            # Use the proxy URL base from environment, ensuring we don't duplicate the route
            # Strip any trailing slashes from proxy base
            proxy_base = self._proxy_url_base.rstrip('/')
            # Make sure route starts with a slash for consistency
            route = self.route if self.route.startswith('/') else f"/{self.route}"
            base_url = f"{proxy_base}{route}"
        else:
            # Default local URL
            if self.host in ("0.0.0.0", "127.0.0.1", "localhost"):
                host = "localhost"
            else:
                host = self.host
                
            base_url = f"http://{host}:{self.port}{self.route}"
            
        # Add auth if requested
        if include_auth:
            username, password = self._basic_auth
            url = urlparse(base_url)
            return url._replace(netloc=f"{username}:{password}@{url.netloc}").geturl()
        
        return base_url
        
    def _build_webhook_url(self, endpoint: str, query_params: Optional[Dict[str, str]] = None) -> str:
        """
        Helper method to build webhook URLs consistently
        
        Args:
            endpoint: The endpoint path (e.g., "swaig", "post_prompt")
            query_params: Optional query parameters to append
            
        Returns:
            Fully constructed webhook URL
        """
        # Base URL construction
        if self._proxy_url_base:
            # For proxy URLs
            base = self._proxy_url_base.rstrip('/')
            
            # Always add auth credentials
            username, password = self._basic_auth
            url = urlparse(base)
            base = url._replace(netloc=f"{username}:{password}@{url.netloc}").geturl()
        else:
            # For local URLs
            if self.host in ("0.0.0.0", "127.0.0.1", "localhost"):
                host = "localhost"
            else:
                host = self.host
                
            # Always include auth credentials
            username, password = self._basic_auth
            base = f"http://{username}:{password}@{host}:{self.port}"
        
        # Ensure the endpoint has a trailing slash to prevent redirects
        if endpoint in ["swaig", "post_prompt"]:
            endpoint = f"{endpoint}/"
            
        # Simple path - use the route directly with the endpoint
        path = f"{self.route}/{endpoint}"
            
        # Construct full URL
        url = f"{base}{path}"
        
        # Add query parameters if any (only if they have values)
        if query_params:
            # Filter out empty parameters
            valid_params = {k: v for k, v in query_params.items() if v}
            if valid_params:
                params = "&".join([f"{k}={v}" for k, v in valid_params.items()])
                url = f"{url}?{params}"
            
        return url

    def _create_tool_token(self, tool_name: str, call_id: str) -> str:
        """
        Create a token for a SWAIG function
        
        Args:
            tool_name: Name of the tool/function
            call_id: Call session ID
            
        Returns:
            Token string for the function
        """
        # If using session manager, generate a token through it
        if self._enable_state_tracking:
            return self._session_manager.generate_token(function_name=tool_name, call_id=call_id)
        
        # Otherwise, use a simpler approach - just use the password as the token
        # Since all requests are authenticated with basic auth anyway
        return self._basic_auth[1]

    def _render_swml(self, call_id: str = None) -> str:
        """
        Render the complete SWML document
        
        Args:
            call_id: Optional call ID for session-specific tokens
            
        Returns:
            SWML document as a string
        """
        # Get prompt
        prompt = self.get_prompt()
        prompt_is_pom = isinstance(prompt, list)
        
        # Get post-prompt
        post_prompt = self.get_post_prompt()
        
        # Generate a call ID if needed
        if self._enable_state_tracking and call_id is None:
            call_id = self._session_manager.create_session()
            
        # Query params with call_id (if available)
        query_params = {}
        if call_id:
            query_params["call_id"] = call_id
        
        # Get the default webhook URL with auth
        default_webhook_url = self._build_webhook_url("swaig", query_params)
        
        # Prepare SWAIG object (correct format)
        swaig_obj = {}
        
        # Add defaults if we have functions
        if self._swaig_functions:
            swaig_obj["defaults"] = {
                "web_hook_url": default_webhook_url
            }
            
        # Add native_functions if any are defined
        if self.native_functions:
            swaig_obj["native_functions"] = self.native_functions
        
        # Create functions array
        swaig_functions = []
        
        # Add each function to the functions array
        for name, func in self._swaig_functions.items():
            # Get token for secure functions when we have a call_id
            token = None
            if func.secure and call_id:
                token = self._create_tool_token(tool_name=name, call_id=call_id)
                
            # Prepare function entry
            function_entry = {
                "function": name,
                "description": func.description,
                "parameters": {
                    "type": "object",
                    "properties": func.parameters
                }
            }
            
            # Add fillers if present
            if func.fillers:
                function_entry["filler"] = func.fillers
                
            # Add token to URL if we have one
            if token:
                # Create a copy of query_params and add token
                token_params = query_params.copy()
                token_params["token"] = token
                function_entry["web_hook_url"] = self._build_webhook_url("swaig", token_params)
                
            swaig_functions.append(function_entry)
            
        # Add functions array to SWAIG object if we have any
        if swaig_functions:
            swaig_obj["functions"] = swaig_functions
            
        # Add post-prompt URL if we have a post-prompt
        post_prompt_url = None
        if post_prompt:
            post_prompt_url = self._build_webhook_url("post_prompt", query_params)
        
        # Get hooks for state tracking
        startup_hook_url = None
        hangup_hook_url = None
        
        if self._enable_state_tracking and call_id:
            # Create tokens for hooks
            startup_token = self._create_tool_token("startup_hook", call_id)
            hangup_token = self._create_tool_token("hangup_hook", call_id)
            
            # Create params with tokens
            startup_params = query_params.copy()
            startup_params["token"] = startup_token
            
            hangup_params = query_params.copy()
            hangup_params["token"] = hangup_token
            
            # Build URLs
            startup_hook_url = self._build_webhook_url("swaig", startup_params)
            hangup_hook_url = self._build_webhook_url("swaig", hangup_params)
            
        # Construct SWML
        swml = {
            "version": "1.0.0",
            "sections": {
                "main": [
                    {
                        "answer": {}
                    },
                    {
                        "ai": {
                            "prompt": {}
                        }
                    }
                ]
            }
        }
        
        # Add post-prompt if set
        if post_prompt:
            swml["sections"]["main"][1]["ai"]["post_prompt"] = {
                "text": post_prompt
            }
            if post_prompt_url:
                swml["sections"]["main"][1]["ai"]["post_prompt_url"] = post_prompt_url
        
        # Add prompt based on type
        if prompt_is_pom:
            swml["sections"]["main"][1]["ai"]["prompt"]["pom"] = prompt
        else:
            swml["sections"]["main"][1]["ai"]["prompt"]["text"] = prompt
        
        # Add SWAIG if we have functions
        if swaig_obj:
            swml["sections"]["main"][1]["ai"]["SWAIG"] = swaig_obj
            
        # Add hooks for state tracking
        if startup_hook_url:
            swml["sections"]["main"][1]["ai"]["SWML"] = {
                "stack": [
                    {
                        "function": "startup_hook"
                    }
                ],
                "functions": {
                    "startup_hook": {
                        "curl": {
                            "url": startup_hook_url,
                            "method": "POST",
                            "content_type": "application/json",
                            "body": {
                                "function": "startup_hook",
                                "call_id": call_id
                            }
                        }
                    }
                }
            }
            
        if hangup_hook_url:
            swml["on_hangup"] = {
                "curl": {
                    "url": hangup_hook_url,
                    "method": "POST", 
                    "content_type": "application/json",
                    "body": {
                        "function": "hangup_hook",
                        "call_id": call_id
                    }
                }
            }
            
        # Return SWML as a string (will be converted to JSON by the endpoint)
        return json.dumps(swml)
    
    def _check_basic_auth(self, request: Request) -> bool:
        """
        Check basic auth from a request
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if auth is valid, False otherwise
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Basic "):
            return False
            
        try:
            # Decode the base64 credentials
            credentials = base64.b64decode(auth_header[6:]).decode("utf-8")
            username, password = credentials.split(":", 1)
            return self.validate_basic_auth(username, password)
        except Exception:
            return False
    
    def as_router(self) -> APIRouter:
        """
        Get a FastAPI router for this agent
        
        Returns:
            FastAPI router object
        """
        if self._router is not None:
            return self._router
            
        router = APIRouter()
        
        # Main SWML endpoint - supports both GET and POST
        @router.get("/")
        async def get_swml(request: Request, response: Response):
            # Check auth
            if not self._check_basic_auth(request):
                response.headers["WWW-Authenticate"] = "Basic"
                return HTTPException(status_code=401, detail="Unauthorized")
                
            # Generate SWML
            call_id = request.query_params.get("call_id")
            swml_string = self._render_swml(call_id)
            
            # Parse the string to get the actual JSON object
            swml_json = json.loads(swml_string)
            
            # Return the raw JSON (FastAPI will serialize it once)
            return swml_json
            
        # POST support for sending data to the agent
        @router.post("/")
        async def post_data(request: Request, response: Response):
            # Check auth
            if not self._check_basic_auth(request):
                response.headers["WWW-Authenticate"] = "Basic"
                return HTTPException(status_code=401, detail="Unauthorized")
                
            try:
                # Parse the request body JSON (if any)
                body = await self._parse_request_body(request)
                
                # Get call_id from query params or body
                call_id = request.query_params.get("call_id", body.get("call_id"))
                
                # Just store the body for now, actual state initialization happens 
                # through startup_hook, not through main endpoint
                if call_id:
                    # Save this request for future processing
                    self._save_request_data(call_id, body)
                
                # Generate and return SWML
                swml_string = self._render_swml(call_id)
                swml_json = json.loads(swml_string)
                
                return swml_json
            except Exception as e:
                return {"status": "error", "message": str(e)}
        
        # Post-prompt webhook (with trailing slash to avoid redirects)
        @router.post("/post_prompt/")
        async def handle_post_prompt(request: Request, response: Response):
            # Check auth
            if not self._check_basic_auth(request):
                response.headers["WWW-Authenticate"] = "Basic"
                return HTTPException(status_code=401, detail="Unauthorized")
                
            # Parse the summary data
            try:
                summary = await request.json()
                
                # Save the summary to state if call_id is present
                call_id = summary.get("call_id")
                if call_id:
                    state = self.get_state(call_id) or {}
                    state["summary"] = summary
                    self.update_state(call_id, state)
                
                # Call the handler
                self.on_summary(summary)
                return {"status": "ok"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
                
        # Single SWAIG endpoint that handles all function calls (with trailing slash to avoid redirects)
        @router.post("/swaig/")
        async def handle_swaig(request: Request, response: Response):
            # Check basic auth first
            if not self._check_basic_auth(request):
                response.headers["WWW-Authenticate"] = "Basic"
                print(f"DEBUG: SWAIG unauthorized access attempt")
                return HTTPException(status_code=401, detail="Unauthorized")
                
            # Parse the request body
            body = await self._parse_request_body(request)
            
            # Get call_id and token from query params or body
            call_id = request.query_params.get("call_id", body.get("call_id"))
            token = request.query_params.get("token", body.get("token"))
            
            # Extract function name from the request body
            function_name = body.get("function")
            print(f"DEBUG: SWAIG function call received: {function_name} with call_id={call_id}")
            
            if not function_name:
                print(f"DEBUG: SWAIG missing function name in request")
                return HTTPException(status_code=400, detail="Function name not provided")
            
            # Special hooks for state tracking
            if function_name == "startup_hook":
                if not self._enable_state_tracking:
                    return {"status": "skipped", "message": "State tracking is disabled"}
                
                if not call_id or not token or not self.validate_tool_token(function_name, token, call_id):
                    return HTTPException(status_code=401, detail="Unauthorized")
                    
                # Activate the session
                self._session_manager.activate_session(call_id)
                
                # Call the hook method with the request data
                self.on_call_start(call_id, body)
                
                return {"status": "ok"}
                
            if function_name == "hangup_hook":
                if not self._enable_state_tracking:
                    return {"status": "skipped", "message": "State tracking is disabled"}
                
                if not call_id or not token or not self.validate_tool_token(function_name, token, call_id):
                    return HTTPException(status_code=401, detail="Unauthorized")
                    
                # End the session
                self._session_manager.end_session(call_id)
                
                # Call the hook method
                self.on_call_end(call_id)
                
                return {"status": "ok"}
            
            # Regular tool calls
            if function_name in self._swaig_functions and self._swaig_functions[function_name].secure:
                # First check if basic auth was successful (we've already passed that check to get here)
                # This allows either basic auth or token auth to work
                has_basic_auth = self._check_basic_auth(request)
                has_token_auth = call_id and token and self.validate_tool_token(function_name, token, call_id)
                
                if not (has_basic_auth or has_token_auth):
                    print(f"DEBUG: SWAIG authentication failed for {function_name}: basic_auth={has_basic_auth}, token_auth={has_token_auth}")
                    return HTTPException(status_code=401, detail="Unauthorized")
                    
                print(f"DEBUG: SWAIG authentication successful for {function_name} via {'basic auth' if has_basic_auth else 'token'}")
            
            # Extract arguments from the request body
            # In SWAIG, arguments come in an "argument" object with "parsed" and "raw" properties
            args = {}
            if "argument" in body and isinstance(body["argument"], dict):
                # Get the parsed arguments
                if "parsed" in body["argument"] and isinstance(body["argument"]["parsed"], list) and body["argument"]["parsed"]:
                    # Use the first item from the parsed array
                    args = body["argument"]["parsed"][0]
                    print(f"DEBUG: SWAIG extracted parsed arguments: {args}")
                elif "raw" in body["argument"]:
                    # Try to parse the raw string as JSON
                    try:
                        args = json.loads(body["argument"]["raw"])
                        print(f"DEBUG: SWAIG extracted raw arguments: {args}")
                    except:
                        print(f"DEBUG: SWAIG failed to parse raw arguments: {body['argument']['raw']}")
                        pass
            
            # Call the function
            try:
                print(f"DEBUG: SWAIG calling function {function_name} with args: {args}")
                print(f"DEBUG: SWAIG full POST data: {body}")
                
                # Pass the full request body and extracted arguments to the handler
                result = self.on_function_call(function_name, args, body)
                
                # Ensure the result is properly serialized
                if isinstance(result, SwaigFunctionResult):
                    result = result.to_dict()
                
                # Ensure the result has the proper format (just response and optional actions)
                if isinstance(result, dict):
                    # Extract only the fields we need
                    clean_result = {}
                    if "response" in result:
                        clean_result["response"] = result["response"]
                    elif "result" in result and isinstance(result["result"], dict) and "response" in result["result"]:
                        # Handle legacy format
                        clean_result["response"] = result["result"]["response"]
                        
                    # Add actions if present
                    if "actions" in result:
                        clean_result["actions"] = result["actions"]
                    elif "result" in result and isinstance(result["result"], dict) and "actions" in result["result"]:
                        clean_result["actions"] = result["result"]["actions"]
                        
                    # If no proper response found, create a default one
                    if "response" not in clean_result:
                        clean_result["response"] = "Function executed successfully."
                        
                    result = clean_result
                else:
                    # If not a dict, create a simple response
                    result = {"response": str(result)}
                    
                print(f"DEBUG: SWAIG function {function_name} result: {result}")
                
                # Log the result if we have state
                if call_id:
                    try:
                        state = self.get_state(call_id) or {}
                        events = state.setdefault("events", [])
                        events.append({
                            "type": "function_result",
                            "function": function_name,
                            "timestamp": datetime.now().isoformat(),
                            "result": result
                        })
                        self.update_state(call_id, state)
                    except Exception as e:
                        print(f"DEBUG: SWAIG error storing state: {str(e)}")
                
                return result
            except Exception as e:
                print(f"DEBUG: SWAIG error executing function {function_name}: {str(e)}")
                return {"response": f"Error: {str(e)}"}
        
        self._router = router
        return router
    
    async def _parse_request_body(self, request: Request) -> Dict[str, Any]:
        """
        Parse the request body as JSON
        
        Args:
            request: FastAPI request object
            
        Returns:
            Dictionary of request data (empty dict if not parseable)
        """
        try:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                return await request.json()
            elif "application/x-www-form-urlencoded" in content_type:
                form_data = await request.form()
                return {k: v for k, v in form_data.items()}
            else:
                # Try JSON anyway as a fallback
                text = await request.body()
                if text:
                    return json.loads(text)
                return {}
        except Exception:
            return {}
    
    def _save_request_data(self, call_id: str, data: Dict[str, Any]) -> None:
        """
        Save incoming request data without processing it
        
        This is a lightweight method called for POST requests to the main endpoint
        before a call has officially started via startup_hook.
        
        Args:
            call_id: Call ID
            data: Request data dictionary
        """
        if not data:
            return
            
        # Get or create a pending_requests entry in state
        state = self.get_state(call_id) or {}
        pending = state.setdefault("pending_requests", [])
        
        # Add this request to the pending list
        pending.append({
            "timestamp": datetime.now().isoformat(),
            "data": data
        })
        
        # Update the state
        self.update_state(call_id, state)
    
    def _process_request_data(self, call_id: str, data: Dict[str, Any]) -> None:
        """
        Process incoming request data for an active call
        
        This is called after a call has been established via startup_hook
        and can be used to update state or trigger other behaviors.
        
        Args:
            call_id: Call ID
            data: Request data dictionary
            
        Override this in subclasses to customize behavior.
        """
        if not data:
            return
            
        # Store the data in state
        state = self.get_state(call_id) or {}
        
        # Add to request history
        requests = state.setdefault("requests", [])
        requests.append({
            "timestamp": datetime.now().isoformat(),
            "data": data
        })
        
        # Store the most recent request
        state["last_request"] = {
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        # Update the state
        self.update_state(call_id, state)
    
    def serve(self, host: Optional[str] = None, port: Optional[int] = None) -> None:
        """
        Start a web server for this agent
        
        Args:
            host: Optional host to override the default
            port: Optional port to override the default
        """
        import uvicorn
        
        if self._app is None:
            app = FastAPI()
            router = self.as_router()
            # Mount the router with the route prefix to ensure endpoints work correctly
            app.include_router(router, prefix=self.route)
            self._app = app
        
        host = host or self.host
        port = port or self.port
        
        # Print the auth credentials with source
        username, password, source = self.get_basic_auth_credentials(include_source=True)
        print(f"Agent '{self.name}' is available at:")
        print(f"URL: http://{host}:{port}{self.route}")
        print(f"Basic Auth: {username}:{password} (source: {source})")
        
        # Additional info for environment variable debugging
        env_user = os.environ.get('SWML_BASIC_AUTH_USER')
        env_pass = os.environ.get('SWML_BASIC_AUTH_PASSWORD')
        
        if source != "environment" and env_user and env_pass:
            print(f"\nWARNING: Environment variables are set but not being used:")
            print(f"- SWML_BASIC_AUTH_USER: {env_user}")
            print(f"- SWML_BASIC_AUTH_PASSWORD: {env_pass}")
            print(f"Using {source} credentials instead: {username}:{password}")
            print(f"This could be because the environment variables weren't properly passed to the Python process.")
        
        uvicorn.run(self._app, host=host, port=port)
    
    def stop(self) -> None:
        """Stop the web server"""
        # This requires additional implementation for graceful shutdown
        pass

    # ----------------------------------------------------------------------
    # Call Settings
    # ----------------------------------------------------------------------
    
    def set_auto_answer(self, enabled: bool) -> 'AgentBase':
        """
        Set whether to automatically answer calls
        
        Args:
            enabled: Whether to auto-answer
            
        Returns:
            Self for method chaining
        """
        self._auto_answer = enabled
        return self
    
    def set_call_recording(self, 
                          enabled: bool, 
                          format: str = "mp4", 
                          stereo: bool = True) -> 'AgentBase':
        """
        Configure call recording settings
        
        Args:
            enabled: Whether to record calls
            format: Recording format ('mp4' or 'wav')
            stereo: Whether to record in stereo
            
        Returns:
            Self for method chaining
        """
        self._record_call = enabled
        self._record_format = format
        self._record_stereo = stereo
        return self

    # Only keep the pure post-prompt setter which is essential
    def set_post_prompt(self, text: str) -> 'AgentBase':
        """
        Set the post-prompt text for summary formatting
        
        Args:
            text: Post-prompt instructions
            
        Returns:
            Self for method chaining
        """
        self._post_prompt = text
        return self

    # ----------------------------------------------------------------------
    # State Management Methods
    # ----------------------------------------------------------------------
    
    def get_state(self, call_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the state for a call
        
        Args:
            call_id: Call session ID
            
        Returns:
            State data dictionary or None if not found
        """
        return self._state_manager.retrieve(call_id)
        
    def set_state(self, call_id: str, data: Dict[str, Any]) -> bool:
        """
        Set the state for a call (overwrites existing state)
        
        Args:
            call_id: Call session ID
            data: State data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        return self._state_manager.store(call_id, data)
        
    def update_state(self, call_id: str, data: Dict[str, Any]) -> bool:
        """
        Update the state for a call (merges with existing state)
        
        Args:
            call_id: Call session ID
            data: State data to update
            
        Returns:
            True if successful, False otherwise
        """
        return self._state_manager.update(call_id, data)
        
    def clear_state(self, call_id: str) -> bool:
        """
        Clear the state for a call
        
        Args:
            call_id: Call session ID
            
        Returns:
            True if successful, False otherwise
        """
        return self._state_manager.delete(call_id)
    
    def cleanup_expired_state(self) -> int:
        """
        Clean up expired state data
        
        Returns:
            Number of expired items cleaned up
        """
        return self._state_manager.cleanup_expired()
    
    # ----------------------------------------------------------------------
    # Hook methods for call lifecycle
    # ----------------------------------------------------------------------
    
    def on_call_start(self, call_id: str, call_data: Dict[str, Any]) -> None:
        """
        Called when a call starts (from startup_hook)
        
        This method is part of the state tracking system and initializes state storage
        when a call officially begins.
        
        Args:
            call_id: Call session ID
            call_data: Initial call data
            
        Override this in subclasses to customize behavior.
        The base implementation initializes state storage.
        """
        # Check for existing pending requests
        existing_state = self.get_state(call_id)
        pending_requests = []
        
        if existing_state:
            # Save any pending requests to process after initialization
            pending_requests = existing_state.get("pending_requests", [])
        
        # Initialize fresh state with call data
        self.set_state(call_id, {
            "call_data": call_data,
            "started_at": datetime.now().isoformat(),
            "events": [{"type": "call_start", "timestamp": datetime.now().isoformat()}],
            "active": True
        })
        
        # Process any pending requests that were received before the call officially started
        if pending_requests:
            state = self.get_state(call_id)
            state["pending_requests"] = pending_requests
            
            # Process each pending request
            for request in pending_requests:
                request_data = request.get("data", {})
                if request_data:
                    self._process_request_data(call_id, request_data)
                    
            # Clear pending requests since they've been processed
            state = self.get_state(call_id)
            if "pending_requests" in state:
                del state["pending_requests"]
                self.update_state(call_id, state)
    
    def on_call_end(self, call_id: str) -> None:
        """
        Called when a call ends (from hangup_hook)
        
        This method is part of the state tracking system and records the call end time
        when a call officially ends.
        
        Args:
            call_id: Call session ID
            
        Override this in subclasses to customize behavior.
        The base implementation records the end time but keeps the state.
        """
        # Update state with end time
        state = self.get_state(call_id)
        if state:
            state.setdefault("events", []).append({
                "type": "call_end", 
                "timestamp": datetime.now().isoformat()
            })
            state["ended_at"] = datetime.now().isoformat()
            state["active"] = False
            self.update_state(call_id, state)

    def _register_class_decorated_tools(self):
        """
        Register tools defined with the class method decorator
        """
        for _, func in inspect.getmembers(self, lambda m: hasattr(m, "_is_tool") and m._is_tool):
            if hasattr(func, "_tool_name") and hasattr(func, "_tool_params"):
                # Get the name from _tool_name attribute
                name = func._tool_name
                
                # Get the parameters from _tool_params
                tool_params = func._tool_params
                description = tool_params.get("description", func.__doc__ or f"Function {name}")
                parameters = tool_params.get("parameters", {})
                secure = tool_params.get("secure", True)
                fillers = tool_params.get("fillers", None)
                
                # Define the tool
                self.define_tool(
                    name=name,
                    description=description,
                    parameters=parameters,
                    handler=func,
                    secure=secure,
                    fillers=fillers
                )

    def add_native_function(self, function_name: str) -> 'AgentBase':
        """
        Add a native function to the agent
        
        Args:
            function_name: Name of the native function to add
            
        Returns:
            Self for method chaining
        """
        if function_name not in self.native_functions:
            self.native_functions.append(function_name)
        return self
        
    def remove_native_function(self, function_name: str) -> 'AgentBase':
        """
        Remove a native function from the agent
        
        Args:
            function_name: Name of the native function to remove
            
        Returns:
            Self for method chaining
        """
        if function_name in self.native_functions:
            self.native_functions.remove(function_name)
        return self
        
    def get_native_functions(self) -> List[str]:
        """
        Get all native functions for the agent
        
        Returns:
            List of native function names
        """
        return self.native_functions.copy()
