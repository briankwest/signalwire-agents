"""
AgentBase - Core foundation class for all SignalWire AI Agents
"""

import functools
import inspect
import os
from typing import Dict, List, Any, Optional, Union, Callable, Tuple, Type, TypeVar
import base64
import secrets
from urllib.parse import urlparse

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
from signalwire_agents.core.swaig_function import SwaigFunction
from signalwire_agents.core.function_result import SwaigFunctionResult
from signalwire_agents.core.swml_renderer import SwmlRenderer
from signalwire_agents.core.security.session_manager import SessionManager


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
        per_call_sessions: bool = True,
        token_expiry_secs: int = 600
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
            per_call_sessions: Whether to use per-call security sessions
            token_expiry_secs: Seconds until tokens expire
        """
        self.name = name
        self.route = route.rstrip("/")  # Ensure no trailing slash
        self.host = host
        self.port = port
        
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
        self._tools: Dict[str, SwaigFunction] = {}
        
        # Initialize session manager
        self._session_manager = SessionManager(token_expiry_secs=token_expiry_secs)
        self._per_call_sessions = per_call_sessions
        
        # Server state
        self._app = None
        self._router = None
        self._running = False
        
        # Register the tool decorator on this instance
        self.tool = self._tool_decorator
        
        # Process declarative PROMPT_SECTIONS if defined in subclass
        self._process_prompt_sections()
    
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
    
    # Legacy/shorthand methods - these are defined in terms of the more general methods above
    # They're maintained for backward compatibility and convenience
    
    def set_personality(self, text: str) -> 'AgentBase':
        """
        Set the agent's personality description
        
        Args:
            text: Personality description
            
        Returns:
            Self for method chaining
        """
        return self.prompt_add_section("Personality", body=text)
    
    def set_goal(self, text: str) -> 'AgentBase':
        """
        Set the agent's goal/objective
        
        Args:
            text: Goal description
            
        Returns:
            Self for method chaining
        """
        return self.prompt_add_section("Goal", body=text)
    
    def add_instruction(self, text: str) -> 'AgentBase':
        """
        Add an instruction bullet point
        
        Args:
            text: Instruction text
            
        Returns:
            Self for method chaining
        """
        return self.prompt_add_to_section("Instructions", bullet=text)
    
    def add_example(self, title: str, body: str) -> 'AgentBase':
        """
        Add an example interaction
        
        Args:
            title: Example title/summary
            body: Example text
            
        Returns:
            Self for method chaining
        """
        if not self._pom_builder.has_section("Examples"):
            self.prompt_add_section("Examples")
        return self.prompt_add_subsection("Examples", title, body=body)
    
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
    # Tool/Function Management
    # ----------------------------------------------------------------------
    
    def define_tool(
        self, 
        name: str, 
        description: str, 
        parameters: Dict[str, Any], 
        handler: Callable,
        secure: bool = True
    ) -> 'AgentBase':
        """
        Define a SWAIG function that the AI can call
        
        Args:
            name: Function name (must be unique)
            description: Function description for the AI
            parameters: JSON Schema of parameters
            handler: Function to call when invoked
            secure: Whether to require token validation
            
        Returns:
            Self for method chaining
        """
        if name in self._tools:
            raise ValueError(f"Tool with name '{name}' already exists")
            
        self._tools[name] = SwaigFunction(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            secure=secure
        )
        return self
    
    def _tool_decorator(self, name=None, **kwargs):
        """
        Decorator for defining SWAIG tools in a class
        
        Used as:
        
        @agent.tool(name="get_weather", parameters={...})
        def get_weather(self, location):
            # ...
        """
        def decorator(func):
            nonlocal name
            if name is None:
                name = func.__name__
                
            parameters = kwargs.get("parameters", {})
            description = kwargs.get("description", func.__doc__ or f"Function {name}")
            secure = kwargs.get("secure", True)
            
            self.define_tool(
                name=name,
                description=description,
                parameters=parameters,
                handler=func,
                secure=secure
            )
            return func
        return decorator
    
    @classmethod
    def tool(cls, name=None, **kwargs):
        """
        Class method decorator for defining SWAIG tools
        
        Used as:
        
        @AgentBase.tool(name="get_weather", parameters={...})
        def get_weather(self, location):
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
    
    def define_tools(self) -> List[SwaigFunction]:
        """
        Define the tools this agent can use
        
        Returns:
            List of SwaigFunction objects
            
        This method can be overridden by subclasses.
        """
        return list(self._tools.values())
    
    def on_summary(self, summary: Dict[str, Any]) -> None:
        """
        Handle the post-prompt summary result
        
        Args:
            summary: Summary data from post_prompt
            
        This method should be overridden by subclasses.
        """
        pass
    
    def on_function_call(self, name: str, args: Dict[str, Any]) -> Any:
        """
        Handle a function call if not handled by a specific function
        
        Args:
            name: Function name
            args: Function arguments
            
        Returns:
            Function result
            
        This method can be overridden by subclasses.
        """
        if name not in self._tools:
            return SwaigFunctionResult(f"Function '{name}' not found").to_dict()
            
        return self._tools[name].execute(args)
    
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
        if not self._per_call_sessions:
            # Simple token comparison if not using session management
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
    
    def get_full_url(self) -> str:
        """
        Get the full URL for this agent's endpoint
        
        Returns:
            Full URL including host, port, and route
        """
        if self.host in ("0.0.0.0", "127.0.0.1", "localhost"):
            host = "localhost"
        else:
            host = self.host
            
        return f"http://{host}:{self.port}{self.route}"
    
    def _build_post_prompt_url(self) -> str:
        """
        Build the URL for post_prompt webhook
        
        Returns:
            Full URL with basic auth
        """
        url = urlparse(f"{self.get_full_url()}/post_prompt")
        username, password = self._basic_auth
        return url._replace(netloc=f"{username}:{password}@{url.netloc}").geturl()
    
    def _build_hook_url(self, hook_name: str, call_id: str, token: str) -> str:
        """
        Build the URL for a hook function
        
        Args:
            hook_name: Hook name (startup_hook or hangup_hook)
            call_id: Call session ID
            token: Security token
            
        Returns:
            Full URL with query parameters
        """
        return f"{self.get_full_url()}/tools/{hook_name}?token={token}&call_id={call_id}"
    
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
        
        # Calculate URLs
        post_prompt_url = self._build_post_prompt_url() if post_prompt else None
        
        # Generate a call ID if needed
        if self._per_call_sessions and call_id is None:
            call_id = self._session_manager.create_session()
            
        # Prepare SWAIG functions
        swaig_functions = []
        for tool in self.define_tools():
            if self._per_call_sessions:
                token = self._session_manager.generate_token(call_id, tool.name)
                swaig_functions.append(tool.to_swaig(
                    base_url=self.get_full_url(),
                    token=token,
                    call_id=call_id
                ))
            else:
                swaig_functions.append(tool.to_swaig(
                    base_url=self.get_full_url()
                ))
        
        # Add hooks for session management
        startup_hook_url = None
        hangup_hook_url = None
        
        if self._per_call_sessions:
            startup_token = self._session_manager.generate_token(call_id, "startup_hook")
            hangup_token = self._session_manager.generate_token(call_id, "hangup_hook")
            
            startup_hook_url = self._build_hook_url("startup_hook", call_id, startup_token)
            hangup_hook_url = self._build_hook_url("hangup_hook", call_id, hangup_token)
        
        # Render SWML
        return SwmlRenderer.render_swml(
            prompt=prompt,
            post_prompt=post_prompt,
            post_prompt_url=post_prompt_url,
            swaig_functions=swaig_functions,
            startup_hook_url=startup_hook_url,
            hangup_hook_url=hangup_hook_url,
            prompt_is_pom=prompt_is_pom
        )
    
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
        
        # Main SWML endpoint
        @router.get("/")
        async def get_swml(request: Request, response: Response):
            # Check auth
            if not self._check_basic_auth(request):
                response.headers["WWW-Authenticate"] = "Basic"
                return HTTPException(status_code=401, detail="Unauthorized")
                
            # Generate SWML
            call_id = request.query_params.get("call_id")
            return self._render_swml(call_id)
        
        # Post-prompt webhook
        @router.post("/post_prompt")
        async def handle_post_prompt(request: Request, response: Response):
            # Check auth
            if not self._check_basic_auth(request):
                response.headers["WWW-Authenticate"] = "Basic"
                return HTTPException(status_code=401, detail="Unauthorized")
                
            # Parse the summary data
            try:
                summary = await request.json()
                self.on_summary(summary)
                return {"status": "ok"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        
        # Tool/function calls
        @router.post("/tools/{function_name}")
        async def handle_tool(function_name: str, request: Request):
            # Special hooks don't need auth validation
            if function_name == "startup_hook":
                call_id = request.query_params.get("call_id")
                token = request.query_params.get("token")
                
                if not call_id or not token or not self.validate_tool_token(function_name, token, call_id):
                    return HTTPException(status_code=401, detail="Unauthorized")
                    
                self._session_manager.activate_session(call_id)
                return {"status": "ok"}
                
            if function_name == "hangup_hook":
                call_id = request.query_params.get("call_id")
                token = request.query_params.get("token")
                
                if not call_id or not token or not self.validate_tool_token(function_name, token, call_id):
                    return HTTPException(status_code=401, detail="Unauthorized")
                    
                self._session_manager.end_session(call_id)
                return {"status": "ok"}
            
            # Regular tool calls
            call_id = request.query_params.get("call_id")
            token = request.query_params.get("token")
            
            # Check if tool exists and requires validation
            if function_name in self._tools and self._tools[function_name].secure:
                if not call_id or not token or not self.validate_tool_token(function_name, token, call_id):
                    return HTTPException(status_code=401, detail="Unauthorized")
            
            # Parse arguments
            try:
                args = await request.json()
            except Exception:
                args = {}
                
            # Call the function
            try:
                result = self.on_function_call(function_name, args)
                return result
            except Exception as e:
                return {"status": "error", "error": {"message": str(e)}}
        
        self._router = router
        return router
    
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
