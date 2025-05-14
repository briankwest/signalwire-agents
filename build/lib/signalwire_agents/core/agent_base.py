"""
AgentBase - Core foundation class for all SignalWire AI Agents
"""

import functools
import inspect
import os
import sys
import uuid
import tempfile
import traceback
from typing import Dict, List, Any, Optional, Union, Callable, Tuple, Type, TypeVar
import base64
import secrets
from urllib.parse import urlparse
import json
from datetime import datetime
import re

try:
    import fastapi
    from fastapi import FastAPI, APIRouter, Depends, HTTPException, Query, Body, Request, Response
    from fastapi.security import HTTPBasic, HTTPBasicCredentials
    from pydantic import BaseModel
except ImportError:
    raise ImportError(
        "fastapi is required. Install it with: pip install fastapi"
    )

try:
    import uvicorn
except ImportError:
    raise ImportError(
        "uvicorn is required. Install it with: pip install uvicorn"
    )

try:
    import structlog
    # Configure structlog only if not already configured
    if not structlog.is_configured():
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
except ImportError:
    raise ImportError(
        "structlog is required. Install it with: pip install structlog"
    )

from signalwire_agents.core.pom_builder import PomBuilder
from signalwire_agents.core.swaig_function import SWAIGFunction
from signalwire_agents.core.function_result import SwaigFunctionResult
from signalwire_agents.core.swml_renderer import SwmlRenderer
from signalwire_agents.core.security.session_manager import SessionManager
from signalwire_agents.core.state import StateManager, FileStateManager
from signalwire_agents.core.swml_service import SWMLService
from signalwire_agents.core.swml_handler import AIVerbHandler

# Create a logger
logger = structlog.get_logger("agent_base")

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
        schema_path: Optional[str] = None,
        suppress_logs: bool = False
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
            suppress_logs: Whether to suppress structured logs
        """
        # Import SWMLService here to avoid circular imports
        from signalwire_agents.core.swml_service import SWMLService
        
        # If schema_path is not provided, we'll let SWMLService find it through its _find_schema_path method
        # which will be called in its __init__
        
        # Initialize the SWMLService base class
        super().__init__(
            name=name,
            route=route,
            host=host,
            port=port,
            basic_auth=basic_auth,
            schema_path=schema_path
        )
        
        # Log the schema path if found and not suppressing logs
        if self.schema_utils and self.schema_utils.schema_path and not suppress_logs:
            print(f"Using schema.json at: {self.schema_utils.schema_path}")
        
        # Setup logger for this instance
        self.log = logger.bind(agent=name)
        self.log.info("agent_initializing", route=route, host=host, port=port)
        
        # Store agent-specific parameters
        self._default_webhook_url = default_webhook_url
        self._suppress_logs = suppress_logs
        
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
        
        # Initialize new configuration containers
        self._hints = []
        self._languages = []
        self._pronounce = []
        self._params = {}
        self._global_data = {}
        self._function_includes = []
    
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
        numbered_bullets: bool = False,
        subsections: Optional[List[Dict[str, Any]]] = None
    ) -> 'AgentBase':
        """
        Add a section to the prompt
        
        Args:
            title: Section title
            body: Optional section body text
            bullets: Optional list of bullet points
            numbered: Whether this section should be numbered
            numbered_bullets: Whether bullets should be numbered
            subsections: Optional list of subsection objects
            
        Returns:
            Self for method chaining
        """
        if self._use_pom and self.pom:
            # Create parameters for add_section based on what's supported
            kwargs = {}
            
            # Start with basic parameters
            kwargs['title'] = title
            kwargs['body'] = body
            if bullets:
                kwargs['bullets'] = bullets
            
            # Add optional parameters if they look supported
            if hasattr(self.pom, 'add_section'):
                sig = inspect.signature(self.pom.add_section)
                if 'numbered' in sig.parameters:
                    kwargs['numbered'] = numbered
                if 'numberedBullets' in sig.parameters:
                    kwargs['numberedBullets'] = numbered_bullets
            
            # Create the section
            section = self.pom.add_section(**kwargs)
            
            # Now add subsections if provided, by calling add_subsection on the section
            if subsections:
                for subsection in subsections:
                    if 'title' in subsection:
                        section.add_subsection(
                            title=subsection.get('title'),
                            body=subsection.get('body', ''),
                            bullets=subsection.get('bullets', [])
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
            # First find or create the parent section
            parent_section = None
            
            # Try to find the parent section by title
            if hasattr(self.pom, 'sections'):
                for section in self.pom.sections:
                    if hasattr(section, 'title') and section.title == parent_title:
                        parent_section = section
                        break
            
            # If parent section not found, create it
            if not parent_section:
                parent_section = self.pom.add_section(title=parent_title)
            
            # Now call add_subsection on the parent section object, not on POM
            parent_section.add_subsection(
                title=title,
                body=body,
                bullets=bullets or []
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
    
    def on_summary(self, summary: Optional[Dict[str, Any]], raw_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Called when a post-prompt summary is received
        
        Args:
            summary: The summary object or None if no summary was found
            raw_data: The complete raw POST data from the request
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

    def _render_swml(self, call_id: str = None, modifications: Optional[dict] = None) -> str:
        """
        Render the complete SWML document using SWMLService methods
        
        Args:
            call_id: Optional call ID for session-specific tokens
            modifications: Optional dict of modifications to apply to the SWML
            
        Returns:
            SWML document as a string
        """
        # Reset the document to a clean state
        self.reset_document()
        
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
        
        # Add includes if any are defined
        if self._function_includes:
            swaig_obj["includes"] = self._function_includes
        
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
        
        # Add answer verb with auto-answer enabled
        self.add_answer_verb()
        
        # Use the AI verb handler to build and validate the AI verb config
        ai_config = {}
        
        # Get the AI verb handler
        ai_handler = self.verb_registry.get_handler("ai")
        if ai_handler:
            try:
                # Build AI config using the proper handler
                ai_config = ai_handler.build_config(
                    prompt_text=None if prompt_is_pom else prompt,
                    prompt_pom=prompt if prompt_is_pom else None,
                    post_prompt=post_prompt,
                    post_prompt_url=post_prompt_url,
                    swaig=swaig_obj if swaig_obj else None
                )
                
                # Add new configuration parameters to the AI config
                
                # Add hints if any
                if self._hints:
                    ai_config["hints"] = self._hints
                
                # Add languages if any
                if self._languages:
                    ai_config["languages"] = self._languages
                
                # Add pronunciation rules if any
                if self._pronounce:
                    ai_config["pronounce"] = self._pronounce
                
                # Add params if any
                if self._params:
                    ai_config["params"] = self._params
                
                # Add global_data if any
                if self._global_data:
                    ai_config["global_data"] = self._global_data
                    
            except ValueError as e:
                if not self._suppress_logs:
                    print(f"Error building AI verb configuration: {str(e)}")
        else:
            # Fallback if no handler (shouldn't happen but just in case)
            ai_config = {
                "prompt": {
                    "text" if not prompt_is_pom else "pom": prompt
                }
            }
            
            if post_prompt:
                ai_config["post_prompt"] = {"text": post_prompt}
                if post_prompt_url:
                    ai_config["post_prompt_url"] = post_prompt_url
                
            if swaig_obj:
                ai_config["SWAIG"] = swaig_obj
        
        # Add the new configurations if not already added by the handler
        if self._hints and "hints" not in ai_config:
            ai_config["hints"] = self._hints
        
        if self._languages and "languages" not in ai_config:
            ai_config["languages"] = self._languages
        
        if self._pronounce and "pronounce" not in ai_config:
            ai_config["pronounce"] = self._pronounce
        
        if self._params and "params" not in ai_config:
            ai_config["params"] = self._params
        
        if self._global_data and "global_data" not in ai_config:
            ai_config["global_data"] = self._global_data
        
        # Add the AI verb to the document
        self.add_verb("ai", ai_config)
        
        # Apply any modifications from the callback
        if modifications and isinstance(modifications, dict):
            # We need a way to apply modifications to the document
            # Get the current document
            document = self.get_document()
            
            # Simple recursive update function
            def update_dict(target, source):
                for key, value in source.items():
                    if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                        update_dict(target[key], value)
                    else:
                        target[key] = value
            
            # Apply modifications to the document
            update_dict(document, modifications)
            
            # Since we can't directly set the document in SWMLService, 
            # we'll need to reset and rebuild if there are modifications
            self.reset_document()
            
            # Add the modified document's sections
            for section_name, section_content in document["sections"].items():
                if section_name != "main":  # Main section is created by default
                    self.add_section(section_name)
                
                # Add each verb to the section
                for verb_obj in section_content:
                    for verb_name, verb_config in verb_obj.items():
                        self.add_verb_to_section(section_name, verb_name, verb_config)
        
        # Return the rendered document as a string
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
        @router.post("/debug")
        async def handle_debug_no_slash(request: Request):
            return await self._handle_debug_request(request)
            
        # Debug endpoint - with trailing slash
        @router.get("/debug/")
        @router.post("/debug/")
        async def handle_debug_with_slash(request: Request):
            return await self._handle_debug_request(request)
            
        # SWAIG endpoint - without trailing slash
        @router.get("/swaig")
        @router.post("/swaig")
        async def handle_swaig_no_slash(request: Request):
            return await self._handle_swaig_request(request)
            
        # SWAIG endpoint - with trailing slash
        @router.get("/swaig/")
        @router.post("/swaig/")
        async def handle_swaig_with_slash(request: Request):
            return await self._handle_swaig_request(request)
            
        # Post-prompt endpoint - without trailing slash
        @router.get("/post_prompt")
        @router.post("/post_prompt")
        async def handle_post_prompt_no_slash(request: Request):
            return await self._handle_post_prompt_request(request)
            
        # Post-prompt endpoint - with trailing slash
        @router.get("/post_prompt/")
        @router.post("/post_prompt/")
        async def handle_post_prompt_with_slash(request: Request):
            return await self._handle_post_prompt_request(request)
        
        self._router = router
        return router
    
    async def _handle_root_request(self, request: Request):
        """Handle GET/POST requests to the root endpoint"""
        req_log = self.log.bind(
            endpoint="root",
            method=request.method,
            path=request.url.path
        )
        
        req_log.debug("endpoint_called")
        
        try:
            # Check auth
            if not self._check_basic_auth(request):
                req_log.warning("unauthorized_access_attempt")
                return Response(
                    content=json.dumps({"error": "Unauthorized"}),
                    status_code=401,
                    headers={"WWW-Authenticate": "Basic"},
                    media_type="application/json"
                )
            
            # Try to parse request body for POST
            body = {}
            call_id = None
            
            if request.method == "POST":
                # Check if body is empty first
                raw_body = await request.body()
                if raw_body:
                    try:
                        body = await request.json()
                        req_log.debug("request_body_received", body_size=len(str(body)))
                        if body:
                            req_log.debug("request_body", body=json.dumps(body, indent=2))
                    except Exception as e:
                        req_log.warning("error_parsing_request_body", error=str(e), traceback=traceback.format_exc())
                        req_log.debug("raw_request_body", body=raw_body.decode('utf-8', errors='replace'))
                        # Continue processing with empty body
                        body = {}
                else:
                    req_log.debug("empty_request_body")
                    
                # Get call_id from body if present
                call_id = body.get("call_id")
            else:
                # Get call_id from query params for GET
                call_id = request.query_params.get("call_id")
                
            # Add call_id to logger if any
            if call_id:
                req_log = req_log.bind(call_id=call_id)
                req_log.debug("call_id_identified")
            
            # Allow subclasses to inspect/modify the request
            modifications = None
            if body:
                try:
                    modifications = self.on_swml_request(body)
                    if modifications:
                        req_log.debug("request_modifications_applied")
                except Exception as e:
                    req_log.error("error_in_request_modifier", error=str(e), traceback=traceback.format_exc())
            
            # Render SWML
            swml = self._render_swml(call_id, modifications)
            req_log.debug("swml_rendered", swml_size=len(swml))
            
            # Return as JSON
            req_log.info("request_successful")
            return Response(
                content=swml,
                media_type="application/json"
            )
        except Exception as e:
            req_log.error("request_failed", error=str(e), traceback=traceback.format_exc())
            return Response(
                content=json.dumps({"error": str(e), "traceback": traceback.format_exc()}),
                status_code=500,
                media_type="application/json"
            )
    
    async def _handle_debug_request(self, request: Request):
        """Handle GET/POST requests to the debug endpoint"""
        req_log = self.log.bind(
            endpoint="debug",
            method=request.method,
            path=request.url.path
        )
        
        req_log.debug("endpoint_called")
        
        try:
            # Check auth
            if not self._check_basic_auth(request):
                req_log.warning("unauthorized_access_attempt")
                return Response(
                    content=json.dumps({"error": "Unauthorized"}),
                    status_code=401,
                    headers={"WWW-Authenticate": "Basic"},
                    media_type="application/json"
                )
            
            # Get call_id from either query params (GET) or body (POST)
            call_id = None
            body = {}
            
            if request.method == "POST":
                try:
                    body = await request.json()
                    req_log.debug("request_body_received", body_size=len(str(body)))
                    if body:
                        req_log.debug("request_body", body=json.dumps(body, indent=2))
                    call_id = body.get("call_id")
                except Exception as e:
                    req_log.warning("error_parsing_request_body", error=str(e), traceback=traceback.format_exc())
                    try:
                        body_text = await request.body()
                        req_log.debug("raw_request_body", body=body_text.decode('utf-8', errors='replace'))
                    except:
                        pass
            else:
                call_id = request.query_params.get("call_id")
            
            # Add call_id to logger if any
            if call_id:
                req_log = req_log.bind(call_id=call_id)
                req_log.debug("call_id_identified")
                
            # Allow subclasses to inspect/modify the request
            modifications = None
            if body:
                modifications = self.on_swml_request(body)
                if modifications:
                    req_log.debug("request_modifications_applied")
                
            # Render SWML
            swml = self._render_swml(call_id, modifications)
            req_log.debug("swml_rendered", swml_size=len(swml))
            
            # Return as JSON
            req_log.info("request_successful")
            return Response(
                content=swml,
                media_type="application/json",
                headers={"X-Debug": "true"}
            )
        except Exception as e:
            req_log.error("request_failed", error=str(e), traceback=traceback.format_exc())
            return Response(
                content=json.dumps({"error": str(e), "traceback": traceback.format_exc()}),
                status_code=500,
                media_type="application/json"
            )
    
    async def _handle_swaig_request(self, request: Request):
        """Handle GET/POST requests to the SWAIG endpoint"""
        req_log = self.log.bind(
            endpoint="swaig",
            method=request.method,
            path=request.url.path
        )
        
        req_log.debug("endpoint_called")
        
        try:
            # Check auth
            if not self._check_basic_auth(request):
                req_log.warning("unauthorized_access_attempt")
                return Response(
                    content=json.dumps({"error": "Unauthorized"}),
                    status_code=401,
                    headers={"WWW-Authenticate": "Basic"},
                    media_type="application/json"
                )
            
            # Handle differently based on method
            if request.method == "GET":
                # For GET requests, return the SWML document (same as root endpoint)
                call_id = request.query_params.get("call_id")
                swml = self._render_swml(call_id)
                req_log.debug("swml_rendered", swml_size=len(swml))
                return Response(
                    content=swml,
                    media_type="application/json"
                )
            
            # For POST requests, process SWAIG function calls
            try:
                body = await request.json()
                req_log.debug("request_body_received", body_size=len(str(body)))
                if body:
                    req_log.debug("request_body", body=json.dumps(body, indent=2))
            except Exception as e:
                req_log.error("error_parsing_request_body", error=str(e), traceback=traceback.format_exc())
                body = {}
            
            # Extract function name
            function_name = body.get("function")
            if not function_name:
                req_log.warning("missing_function_name")
                return Response(
                    content=json.dumps({"error": "Missing function name"}),
                    status_code=400,
                    media_type="application/json"
                )
            
            # Add function info to logger
            req_log = req_log.bind(function=function_name)
            req_log.debug("function_call_received")
            
            # Extract arguments
            args = {}
            if "argument" in body and isinstance(body["argument"], dict):
                if "parsed" in body["argument"] and isinstance(body["argument"]["parsed"], list) and body["argument"]["parsed"]:
                    args = body["argument"]["parsed"][0]
                    req_log.debug("parsed_arguments", args=json.dumps(args, indent=2))
                elif "raw" in body["argument"]:
                    try:
                        args = json.loads(body["argument"]["raw"])
                        req_log.debug("raw_arguments_parsed", args=json.dumps(args, indent=2))
                    except Exception as e:
                        req_log.error("error_parsing_raw_arguments", error=str(e), raw=body["argument"]["raw"])
            
            # Get call_id from body
            call_id = body.get("call_id")
            if call_id:
                req_log = req_log.bind(call_id=call_id)
                req_log.debug("call_id_identified")
            
            # Call the function
            try:
                result = self.on_function_call(function_name, args, body)
                
                # Convert result to dict if needed
                if isinstance(result, SwaigFunctionResult):
                    result_dict = result.to_dict()
                elif isinstance(result, dict):
                    result_dict = result
                else:
                    result_dict = {"response": str(result)}
                
                req_log.info("function_executed_successfully")
                req_log.debug("function_result", result=json.dumps(result_dict, indent=2))
                return result_dict
            except Exception as e:
                req_log.error("function_execution_error", error=str(e), traceback=traceback.format_exc())
                return {"error": str(e), "function": function_name}
                
        except Exception as e:
            req_log.error("request_failed", error=str(e), traceback=traceback.format_exc())
            return Response(
                content=json.dumps({"error": str(e)}),
                status_code=500,
                media_type="application/json"
            )
            
    async def _handle_post_prompt_request(self, request: Request):
        """Handle GET/POST requests to the post_prompt endpoint"""
        req_log = self.log.bind(
            endpoint="post_prompt",
            method=request.method,
            path=request.url.path
        )
        
        # Only log if not suppressed
        if not self._suppress_logs:
            req_log.debug("endpoint_called")
        
        try:
            # Check auth
            if not self._check_basic_auth(request):
                req_log.warning("unauthorized_access_attempt")
                return Response(
                    content=json.dumps({"error": "Unauthorized"}),
                    status_code=401,
                    headers={"WWW-Authenticate": "Basic"},
                    media_type="application/json"
                )
            
            # For GET requests, return the SWML document (same as root endpoint)
            if request.method == "GET":
                call_id = request.query_params.get("call_id")
                swml = self._render_swml(call_id)
                req_log.debug("swml_rendered", swml_size=len(swml))
                return Response(
                    content=swml,
                    media_type="application/json"
                )
            
            # For POST requests, process the post-prompt data
            try:
                body = await request.json()
                
                # Only log if not suppressed
                if not self._suppress_logs:
                    req_log.debug("request_body_received", body_size=len(str(body)))
                    # Log the raw body as properly formatted JSON (not Python dict representation)
                    print("POST_PROMPT_BODY: " + json.dumps(body))
            except Exception as e:
                req_log.error("error_parsing_request_body", error=str(e), traceback=traceback.format_exc())
                body = {}
                
            # Extract summary from the correct location in the request
            summary = self._find_summary_in_post_data(body, req_log)
            
            # Save state if call_id is provided
            call_id = body.get("call_id")
            if call_id and summary:
                req_log = req_log.bind(call_id=call_id)
                
                # Check if state manager has the right methods
                try:
                    if hasattr(self._state_manager, 'get_state'):
                        state = self._state_manager.get_state(call_id) or {}
                        state["summary"] = summary
                        if hasattr(self._state_manager, 'update_state'):
                            self._state_manager.update_state(call_id, state)
                            req_log.debug("state_updated_with_summary")
                except Exception as e:
                    req_log.warning("state_update_failed", error=str(e))
            
            # Call the summary handler with the summary and the full body
            try:
                if summary:
                    self.on_summary(summary, body)
                    req_log.debug("summary_handler_called_successfully")
                else:
                    # If no summary found but still want to process the data
                    self.on_summary(None, body)
                    req_log.debug("summary_handler_called_with_null_summary")
            except Exception as e:
                req_log.error("error_in_summary_handler", error=str(e), traceback=traceback.format_exc())
            
            # Return success
            req_log.info("request_successful")
            return {"success": True}
        except Exception as e:
            req_log.error("request_failed", error=str(e), traceback=traceback.format_exc())
            return Response(
                content=json.dumps({"error": str(e)}),
                status_code=500,
                media_type="application/json"
            )

    def _find_summary_in_post_data(self, body, logger):
        """
        Extensive search for the summary in the post data
        
        Args:
            body: The POST request body
            logger: The logger instance to use
            
        Returns:
            The summary if found, None otherwise
        """
        summary = None
        
        # Check all the locations where the summary might be found
        
        # 1. First check post_prompt_data.parsed array (new standard location)
        post_prompt_data = body.get("post_prompt_data", {})
        if post_prompt_data:
            if not self._suppress_logs:
                logger.debug("checking_post_prompt_data", data_type=type(post_prompt_data).__name__)
            
            # Check for parsed array first (this is the most common location)
            if isinstance(post_prompt_data, dict) and "parsed" in post_prompt_data:
                parsed = post_prompt_data.get("parsed")
                if isinstance(parsed, list) and len(parsed) > 0:
                    # The summary is the first item in the parsed array
                    summary = parsed[0]
                    print("SUMMARY_FOUND: " + json.dumps(summary))
                    return summary
            
            # Check raw field - it might contain a JSON string
            if isinstance(post_prompt_data, dict) and "raw" in post_prompt_data:
                raw = post_prompt_data.get("raw")
                if isinstance(raw, str):
                    try:
                        # Try to parse the raw field as JSON
                        parsed_raw = json.loads(raw)
                        if not self._suppress_logs:
                            print("SUMMARY_FOUND_RAW: " + json.dumps(parsed_raw))
                        return parsed_raw
                    except:
                        pass
            
            # Direct access to substituted field
            if isinstance(post_prompt_data, dict) and "substituted" in post_prompt_data:
                summary = post_prompt_data.get("substituted")
                if not self._suppress_logs:
                    print("SUMMARY_FOUND_SUBSTITUTED: " + json.dumps(summary) if isinstance(summary, (dict, list)) else f"SUMMARY_FOUND_SUBSTITUTED: {summary}")
                return summary
            
            # Check for nested data structure
            if isinstance(post_prompt_data, dict) and "data" in post_prompt_data:
                data = post_prompt_data.get("data")
                if isinstance(data, dict):
                    if "substituted" in data:
                        summary = data.get("substituted")
                        if not self._suppress_logs:
                            print("SUMMARY_FOUND_DATA_SUBSTITUTED: " + json.dumps(summary) if isinstance(summary, (dict, list)) else f"SUMMARY_FOUND_DATA_SUBSTITUTED: {summary}")
                        return summary
                    
                    # Try text field
                    if "text" in data:
                        summary = data.get("text")
                        if not self._suppress_logs:
                            print("SUMMARY_FOUND_DATA_TEXT: " + json.dumps(summary) if isinstance(summary, (dict, list)) else f"SUMMARY_FOUND_DATA_TEXT: {summary}")
                        return summary
        
        # 2. Check ai_response (legacy location)
        ai_response = body.get("ai_response", {})
        if ai_response and isinstance(ai_response, dict):
            if "summary" in ai_response:
                summary = ai_response.get("summary")
                if not self._suppress_logs:
                    print("SUMMARY_FOUND_AI_RESPONSE: " + json.dumps(summary) if isinstance(summary, (dict, list)) else f"SUMMARY_FOUND_AI_RESPONSE: {summary}")
                return summary
        
        # 3. Look for direct fields at the top level
        for field in ["substituted", "summary", "content", "text", "result", "output"]:
            if field in body:
                summary = body.get(field)
                if not self._suppress_logs:
                    print(f"SUMMARY_FOUND_TOP_LEVEL_{field}: " + json.dumps(summary) if isinstance(summary, (dict, list)) else f"SUMMARY_FOUND_TOP_LEVEL_{field}: {summary}")
                return summary
        
        # 4. Recursively search for summary-like fields up to 3 levels deep
        def recursive_search(data, path="", depth=0):
            if depth > 3 or not isinstance(data, dict):  # Limit recursion depth
                return None
            
            # Check if any key looks like it might contain a summary
            for key in data.keys():
                if key.lower() in ["summary", "substituted", "output", "result", "content", "text"]:
                    value = data.get(key)
                    curr_path = f"{path}.{key}" if path else key
                    if not self._suppress_logs:
                        logger.info(f"potential_summary_found_at_{curr_path}", 
                                  value_type=type(value).__name__)
                    if isinstance(value, (str, dict, list)):
                        return value
                    
            # Recursively check nested dictionaries
            for key, value in data.items():
                if isinstance(value, dict):
                    curr_path = f"{path}.{key}" if path else key
                    result = recursive_search(value, curr_path, depth + 1)
                    if result:
                        return result
                    
            return None
        
        # Perform recursive search
        recursive_result = recursive_search(body)
        if recursive_result:
            summary = recursive_result
            if not self._suppress_logs:
                print("SUMMARY_FOUND_RECURSIVE: " + json.dumps(summary) if isinstance(summary, (dict, list)) else f"SUMMARY_FOUND_RECURSIVE: {summary}")
            return summary
        
        # No summary found
        if not self._suppress_logs:
            print("NO_SUMMARY_FOUND")
        return None

    def _register_routes(self, app):
        """Register all routes for the agent, with both slash variants and both HTTP methods"""
        
        self.log.info("registering_routes", path=self.route)
        
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
        @app.post(f"{self.route}/debug")
        async def handle_debug_no_slash(request: Request):
            return await self._handle_debug_request(request)
            
        # Debug endpoint - with trailing slash
        @app.get(f"{self.route}/debug/")
        @app.post(f"{self.route}/debug/")
        async def handle_debug_with_slash(request: Request):
            return await self._handle_debug_request(request)
            
        # SWAIG endpoint - without trailing slash
        @app.get(f"{self.route}/swaig")
        @app.post(f"{self.route}/swaig")
        async def handle_swaig_no_slash(request: Request):
            return await self._handle_swaig_request(request)
            
        # SWAIG endpoint - with trailing slash
        @app.get(f"{self.route}/swaig/")
        @app.post(f"{self.route}/swaig/")
        async def handle_swaig_with_slash(request: Request):
            return await self._handle_swaig_request(request)
        
        # Post-prompt endpoint - without trailing slash
        @app.get(f"{self.route}/post_prompt")
        @app.post(f"{self.route}/post_prompt")
        async def handle_post_prompt_no_slash(request: Request):
            return await self._handle_post_prompt_request(request)
            
        # Post-prompt endpoint - with trailing slash
        @app.get(f"{self.route}/post_prompt/")
        @app.post(f"{self.route}/post_prompt/")
        async def handle_post_prompt_with_slash(request: Request):
            return await self._handle_post_prompt_request(request)
        
        # Check if SIP routing is enabled for this agent
        # (The agent will have _sip_usernames if enable_sip_routing was called)
        if hasattr(self, '_sip_usernames') and self._sip_usernames:
            self.log.info("registering_sip_endpoint", usernames=list(self._sip_usernames))
            
            # SIP endpoint - without trailing slash
            @app.get("/sip")
            @app.post("/sip")
            async def handle_sip_no_slash(request: Request):
                return await self._handle_root_request(request)
                
            # SIP endpoint - with trailing slash
            @app.get("/sip/")
            @app.post("/sip/")
            async def handle_sip_with_slash(request: Request):
                return await self._handle_root_request(request)
                
            # Log that SIP endpoint was added
            self.log.info("sip_endpoint_registered", path="/sip")
            
            # Add SIP routes to the printed information
            print(f"SIP endpoint available at: http://{self.host}:{self.port}/sip")
        
        # Log all registered routes
        routes = [f"{route.methods} {route.path}" for route in app.routes]
        self.log.debug("routes_registered", routes=routes)

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

    # State Management Methods
    def get_state(self, call_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the state for a call
        
        Args:
            call_id: Call ID to get state for
            
        Returns:
            Call state or None if not found
        """
        try:
            if hasattr(self._state_manager, 'get_state'):
                return self._state_manager.get_state(call_id)
            return None
        except Exception as e:
            logger.warning("get_state_failed", error=str(e))
            return None
        
    def set_state(self, call_id: str, data: Dict[str, Any]) -> bool:
        """
        Set the state for a call
        
        Args:
            call_id: Call ID to set state for
            data: State data to set
            
        Returns:
            True if state was set, False otherwise
        """
        try:
            if hasattr(self._state_manager, 'set_state'):
                return self._state_manager.set_state(call_id, data)
            return False
        except Exception as e:
            logger.warning("set_state_failed", error=str(e))
            return False
        
    def update_state(self, call_id: str, data: Dict[str, Any]) -> bool:
        """
        Update the state for a call
        
        Args:
            call_id: Call ID to update state for
            data: State data to update
            
        Returns:
            True if state was updated, False otherwise
        """
        try:
            if hasattr(self._state_manager, 'update_state'):
                return self._state_manager.update_state(call_id, data)
            return self.set_state(call_id, data)
        except Exception as e:
            logger.warning("update_state_failed", error=str(e))
            return False
        
    def clear_state(self, call_id: str) -> bool:
        """
        Clear the state for a call
        
        Args:
            call_id: Call ID to clear state for
            
        Returns:
            True if state was cleared, False otherwise
        """
        try:
            if hasattr(self._state_manager, 'clear_state'):
                return self._state_manager.clear_state(call_id)
            return False
        except Exception as e:
            logger.warning("clear_state_failed", error=str(e))
            return False
        
    def cleanup_expired_state(self) -> int:
        """
        Clean up expired state
        
        Returns:
            Number of expired state entries removed
        """
        try:
            if hasattr(self._state_manager, 'cleanup_expired'):
                return self._state_manager.cleanup_expired()
            return 0
        except Exception as e:
            logger.warning("cleanup_expired_state_failed", error=str(e))
            return 0

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
        
    def add_native_function(self, function_name: str) -> 'AgentBase':
        """
        Add a native function to the list of enabled native functions
        
        Args:
            function_name: Name of native function to enable
            
        Returns:
            Self for method chaining
        """
        if function_name and isinstance(function_name, str):
            if not self.native_functions:
                self.native_functions = []
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

    def serve(self, host: Optional[str] = None, port: Optional[int] = None) -> None:
        """
        Start a web server for this agent
        
        Args:
            host: Optional host to override the default
            port: Optional port to override the default
        """
        import uvicorn
        
        # Create a FastAPI app with no automatic redirects
        app = FastAPI(redirect_slashes=False)
        
        # Register all routes
        self._register_routes(app)
        
        host = host or self.host
        port = port or self.port
        
        # Print the auth credentials with source
        username, password, source = self.get_basic_auth_credentials(include_source=True)
        self.log.info("starting_server", 
                     url=f"http://{host}:{port}{self.route}",
                     username=username,
                     password="*" * len(password),
                     auth_source=source)
        
        print(f"Agent '{self.name}' is available at:")
        print(f"URL: http://{host}:{port}{self.route}")
        print(f"Basic Auth: {username}:{password} (source: {source})")
        
        # Check if SIP routing is enabled and print additional info
        if hasattr(self, '_sip_usernames') and self._sip_usernames:
            print(f"SIP endpoint: http://{host}:{port}/sip")
            print(f"SIP usernames: {', '.join(self._sip_usernames)}")
        
        # Configure Uvicorn for production
        uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
        uvicorn_log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        uvicorn_log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        try:
            # Run the server
            uvicorn.run(
                app, 
                host=host, 
                port=port,
                log_config=uvicorn_log_config
            )
        except KeyboardInterrupt:
            self.log.info("server_shutdown")
            print("\nStopping the agent.")

    # ----------------------------------------------------------------------
    # AI Verb Configuration Methods
    # ----------------------------------------------------------------------

    def add_hint(self, hint: str) -> 'AgentBase':
        """
        Add a simple string hint to help the AI agent understand certain words better
        
        Args:
            hint: The hint string to add
            
        Returns:
            Self for method chaining
        """
        if isinstance(hint, str) and hint:
            self._hints.append(hint)
        return self

    def add_hints(self, hints: List[str]) -> 'AgentBase':
        """
        Add multiple string hints
        
        Args:
            hints: List of hint strings
            
        Returns:
            Self for method chaining
        """
        if hints and isinstance(hints, list):
            for hint in hints:
                if isinstance(hint, str) and hint:
                    self._hints.append(hint)
        return self

    def add_pattern_hint(self, 
                         hint: str, 
                         pattern: str, 
                         replace: str, 
                         ignore_case: bool = False) -> 'AgentBase':
        """
        Add a complex hint with pattern matching
        
        Args:
            hint: The hint to match
            pattern: Regular expression pattern
            replace: Text to replace the hint with
            ignore_case: Whether to ignore case when matching
            
        Returns:
            Self for method chaining
        """
        if hint and pattern and replace:
            self._hints.append({
                "hint": hint,
                "pattern": pattern,
                "replace": replace,
                "ignore_case": ignore_case
            })
        return self

    def add_language(self, 
                     name: str, 
                     code: str, 
                     voice: str,
                     speech_fillers: Optional[List[str]] = None,
                     function_fillers: Optional[List[str]] = None,
                     engine: Optional[str] = None,
                     model: Optional[str] = None) -> 'AgentBase':
        """
        Add a language configuration to support multilingual conversations
        
        Args:
            name: Name of the language (e.g., "English", "French")
            code: Language code (e.g., "en-US", "fr-FR")
            voice: TTS voice to use. Can be a simple name (e.g., "en-US-Neural2-F") 
                  or a combined format "engine.voice:model" (e.g., "elevenlabs.josh:eleven_turbo_v2_5")
            speech_fillers: Optional list of filler phrases for natural speech
            function_fillers: Optional list of filler phrases during function calls
            engine: Optional explicit engine name (e.g., "elevenlabs", "rime")
            model: Optional explicit model name (e.g., "eleven_turbo_v2_5", "arcana")
            
        Returns:
            Self for method chaining
            
        Examples:
            # Simple voice name
            agent.add_language("English", "en-US", "en-US-Neural2-F")
            
            # Explicit parameters
            agent.add_language("English", "en-US", "josh", engine="elevenlabs", model="eleven_turbo_v2_5")
            
            # Combined format
            agent.add_language("English", "en-US", "elevenlabs.josh:eleven_turbo_v2_5")
        """
        language = {
            "name": name,
            "code": code
        }
        
        # Handle voice formatting (either explicit params or combined string)
        if engine or model:
            # Use explicit parameters if provided
            language["voice"] = voice
            if engine:
                language["engine"] = engine
            if model:
                language["model"] = model
        elif "." in voice and ":" in voice:
            # Parse combined string format: "engine.voice:model"
            try:
                engine_voice, model_part = voice.split(":", 1)
                engine_part, voice_part = engine_voice.split(".", 1)
                
                language["voice"] = voice_part
                language["engine"] = engine_part
                language["model"] = model_part
            except ValueError:
                # If parsing fails, use the voice string as-is
                language["voice"] = voice
        else:
            # Simple voice string
            language["voice"] = voice
        
        # Add fillers if provided
        if speech_fillers and function_fillers:
            language["speech_fillers"] = speech_fillers
            language["function_fillers"] = function_fillers
        elif speech_fillers or function_fillers:
            # If only one type of fillers is provided, use the deprecated "fillers" field
            fillers = speech_fillers or function_fillers
            language["fillers"] = fillers
        
        self._languages.append(language)
        return self

    def set_languages(self, languages: List[Dict[str, Any]]) -> 'AgentBase':
        """
        Set all language configurations at once
        
        Args:
            languages: List of language configuration dictionaries
            
        Returns:
            Self for method chaining
        """
        if languages and isinstance(languages, list):
            self._languages = languages
        return self

    def add_pronunciation(self, 
                         replace: str, 
                         with_text: str, 
                         ignore_case: bool = False) -> 'AgentBase':
        """
        Add a pronunciation rule to help the AI speak certain words correctly
        
        Args:
            replace: The expression to replace
            with_text: The phonetic spelling to use instead
            ignore_case: Whether to ignore case when matching
            
        Returns:
            Self for method chaining
        """
        if replace and with_text:
            rule = {
                "replace": replace,
                "with": with_text
            }
            if ignore_case:
                rule["ignore_case"] = True
            
            self._pronounce.append(rule)
        return self

    def set_pronunciations(self, pronunciations: List[Dict[str, Any]]) -> 'AgentBase':
        """
        Set all pronunciation rules at once
        
        Args:
            pronunciations: List of pronunciation rule dictionaries
            
        Returns:
            Self for method chaining
        """
        if pronunciations and isinstance(pronunciations, list):
            self._pronounce = pronunciations
        return self

    def set_param(self, key: str, value: Any) -> 'AgentBase':
        """
        Set a single AI parameter
        
        Args:
            key: Parameter name
            value: Parameter value
            
        Returns:
            Self for method chaining
        """
        if key:
            self._params[key] = value
        return self

    def set_params(self, params: Dict[str, Any]) -> 'AgentBase':
        """
        Set multiple AI parameters at once
        
        Args:
            params: Dictionary of parameter name/value pairs
            
        Returns:
            Self for method chaining
        """
        if params and isinstance(params, dict):
            self._params.update(params)
        return self

    def set_global_data(self, data: Dict[str, Any]) -> 'AgentBase':
        """
        Set the global data available to the AI throughout the conversation
        
        Args:
            data: Dictionary of global data
            
        Returns:
            Self for method chaining
        """
        if data and isinstance(data, dict):
            self._global_data = data
        return self

    def update_global_data(self, data: Dict[str, Any]) -> 'AgentBase':
        """
        Update the global data with new values
        
        Args:
            data: Dictionary of global data to update
            
        Returns:
            Self for method chaining
        """
        if data and isinstance(data, dict):
            self._global_data.update(data)
        return self

    def set_native_functions(self, function_names: List[str]) -> 'AgentBase':
        """
        Set the list of native functions to enable
        
        Args:
            function_names: List of native function names
            
        Returns:
            Self for method chaining
        """
        if function_names and isinstance(function_names, list):
            self.native_functions = [name for name in function_names if isinstance(name, str)]
        return self

    def add_function_include(self, url: str, functions: List[str], meta_data: Optional[Dict[str, Any]] = None) -> 'AgentBase':
        """
        Add a remote function include to the SWAIG configuration
        
        Args:
            url: URL to fetch remote functions from
            functions: List of function names to include
            meta_data: Optional metadata to include with the function include
            
        Returns:
            Self for method chaining
        """
        if url and functions and isinstance(functions, list):
            include = {
                "url": url,
                "functions": functions
            }
            if meta_data and isinstance(meta_data, dict):
                include["meta_data"] = meta_data
            
            self._function_includes.append(include)
        return self

    def set_function_includes(self, includes: List[Dict[str, Any]]) -> 'AgentBase':
        """
        Set the complete list of function includes
        
        Args:
            includes: List of include objects, each with url and functions properties
            
        Returns:
            Self for method chaining
        """
        if includes and isinstance(includes, list):
            # Validate each include has required properties
            valid_includes = []
            for include in includes:
                if isinstance(include, dict) and "url" in include and "functions" in include:
                    if isinstance(include["functions"], list):
                        valid_includes.append(include)
            
            self._function_includes = valid_includes
        return self

    def enable_sip_routing(self, auto_map: bool = True) -> 'AgentBase':
        """
        Enable SIP-based routing for this agent
        
        This allows the agent to automatically route SIP requests based on SIP usernames.
        When enabled, a global `/sip` endpoint is automatically created that will handle
        SIP requests and deliver them to this agent.
        
        Args:
            auto_map: Whether to automatically map common SIP usernames to this agent
                     (based on the agent name and route path)
            
        Returns:
            Self for method chaining
        """
        # Create a routing callback that handles SIP usernames
        def sip_routing_callback(request: Request, body: Dict[str, Any]) -> Optional[str]:
            # Extract SIP username from the request body
            sip_username = self.extract_sip_username(body)
            
            if sip_username:
                self.log.info("sip_username_extracted", username=sip_username)
                
                # This route is already being handled by the agent, no need to redirect
                return None
                
        # Register the callback with the SWMLService
        self.register_routing_callback(sip_routing_callback)
        
        # Auto-map common usernames if requested
        if auto_map:
            self.auto_map_sip_usernames()
            
        return self
        
    def register_sip_username(self, sip_username: str) -> 'AgentBase':
        """
        Register a SIP username that should be routed to this agent
        
        Args:
            sip_username: SIP username to register
            
        Returns:
            Self for method chaining
        """
        if not hasattr(self, '_sip_usernames'):
            self._sip_usernames = set()
            
        self._sip_usernames.add(sip_username.lower())
        self.log.info("sip_username_registered", username=sip_username)
        
        return self
        
    def auto_map_sip_usernames(self) -> 'AgentBase':
        """
        Automatically register common SIP usernames based on this agent's 
        name and route
        
        Returns:
            Self for method chaining
        """
        # Register username based on agent name
        clean_name = re.sub(r'[^a-z0-9_]', '', self.name.lower())
        if clean_name:
            self.register_sip_username(clean_name)
            
        # Register username based on route (without slashes)
        clean_route = re.sub(r'[^a-z0-9_]', '', self.route.lower())
        if clean_route and clean_route != clean_name:
            self.register_sip_username(clean_route)
            
        # Register common variations if they make sense
        if len(clean_name) > 3:
            # Register without vowels
            no_vowels = re.sub(r'[aeiou]', '', clean_name)
            if no_vowels != clean_name and len(no_vowels) > 2:
                self.register_sip_username(no_vowels)
                
        return self
