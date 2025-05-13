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
import traceback

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
from signalwire_agents.core.swml_service import SWMLService
from signalwire_agents.core.swml_handler import AIVerbHandler


class AgentBase(SWMLService):
    """
    Base class for all SignalWire AI Agents.
    
    This class extends SWMLService and provides enhanced functionality for building agents including:
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
        native_functions: Optional[List[str]] = None,
        schema_path: Optional[str] = None
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
            enable_state_tracking: Whether to register startup_hook and hangup_hook SWAIG functions to track conversation state
            token_expiry_secs: Seconds until tokens expire
            auto_answer: Whether to automatically answer calls
            record_call: Whether to record calls
            record_format: Recording format
            record_stereo: Whether to record in stereo
            state_manager: Optional state manager for this agent
            default_webhook_url: Optional default webhook URL for all SWAIG functions
            agent_id: Optional unique ID for this agent, generated if not provided
            native_functions: Optional list of native functions to include in the SWAIG object
            schema_path: Optional path to the schema file
        """
        # Initialize the SWMLService base class
        super().__init__(
            name=name,
            route=route,
            host=host,
            port=port,
            basic_auth=basic_auth,
            schema_path=schema_path
        )
        
        # Store agent-specific parameters
        self._default_webhook_url = default_webhook_url
        
        # Generate or use the provided agent ID
        self.agent_id = agent_id or str(uuid.uuid4())
        
        # Check for proxy URL base in environment
        self._proxy_url_base = os.environ.get('SWML_PROXY_URL_BASE')
        
        # Initialize prompt handling
        self._use_pom = use_pom
        self._raw_prompt = None
        self._post_prompt = None
        
        # Initialize POM if needed
        if self._use_pom:
            try:
                from signalwire_pom.pom import PromptObjectModel
                self.pom = PromptObjectModel()
            except ImportError:
                raise ImportError(
                    "signalwire-pom package is required for use_pom=True. "
                    "Install it with: pip install signalwire-pom"
                )
        else:
            self.pom = None
        
        # Initialize tool registry (separate from SWMLService verb registry)
        self._swaig_functions: Dict[str, SWAIGFunction] = {}
        
        # Initialize session manager
        self._session_manager = SessionManager(token_expiry_secs=token_expiry_secs)
        self._enable_state_tracking = enable_state_tracking
        
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
        
        # Register state tracking tools if enabled
        if enable_state_tracking:
            self._register_state_tracking_tools()
    
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
                elif isinstance(content, list) and content:  # Only add if non-empty
                    # List of strings - add as bullets
                    self.prompt_add_section(title, bullets=content)
                elif isinstance(content, dict):
                    # Dictionary with body/bullets/subsections
                    body = content.get('body', '')
                    bullets = content.get('bullets', [])
                    numbered = content.get('numbered', False)
                    numbered_bullets = content.get('numberedBullets', False)
                    
                    # Only create section if it has content
                    if body or bullets or 'subsections' in content:
                        # Create the section
                        self.prompt_add_section(
                            title, 
                            body=body, 
                            bullets=bullets if bullets else None,
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
                                
                                # Only add subsection if it has content
                                if sub_body or sub_bullets:
                                    self.prompt_add_subsection(
                                        title, 
                                        sub_title,
                                        body=sub_body,
                                        bullets=sub_bullets if sub_bullets else None
                                    )
        # If sections is a list of section objects, use the POM format directly
        elif isinstance(sections, list):
            if self.pom:
                # Process each section using auto-vivifying methods
                for section in sections:
                    if 'title' in section:
                        title = section['title']
                        body = section.get('body', '')
                        bullets = section.get('bullets', [])
                        numbered = section.get('numbered', False)
                        numbered_bullets = section.get('numberedBullets', False)
                        
                        # Only create section if it has content
                        if body or bullets or 'subsections' in section:
                            self.prompt_add_section(
                                title,
                                body=body,
                                bullets=bullets if bullets else None,
                                numbered=numbered,
                                numbered_bullets=numbered_bullets
                            )
                            
                            # Process subsections if any
                            subsections = section.get('subsections', [])
                            for subsection in subsections:
                                if 'title' in subsection:
                                    sub_title = subsection['title']
                                    sub_body = subsection.get('body', '')
                                    sub_bullets = subsection.get('bullets', [])
                                    
                                    # Only add subsection if it has content
                                    if sub_body or sub_bullets:
                                        self.prompt_add_subsection(
                                            title,
                                            sub_title,
                                            body=sub_body,
                                            bullets=sub_bullets if sub_bullets else None
                                        )
    
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
            self.pom = pom
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
        if self._use_pom and self.pom:
            # Check if the POM implementation supports numbered_bullets
            if hasattr(self.pom, 'add_section') and 'numbered_bullets' in inspect.signature(self.pom.add_section).parameters:
                self.pom.add_section(
                    title=title,
                    body=body,
                    bullets=bullets,
                    numbered=numbered,
                    numbered_bullets=numbered_bullets
                )
            else:
                # Fall back to compatible parameters only
                self.pom.add_section(
                    title=title,
                    body=body,
                    bullets=bullets,
                    numbered=numbered
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
        if self._use_pom and self.pom:
            self.pom.add_to_section(
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
        if self._use_pom and self.pom:
            self.pom.add_subsection(
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
            Either a string prompt or a POM object as list of dicts
        """
        # If using POM, return the POM structure
        if self._use_pom and self.pom:
            try:
                # Try different methods that might be available on the POM implementation
                if hasattr(self.pom, 'render_dict'):
                    return self.pom.render_dict()
                elif hasattr(self.pom, 'to_dict'):
                    return self.pom.to_dict()
                elif hasattr(self.pom, 'to_list'):
                    return self.pom.to_list()
                elif hasattr(self.pom, 'render'):
                    render_result = self.pom.render()
                    # If render returns a string, we need to convert it to JSON
                    if isinstance(render_result, str):
                        try:
                            import json
                            return json.loads(render_result)
                        except:
                            # If we can't parse as JSON, fall back to raw text
                            pass
                    return render_result
                else:
                    # Last resort: attempt to convert the POM object directly to a list/dict
                    # This assumes the POM object has a reasonable __str__ or __repr__ method
                    pom_data = self.pom.__dict__
                    if '_sections' in pom_data and isinstance(pom_data['_sections'], list):
                        return pom_data['_sections']
                    # Fall through to default if nothing worked
            except Exception as e:
                print(f"Error rendering POM: {e}")
                # Fall back to raw text if POM fails
                
        # Return raw text (either explicitly set or default)
        return self._raw_prompt or f"You are {self.name}, a helpful AI assistant."
    
    def get_post_prompt(self) -> Optional[str]:
        """
        Get the post-prompt for the agent
        
        Returns:
            Post-prompt text or None if not set
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
        Called when a post-prompt summary is received
        
        Args:
            summary: The summary object
        """
        # Default implementation does nothing
        pass
    
    def on_function_call(self, name: str, args: Dict[str, Any], raw_data: Optional[Dict[str, Any]] = None) -> Any:
        """
        Called when a SWAIG function is invoked
        
        Args:
            name: Function name
            args: Function arguments
            raw_data: Raw request data
            
        Returns:
            Function result
        """
        # Check if the function is registered
        if name not in self._swaig_functions:
            # If the function is not found, return an error
            return {"response": f"Function '{name}' not found"}
            
        # Get the function
        func = self._swaig_functions[name]
        
        # Call the handler
        try:
            result = func.handler(args, raw_data)
            if result is None:
                # If the handler returns None, create a default response
                result = SwaigFunctionResult("Function executed successfully")
            return result
        except Exception as e:
            # If the handler raises an exception, return an error response
            return {"response": f"Error executing function '{name}': {str(e)}"}
    
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
    
    def _create_tool_token(self, tool_name: str, call_id: str) -> str:
        """
        Create a secure token for a tool call
        
        Args:
            tool_name: Name of the tool
            call_id: Call ID for this session
            
        Returns:
            Secure token string
        """
        return self._session_manager.create_tool_token(tool_name, call_id)
    
    def validate_tool_token(self, function_name: str, token: str, call_id: str) -> bool:
        """
        Validate a tool token
        
        Args:
            function_name: Name of the function/tool
            token: Token to validate
            call_id: Call ID for the session
            
        Returns:
            True if token is valid, False otherwise
        """
        # Skip validation for non-secure tools
        if function_name not in self._swaig_functions:
            return False
            
        if not self._swaig_functions[function_name].secure:
            return True
            
        return self._session_manager.validate_tool_token(function_name, token, call_id)
    
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
        if hasattr(self, '_proxy_url_base') and self._proxy_url_base:
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
        # But NEVER add call_id parameter - it should be in the body, not the URL
        if query_params:
            # Remove any call_id from query params
            filtered_params = {k: v for k, v in query_params.items() if k != "call_id" and v}
            if filtered_params:
                params = "&".join([f"{k}={v}" for k, v in filtered_params.items()])
                url = f"{url}?{params}"
            
        return url

    def _render_swml(self, call_id: str = None) -> str:
        """
        Render the complete SWML document
        
        Args:
            call_id: Optional call ID for session-specific tokens
            
        Returns:
            SWML document as a string
        """
        # Reset the document
        self.reset_document()
        
        # Add answer verb if enabled
        if self._auto_answer:
            self.add_answer_verb()
        
        # Add record_call verb if enabled
        if self._record_call:
            self.add_verb("record_call", {
                "format": self._record_format,
                "stereo": self._record_stereo
            })
        
        # Get prompt
        prompt = self.get_prompt()
        prompt_is_pom = isinstance(prompt, list)
        
        # Get post-prompt
        post_prompt = self.get_post_prompt()
        
        # Generate a call ID if needed
        if self._enable_state_tracking and call_id is None:
            call_id = self._session_manager.create_session()
            
        # Empty query params - no need to include call_id in URLs
        query_params = {}
        
        # Get the default webhook URL with auth
        default_webhook_url = self._build_webhook_url("swaig", query_params)
        
        # Prepare SWAIG object
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
        functions = []
        
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
                function_entry["fillers"] = func.fillers
                
            # Add token to URL if we have one
            if token:
                # Create token params without call_id
                token_params = {"token": token}
                function_entry["web_hook_url"] = self._build_webhook_url("swaig", token_params)
                
            functions.append(function_entry)
            
        # Add functions array to SWAIG object if we have any
        if functions:
            swaig_obj["functions"] = functions
            
        # Add post-prompt URL if we have a post-prompt
        post_prompt_url = None
        if post_prompt:
            post_prompt_url = self._build_webhook_url("post_prompt", {})
        
        # Add AI verb
        self.add_ai_verb(
            prompt_text=None if prompt_is_pom else prompt,
            prompt_pom=prompt if prompt_is_pom else None,
            post_prompt=post_prompt,
            post_prompt_url=post_prompt_url,
            swaig=swaig_obj if swaig_obj else None
        )
        
        # Return the rendered document
        return self.render_document()
    
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
            FastAPI router
        """
        # Get the base router from SWMLService
        router = super().as_router()
        
        # Override the root endpoint to use our SWML rendering
        @router.get("/")
        @router.post("/")
        async def handle_root_no_slash(request: Request):
            return await self._handle_root_request(request)
            
        # Root endpoint - with trailing slash
        @router.get("/")
        @router.post("/")
        async def handle_root_with_slash(request: Request):
            return await self._handle_root_request(request)
            
        # Debug endpoint - without trailing slash
        @router.get("/debug")
        async def handle_debug_no_slash(request: Request):
            return await self._handle_debug_request(request)
            
        # Debug endpoint - with trailing slash
        @router.get("/debug/")
        async def handle_debug_with_slash(request: Request):
            return await self._handle_debug_request(request)
            
        # SWAIG endpoint - without trailing slash
        @router.post("/swaig")
        async def handle_swaig_no_slash(request: Request):
            return await self._handle_swaig_request(request)
            
        # SWAIG endpoint - with trailing slash
        @router.post("/swaig/")
        async def handle_swaig_with_slash(request: Request):
            return await self._handle_swaig_request(request)
            
        # Post-prompt endpoint - without trailing slash
        @router.post("/post_prompt")
        async def handle_post_prompt_no_slash(request: Request):
            return await self._handle_post_prompt_request(request)
            
        # Post-prompt endpoint - with trailing slash
        @router.post("/post_prompt/")
        async def handle_post_prompt_with_slash(request: Request):
            return await self._handle_post_prompt_request(request)
        
        self._router = router
        return router
    
    async def _handle_root_request(self, request: Request):
        """Handle GET/POST requests to the root endpoint"""
        print(f"ROOT ENDPOINT CALLED WITH METHOD: {request.method}")
        print(f"PATH: {request.url.path}")
        
        try:
            # Check auth
            if not self._check_basic_auth(request):
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
                    print(f"Received POST data: {body}")
                except Exception as e:
                    print(f"Error parsing POST data: {str(e)}")
                    try:
                        body_text = await request.body()
                        print(f"Raw POST body: {body_text}")
                    except:
                        pass
                        
                # Get call_id from body if present
                call_id = body.get("call_id")
            else:
                # Get call_id from query params for GET
                call_id = request.query_params.get("call_id")
                
            # Print the call_id if any
            if call_id:
                print(f"Call ID: {call_id}")
            
            # Allow subclasses to inspect/modify the request
            modifications = None
            if body:
                modifications = self.on_swml_request(body)
            
            # Render SWML
            swml = self._render_swml(call_id, modifications)
            print(f"ROOT: Rendered SWML, length: {len(swml)}")
            
            # Return as JSON
            return Response(
                content=swml,
                media_type="application/json"
            )
        except Exception as e:
            print("ROOT ERROR:", str(e))
            traceback.print_exc()
            return Response(
                content=json.dumps({"error": str(e)}),
                status_code=500,
                media_type="application/json"
            )
    
    async def _handle_debug_request(self, request: Request):
        """Handle GET requests to the debug endpoint"""
        print("DEBUG ENDPOINT CALLED!")
        print(f"PATH: {request.url.path}")
        
        try:
            # Check auth
            if not self._check_basic_auth(request):
                return Response(
                    content=json.dumps({"error": "Unauthorized"}),
                    status_code=401,
                    headers={"WWW-Authenticate": "Basic"},
                    media_type="application/json"
                )
            
            # Render SWML
            swml = self._render_swml()
            print(f"DEBUG: Rendered SWML, length: {len(swml)}")
            print(f"DEBUG: SWML first 200 chars: {swml[:200]}")
            
            # Return as JSON
            return Response(
                content=swml,
                media_type="application/json",
                headers={"X-Debug": "true"}
            )
        except Exception as e:
            print("DEBUG ERROR:", str(e))
            traceback.print_exc()
            return Response(
                content=json.dumps({"error": str(e)}),
                status_code=500,
                media_type="application/json"
            )
    
    async def _handle_swaig_request(self, request: Request):
        """Handle POST requests to the SWAIG endpoint"""
        print("SWAIG ENDPOINT CALLED!")
        print(f"PATH: {request.url.path}")
        
        try:
            # Check auth
            if not self._check_basic_auth(request):
                return Response(
                    content=json.dumps({"error": "Unauthorized"}),
                    status_code=401,
                    headers={"WWW-Authenticate": "Basic"},
                    media_type="application/json"
                )
            
            # Parse request
            try:
                body = await request.json()
            except Exception:
                body = {}
            
            # Extract function name
            function_name = body.get("function")
            if not function_name:
                return Response(
                    content=json.dumps({"error": "Missing function name"}),
                    status_code=400,
                    media_type="application/json"
                )
            
            print(f"Function called: {function_name}")
            
            # Extract arguments
            args = {}
            if "argument" in body and isinstance(body["argument"], dict):
                if "parsed" in body["argument"] and isinstance(body["argument"]["parsed"], list) and body["argument"]["parsed"]:
                    args = body["argument"]["parsed"][0]
                elif "raw" in body["argument"]:
                    try:
                        args = json.loads(body["argument"]["raw"])
                    except:
                        pass
            
            # Call the function
            result = self.on_function_call(function_name, args, body)
            
            # Convert result to dict if needed
            if isinstance(result, SwaigFunctionResult):
                result_dict = result.to_dict()
            elif isinstance(result, dict):
                result_dict = result
            else:
                result_dict = {"response": str(result)}
            
            return result_dict
        except Exception as e:
            print("SWAIG ERROR:", str(e))
            traceback.print_exc()
            return Response(
                content=json.dumps({"error": str(e)}),
                status_code=500,
                media_type="application/json"
            )

    def _check_basic_auth(self, request):
        """Check if the request has valid basic auth credentials"""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Basic "):
            return False
            
        try:
            # Extract and decode credentials
            auth_data = auth_header.replace("Basic ", "")
            decoded = base64.b64decode(auth_data).decode("utf-8")
            username, password = decoded.split(":", 1)
            
            # Check against expected credentials
            expected_username, expected_password = self._basic_auth
            return username == expected_username and password == expected_password
        except Exception as e:
            print(f"Auth error: {str(e)}")
            return False

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
        Set call recording parameters
        
        Args:
            enabled: Whether to record calls
            format: Recording format
            stereo: Whether to record in stereo
            
        Returns:
            Self for method chaining
        """
        self._record_call = enabled
        self._record_format = format
        self._record_stereo = stereo
        return self

    def set_post_prompt(self, text: str) -> 'AgentBase':
        """
        Set the post-prompt for the agent
        
        Args:
            text: Post-prompt text
            
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
            call_id: Call ID to get state for
            
        Returns:
            Call state or None if not found
        """
        return self._state_manager.get_state(call_id)
        
    def set_state(self, call_id: str, data: Dict[str, Any]) -> bool:
        """
        Set the state for a call
        
        Args:
            call_id: Call ID to set state for
            data: State data to set
            
        Returns:
            True if state was set, False otherwise
        """
        return self._state_manager.set_state(call_id, data)
        
    def update_state(self, call_id: str, data: Dict[str, Any]) -> bool:
        """
        Update the state for a call
        
        Args:
            call_id: Call ID to update state for
            data: State data to update
            
        Returns:
            True if state was updated, False otherwise
        """
        return self._state_manager.update_state(call_id, data)
        
    def clear_state(self, call_id: str) -> bool:
        """
        Clear the state for a call
        
        Args:
            call_id: Call ID to clear state for
            
        Returns:
            True if state was cleared, False otherwise
        """
        return self._state_manager.clear_state(call_id)
        
    def cleanup_expired_state(self) -> int:
        """
        Clean up expired state
        
        Returns:
            Number of expired state entries removed
        """
        return self._state_manager.cleanup_expired()
    
    # ----------------------------------------------------------------------
    # Hook methods for call lifecycle
    # ----------------------------------------------------------------------
    
    def _register_class_decorated_tools(self):
        """
        Register all tools decorated with @AgentBase.tool
        """
        for name in dir(self):
            attr = getattr(self, name)
            if callable(attr) and hasattr(attr, "_is_tool"):
                # Get tool parameters
                tool_name = getattr(attr, "_tool_name", name)
                tool_params = getattr(attr, "_tool_params", {})
                
                # Extract parameters
                parameters = tool_params.get("parameters", {})
                description = tool_params.get("description", attr.__doc__ or f"Function {tool_name}")
                secure = tool_params.get("secure", True)
                fillers = tool_params.get("fillers", None)
                
                # Create a wrapper that binds the method to this instance
                def make_wrapper(method):
                    @functools.wraps(method)
                    def wrapper(args, raw_data=None):
                        return method(args, raw_data)
                    return wrapper
                
                # Register the tool
                self.define_tool(
                    name=tool_name,
                    description=description,
                    parameters=parameters,
                    handler=make_wrapper(attr),
                    secure=secure,
                    fillers=fillers
                )

    def add_native_function(self, function_name: str) -> 'AgentBase':
        """
        Add a native function to the SWAIG object
        
        Args:
            function_name: Name of the native function
            
        Returns:
            Self for method chaining
        """
        if function_name not in self.native_functions:
            self.native_functions.append(function_name)
        return self
        
    def remove_native_function(self, function_name: str) -> 'AgentBase':
        """
        Remove a native function from the SWAIG object
        
        Args:
            function_name: Name of the native function
            
        Returns:
            Self for method chaining
        """
        if function_name in self.native_functions:
            self.native_functions.remove(function_name)
        return self
        
    def get_native_functions(self) -> List[str]:
        """
        Get the list of native functions
        
        Returns:
            List of native function names
        """
        return self.native_functions.copy()

    def has_section(self, title: str) -> bool:
        """
        Check if a section exists in the prompt
        
        Args:
            title: Section title
            
        Returns:
            True if the section exists, False otherwise
        """
        if not self._use_pom or not self.pom:
            return False
            
        return self.pom.has_section(title)

    def _register_state_tracking_tools(self):
        """
        Register tools for tracking conversation state
        """
        # Register startup hook
        self.define_tool(
            name="startup_hook",
            description="Called when the conversation starts",
            parameters={},
            handler=self._startup_hook_handler,
            secure=False
        )
        
        # Register hangup hook
        self.define_tool(
            name="hangup_hook",
            description="Called when the conversation ends",
            parameters={},
            handler=self._hangup_hook_handler,
            secure=False
        )
    
    def _startup_hook_handler(self, args, raw_data):
        """
        Handler for the startup hook
        
        Args:
            args: Function arguments
            raw_data: Raw request data
            
        Returns:
            Function result
        """
        # Extract call ID
        call_id = raw_data.get("call_id") if raw_data else None
        if not call_id:
            return SwaigFunctionResult("Error: Missing call_id")
            
        # Activate the session
        self._session_manager.activate_session(call_id)
        
        # Initialize state
        self.set_state(call_id, {
            "start_time": datetime.now().isoformat(),
            "events": []
        })
        
        return SwaigFunctionResult("Call started and session activated")
    
    def _hangup_hook_handler(self, args, raw_data):
        """
        Handler for the hangup hook
        
        Args:
            args: Function arguments
            raw_data: Raw request data
            
        Returns:
            Function result
        """
        # Extract call ID
        call_id = raw_data.get("call_id") if raw_data else None
        if not call_id:
            return SwaigFunctionResult("Error: Missing call_id")
            
        # End the session
        self._session_manager.end_session(call_id)
        
        # Update state
        state = self.get_state(call_id) or {}
        state["end_time"] = datetime.now().isoformat()
        self.update_state(call_id, state)
        
        return SwaigFunctionResult("Call ended and session deactivated")

    def on_swml_request(self, request_data: Optional[dict] = None) -> Optional[dict]:
        """
        Called when SWML is requested, with request data when available.
        
        Subclasses can override this to inspect or modify SWML based on the request.
        
        Args:
            request_data: Optional dictionary containing the parsed POST body
            
        Returns:
            Optional dict to modify/augment the SWML document
        """
        # Default implementation does nothing
        return None

    def _render_swml(self, call_id: str = None, modifications: Optional[dict] = None) -> str:
        """
        Render the complete SWML document
        
        Args:
            call_id: Optional call ID for session-specific tokens
            modifications: Optional dict of modifications to apply to the SWML
            
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
            
        # Empty query params - no need to include call_id in URLs
        query_params = {}
        
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
                token = self._session_manager.create_token(tool_name=name, call_id=call_id)
                
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
                function_entry["fillers"] = func.fillers
                
            # Add token to URL if we have one
            if token:
                # Create token params without call_id
                token_params = {"token": token}
                function_entry["web_hook_url"] = self._build_webhook_url("swaig", token_params)
                
            swaig_functions.append(function_entry)
            
        # Add functions array to SWAIG object if we have any
        if swaig_functions:
            swaig_obj["functions"] = swaig_functions
            
        # Add post-prompt URL if we have a post-prompt
        post_prompt_url = None
        if post_prompt:
            post_prompt_url = self._build_webhook_url("post_prompt", {})
        
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
            
        # Apply any modifications from the callback
        if modifications and isinstance(modifications, dict):
            # Simple recursive update function
            def update_dict(target, source):
                for key, value in source.items():
                    if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                        update_dict(target[key], value)
                    else:
                        target[key] = value
            
            update_dict(swml, modifications)
            
        # Return SWML as a string (will be converted to JSON by the endpoint)
        return json.dumps(swml)

    async def _handle_post_prompt_request(self, request: Request):
        """Handle POST requests to the post_prompt endpoint"""
        print("POST_PROMPT ENDPOINT CALLED!")
        print(f"PATH: {request.url.path}")
        
        try:
            # Check auth
            if not self._check_basic_auth(request):
                return Response(
                    content=json.dumps({"error": "Unauthorized"}),
                    status_code=401,
                    headers={"WWW-Authenticate": "Basic"},
                    media_type="application/json"
                )
            
            # Parse request body
            try:
                body = await request.json()
                print(f"POST_PROMPT body: {body}")
            except Exception as e:
                print(f"Error parsing POST_PROMPT data: {str(e)}")
                body = {}
                
            # Extract summary from the request
            ai_response = body.get("ai_response", {})
            summary = ai_response.get("summary")
            
            # Log the summary
            print(f"Received summary: {summary}")
            
            # Save state if call_id is provided
            call_id = body.get("call_id")
            if call_id and summary:
                state = self.get_state(call_id) or {}
                state["summary"] = summary
                self.update_state(call_id, state)
            
            # Call the summary handler
            if summary:
                self.on_summary(summary)
            
            # Return success
            return {"success": True}
        except Exception as e:
            print("POST_PROMPT ERROR:", str(e))
            traceback.print_exc()
            return Response(
                content=json.dumps({"error": str(e)}),
                status_code=500,
                media_type="application/json"
            )

    def _register_routes(self, app):
        """Register all routes for the agent, with both slash variants and both HTTP methods"""
        
        print(f"Registering routes for agent '{self.name}' at path '{self.route}'")
        
        # Root endpoint - without trailing slash
        @app.get(f"{self.route}")
        @app.post(f"{self.route}")
        async def handle_root_no_slash(request: Request):
            return await self._handle_root_request(request)
            
        # Root endpoint - with trailing slash
        @app.get(f"{self.route}/")
        @app.post(f"{self.route}/")
        async def handle_root_with_slash(request: Request):
            return await self._handle_root_request(request)
            
        # Debug endpoint - without trailing slash
        @app.get(f"{self.route}/debug")
        async def handle_debug_no_slash(request: Request):
            return await self._handle_debug_request(request)
            
        # Debug endpoint - with trailing slash
        @app.get(f"{self.route}/debug/")
        async def handle_debug_with_slash(request: Request):
            return await self._handle_debug_request(request)
            
        # SWAIG endpoint - without trailing slash
        @app.post(f"{self.route}/swaig")
        async def handle_swaig_no_slash(request: Request):
            return await self._handle_swaig_request(request)
            
        # SWAIG endpoint - with trailing slash
        @app.post(f"{self.route}/swaig/")
        async def handle_swaig_with_slash(request: Request):
            return await self._handle_swaig_request(request)
        
        print(f"Registering post_prompt routes for: {self.route}/post_prompt and {self.route}/post_prompt/")
            
        # Post-prompt endpoint - without trailing slash
        @app.post(f"{self.route}/post_prompt")
        async def handle_post_prompt_no_slash(request: Request):
            return await self._handle_post_prompt_request(request)
            
        # Post-prompt endpoint - with trailing slash
        @app.post(f"{self.route}/post_prompt/")
        async def handle_post_prompt_with_slash(request: Request):
            return await self._handle_post_prompt_request(request)
        
        # Print all registered routes for debugging
        print("Registered routes:")
        for route in app.routes:
            print(f"  {route.methods} {route.path}")
