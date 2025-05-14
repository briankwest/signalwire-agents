"""
SWMLService - Base class for SWML document creation and serving

This class provides the foundation for creating and serving SWML documents.
It handles schema validation, document creation, and web service functionality.
"""

import os
import inspect
import json
import secrets
import base64
import logging
import sys
import types
from typing import Dict, List, Any, Optional, Union, Callable, Tuple, Type
from urllib.parse import urlparse

# Import and configure structlog
try:
    import structlog
    
    # Only configure if not already configured
    if not hasattr(structlog, "_configured") or not structlog._configured:
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
        
        # Set up root logger with structlog
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=logging.INFO,
        )
        
        # Mark as configured to avoid duplicate configuration
        structlog._configured = True
    
    # Create the module logger
    logger = structlog.get_logger("swml_service")
    
except ImportError:
    # Fallback to standard logging if structlog is not available
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )
    logger = logging.getLogger("swml_service")

try:
    import fastapi
    from fastapi import FastAPI, APIRouter, Depends, HTTPException, Query, Body, Request, Response
    from fastapi.security import HTTPBasic, HTTPBasicCredentials
    from pydantic import BaseModel
except ImportError:
    raise ImportError(
        "fastapi is required. Install it with: pip install fastapi"
    )

from signalwire_agents.utils.schema_utils import SchemaUtils
from signalwire_agents.core.swml_handler import VerbHandlerRegistry, SWMLVerbHandler


class SWMLService:
    """
    Base class for creating and serving SWML documents.
    
    This class provides core functionality for:
    - Loading and validating SWML schema
    - Creating SWML documents
    - Setting up web endpoints for serving SWML
    - Managing authentication
    - Registering SWML functions
    
    It serves as the foundation for more specialized services like AgentBase.
    """
    
    def __init__(
        self,
        name: str,
        route: str = "/",
        host: str = "0.0.0.0",
        port: int = 3000,
        basic_auth: Optional[Tuple[str, str]] = None,
        schema_path: Optional[str] = None
    ):
        """
        Initialize a new SWML service
        
        Args:
            name: Service name/identifier
            route: HTTP route path for this service
            host: Host to bind the web server to
            port: Port to bind the web server to
            basic_auth: Optional (username, password) tuple for basic auth
            schema_path: Optional path to the schema file
        """
        self.name = name
        self.route = route.rstrip("/")  # Ensure no trailing slash
        self.host = host
        self.port = port
        self.ssl_enabled = False
        self.domain = None
        
        # Initialize logger for this instance
        self.log = logger.bind(service=name)
        self.log.info("service_initializing", route=self.route, host=host, port=port)
        
        # Set basic auth credentials
        if basic_auth is not None:
            # Use provided credentials
            self._basic_auth = basic_auth
        else:
            # Check environment variables first
            env_user = os.environ.get('SWML_BASIC_AUTH_USER')
            env_pass = os.environ.get('SWML_BASIC_AUTH_PASSWORD')
            
            if env_user and env_pass:
                # Use environment variables
                self._basic_auth = (env_user, env_pass)
            else:
                # Generate random credentials as fallback
                username = f"user_{secrets.token_hex(4)}"
                password = secrets.token_urlsafe(16)
                self._basic_auth = (username, password)
        
        # Find the schema file if not provided
        if schema_path is None:
            schema_path = self._find_schema_path()
            if schema_path:
                self.log.debug("schema_found", path=schema_path)
            else:
                self.log.warning("schema_not_found")
        
        # Initialize schema utils
        self.schema_utils = SchemaUtils(schema_path)
        
        # Initialize verb handler registry
        self.verb_registry = VerbHandlerRegistry()
        
        # Server state
        self._app = None
        self._router = None
        self._running = False
        
        # Initialize SWML document state
        self._current_document = self._create_empty_document()
        
        # Dictionary to cache dynamically created methods (instance level cache)
        self._verb_methods_cache = {}
        
        # Create auto-vivified methods for all verbs
        self._create_verb_methods()
        
        # Initialize routing callback
        self._routing_callback = None
    
    def _create_verb_methods(self) -> None:
        """
        Create auto-vivified methods for all verbs at initialization time
        """
        print("Creating auto-vivified methods for all verbs")
        
        # Get all verb names from the schema
        verb_names = self.schema_utils.get_all_verb_names()
        print(f"Found {len(verb_names)} verbs in schema")
        
        # Create a method for each verb
        for verb_name in verb_names:
            # Skip verbs that already have specific methods
            if hasattr(self, verb_name):
                print(f"Skipping {verb_name} - already has a method")
                continue
            
            # Handle sleep verb specially since it takes an integer directly
            if verb_name == "sleep":
                def sleep_method(self_instance, duration=None, **kwargs):
                    """
                    Add the sleep verb to the document.
                    
                    Args:
                        duration: The amount of time to sleep in milliseconds
                    """
                    print(f"Executing auto-vivified method for 'sleep'")
                    # Sleep verb takes a direct integer parameter in SWML
                    if duration is not None:
                        return self_instance.add_verb("sleep", duration)
                    elif kwargs:
                        # Try to get the value from kwargs
                        return self_instance.add_verb("sleep", next(iter(kwargs.values())))
                    else:
                        raise TypeError("sleep() missing required argument: 'duration'")
                
                # Set it as an attribute of self
                setattr(self, verb_name, types.MethodType(sleep_method, self))
                
                # Also cache it for later
                self._verb_methods_cache[verb_name] = sleep_method
                
                print(f"Created special method for {verb_name}")
                continue
                
            # Generate the method implementation for normal verbs
            def make_verb_method(name):
                def verb_method(self_instance, **kwargs):
                    """
                    Dynamically generated method for SWML verb
                    """
                    print(f"Executing auto-vivified method for '{name}'")
                    config = {}
                    for key, value in kwargs.items():
                        if value is not None:
                            config[key] = value
                    return self_instance.add_verb(name, config)
                
                # Add docstring to the method
                verb_properties = self.schema_utils.get_verb_properties(name)
                if "description" in verb_properties:
                    verb_method.__doc__ = f"Add the {name} verb to the document.\n\n{verb_properties['description']}"
                else:
                    verb_method.__doc__ = f"Add the {name} verb to the document."
                
                return verb_method
            
            # Create the method with closure over the verb name
            method = make_verb_method(verb_name)
            
            # Set it as an attribute of self
            setattr(self, verb_name, types.MethodType(method, self))
            
            # Also cache it for later
            self._verb_methods_cache[verb_name] = method
            
            print(f"Created method for {verb_name}")
    
    def __getattr__(self, name: str) -> Any:
        """
        Dynamically generate and return SWML verb methods when accessed
        
        This method is called when an attribute lookup fails through the normal
        mechanisms. It checks if the attribute name corresponds to a SWML verb
        defined in the schema, and if so, dynamically creates a method for that verb.
        
        Args:
            name: The name of the attribute being accessed
            
        Returns:
            The dynamically created verb method if name is a valid SWML verb,
            otherwise raises AttributeError
            
        Raises:
            AttributeError: If name is not a valid SWML verb
        """
        print(f"DEBUG: __getattr__ called for '{name}'")
        
        # Simple version to match our test script
        # First check if this is a valid SWML verb
        verb_names = self.schema_utils.get_all_verb_names()
        
        if name in verb_names:
            print(f"DEBUG: '{name}' is a valid verb")
            
            # Check if we already have this method in the cache
            if not hasattr(self, '_verb_methods_cache'):
                self._verb_methods_cache = {}
                
            if name in self._verb_methods_cache:
                print(f"DEBUG: Using cached method for '{name}'")
                return types.MethodType(self._verb_methods_cache[name], self)
            
            # Handle sleep verb specially since it takes an integer directly
            if name == "sleep":
                def sleep_method(self_instance, duration=None, **kwargs):
                    """
                    Add the sleep verb to the document.
                    
                    Args:
                        duration: The amount of time to sleep in milliseconds
                    """
                    print(f"DEBUG: Executing auto-vivified method for 'sleep'")
                    # Sleep verb takes a direct integer parameter in SWML
                    if duration is not None:
                        return self_instance.add_verb("sleep", duration)
                    elif kwargs:
                        # Try to get the value from kwargs
                        return self_instance.add_verb("sleep", next(iter(kwargs.values())))
                    else:
                        raise TypeError("sleep() missing required argument: 'duration'")
                
                # Cache the method for future use
                print(f"DEBUG: Caching special method for '{name}'")
                self._verb_methods_cache[name] = sleep_method
                
                # Return the bound method
                return types.MethodType(sleep_method, self)
            
            # Generate the method implementation for normal verbs
            def verb_method(self_instance, **kwargs):
                """
                Dynamically generated method for SWML verb
                """
                print(f"DEBUG: Executing auto-vivified method for '{name}'")
                config = {}
                for key, value in kwargs.items():
                    if value is not None:
                        config[key] = value
                return self_instance.add_verb(name, config)
            
            # Add docstring to the method
            verb_properties = self.schema_utils.get_verb_properties(name)
            if "description" in verb_properties:
                verb_method.__doc__ = f"Add the {name} verb to the document.\n\n{verb_properties['description']}"
            else:
                verb_method.__doc__ = f"Add the {name} verb to the document."
            
            # Cache the method for future use
            print(f"DEBUG: Caching method for '{name}'")
            self._verb_methods_cache[name] = verb_method
            
            # Return the bound method
            return types.MethodType(verb_method, self)
        
        # Not a valid verb
        msg = f"'{self.__class__.__name__}' object has no attribute '{name}'"
        print(f"DEBUG: {msg}")
        raise AttributeError(msg)
    
    def _find_schema_path(self) -> Optional[str]:
        """
        Find the schema.json file location
        
        Returns:
            Path to schema.json if found, None otherwise
        """
        # Try package resources first (most reliable after pip install)
        try:
            import importlib.resources
            try:
                # Python 3.9+
                with importlib.resources.files("signalwire_agents").joinpath("schema.json") as path:
                    return str(path)
            except AttributeError:
                # Python 3.7-3.8
                with importlib.resources.path("signalwire_agents", "schema.json") as path:
                    return str(path)
        except (ImportError, ModuleNotFoundError):
            pass
            
        # Fall back to pkg_resources for older Python or alternative lookup
        try:
            import pkg_resources
            return pkg_resources.resource_filename("signalwire_agents", "schema.json")
        except (ImportError, ModuleNotFoundError, pkg_resources.DistributionNotFound):
            pass

        # Fall back to manual search in various locations
        import sys
        
        # Get package directory
        package_dir = os.path.dirname(os.path.dirname(__file__))
        
        # Potential locations for schema.json
        potential_paths = [
            os.path.join(os.getcwd(), "schema.json"),  # Current working directory
            os.path.join(package_dir, "schema.json"),  # Package directory
            os.path.join(os.path.dirname(package_dir), "schema.json"),  # Parent of package directory
            os.path.join(sys.prefix, "schema.json"),  # Python installation directory
            os.path.join(package_dir, "data", "schema.json"),  # Data subdirectory
            os.path.join(os.path.dirname(package_dir), "data", "schema.json"),  # Parent's data subdirectory
        ]
        
        # Try to find the schema file
        for path in potential_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def _create_empty_document(self) -> Dict[str, Any]:
        """
        Create an empty SWML document
        
        Returns:
            Empty SWML document structure
        """
        return {
            "version": "1.0.0",
            "sections": {
                "main": []
            }
        }
    
    def reset_document(self) -> None:
        """
        Reset the current document to an empty state
        """
        self._current_document = self._create_empty_document()
    
    def add_verb(self, verb_name: str, config: Union[Dict[str, Any], int]) -> bool:
        """
        Add a verb to the main section of the current document
        
        Args:
            verb_name: The name of the verb to add
            config: Configuration for the verb or direct value for certain verbs (e.g., sleep)
            
        Returns:
            True if the verb was added successfully, False otherwise
        """
        # Special case for verbs that take direct values (like sleep)
        if verb_name == "sleep" and isinstance(config, int):
            # Sleep verb takes a direct integer value
            verb_obj = {verb_name: config}
            self._current_document["sections"]["main"].append(verb_obj)
            return True
            
        # Ensure config is a dictionary for other verbs
        if not isinstance(config, dict):
            self.log.warning(f"invalid_config_type", verb=verb_name, 
                            expected="dict", got=type(config).__name__)
            return False
        
        # Check if we have a specialized handler for this verb
        if self.verb_registry.has_handler(verb_name):
            handler = self.verb_registry.get_handler(verb_name)
            is_valid, errors = handler.validate_config(config)
        else:
            # Use schema-based validation for standard verbs
            is_valid, errors = self.schema_utils.validate_verb(verb_name, config)
        
        if not is_valid:
            # Log validation errors
            self.log.warning(f"verb_validation_error", verb=verb_name, errors=errors)
            return False
        
        # Add the verb to the main section
        verb_obj = {verb_name: config}
        self._current_document["sections"]["main"].append(verb_obj)
        return True
    
    def add_section(self, section_name: str) -> bool:
        """
        Add a new section to the document
        
        Args:
            section_name: Name of the section to add
            
        Returns:
            True if the section was added, False if it already exists
        """
        if section_name in self._current_document["sections"]:
            return False
        
        self._current_document["sections"][section_name] = []
        return True
    
    def add_verb_to_section(self, section_name: str, verb_name: str, config: Union[Dict[str, Any], int]) -> bool:
        """
        Add a verb to a specific section
        
        Args:
            section_name: Name of the section to add to
            verb_name: The name of the verb to add
            config: Configuration for the verb or direct value for certain verbs (e.g., sleep)
            
        Returns:
            True if the verb was added successfully, False otherwise
        """
        # Make sure the section exists
        if section_name not in self._current_document["sections"]:
            self.add_section(section_name)
        
        # Special case for verbs that take direct values (like sleep)
        if verb_name == "sleep" and isinstance(config, int):
            # Sleep verb takes a direct integer value
            verb_obj = {verb_name: config}
            self._current_document["sections"][section_name].append(verb_obj)
            return True
            
        # Ensure config is a dictionary for other verbs
        if not isinstance(config, dict):
            self.log.warning(f"invalid_config_type", verb=verb_name, section=section_name,
                            expected="dict", got=type(config).__name__)
            return False
        
        # Check if we have a specialized handler for this verb
        if self.verb_registry.has_handler(verb_name):
            handler = self.verb_registry.get_handler(verb_name)
            is_valid, errors = handler.validate_config(config)
        else:
            # Use schema-based validation for standard verbs
            is_valid, errors = self.schema_utils.validate_verb(verb_name, config)
        
        if not is_valid:
            # Log validation errors
            self.log.warning(f"verb_validation_error", verb=verb_name, section=section_name, errors=errors)
            return False
        
        # Add the verb to the section
        verb_obj = {verb_name: config}
        self._current_document["sections"][section_name].append(verb_obj)
        return True
    
    def get_document(self) -> Dict[str, Any]:
        """
        Get the current SWML document
        
        Returns:
            The current SWML document as a dictionary
        """
        return self._current_document
    
    def render_document(self) -> str:
        """
        Render the current SWML document as a JSON string
        
        Returns:
            The current SWML document as a JSON string
        """
        return json.dumps(self._current_document)
    
    def register_verb_handler(self, handler: SWMLVerbHandler) -> None:
        """
        Register a custom verb handler
        
        Args:
            handler: The verb handler to register
        """
        self.verb_registry.register_handler(handler)
    
    def as_router(self) -> APIRouter:
        """
        Get a FastAPI router for this service
        
        Returns:
            FastAPI router
        """
        router = APIRouter()
        
        # Root endpoint - without trailing slash
        @router.get("")
        @router.post("")
        async def handle_root_no_slash(request: Request, response: Response):
            """Handle GET/POST requests to the root endpoint"""
            return await self._handle_request(request, response)
            
        # Root endpoint - with trailing slash
        @router.get("/")
        @router.post("/")
        async def handle_root_with_slash(request: Request, response: Response):
            """Handle GET/POST requests to the root endpoint with trailing slash"""
            return await self._handle_request(request, response)
        
        # Add SIP endpoint if routing callback is configured
        if self._routing_callback is not None:
            # SIP endpoint - without trailing slash
            @router.get("/sip")
            @router.post("/sip")
            async def handle_sip_no_slash(request: Request, response: Response):
                """Handle GET/POST requests to the SIP endpoint"""
                return await self._handle_request(request, response)
                
            # SIP endpoint - with trailing slash
            @router.get("/sip/")
            @router.post("/sip/")
            async def handle_sip_with_slash(request: Request, response: Response):
                """Handle GET/POST requests to the SIP endpoint with trailing slash"""
                return await self._handle_request(request, response)
                
            self.log.info("sip_endpoint_registered", path="/sip")
        
        self._router = router
        return router
    
    def register_routing_callback(self, callback_fn: Callable[[Request, Dict[str, Any]], Optional[str]]) -> None:
        """
        Register a callback function that will be called to determine routing
        based on POST data.
        
        When a routing callback is registered, a global `/sip` endpoint is automatically
        created that will handle SIP requests. This endpoint will use the callback to
        determine if the request should be processed by this service or redirected.
        
        The callback should take a request object and request body dictionary and return:
        - A route string if it should be routed to a different endpoint
        - None if normal processing should continue
        
        Args:
            callback_fn: The callback function to register
        """
        self.log.info("registering_routing_callback")
        self._routing_callback = callback_fn

    @staticmethod
    def extract_sip_username(request_body: Dict[str, Any]) -> Optional[str]:
        """
        Extract SIP username from request body
        
        This extracts the username portion of a SIP URI from the 'to' field
        in the call data of a request body.
        
        Args:
            request_body: The parsed JSON body of the request
            
        Returns:
            The extracted SIP username, or None if not found
        """
        try:
            # Check if we have call data with a 'to' field
            if "call" in request_body and "to" in request_body["call"]:
                to_field = request_body["call"]["to"]
                
                # Handle SIP URIs like "sip:username@domain"
                if to_field.startswith("sip:"):
                    # Extract username part (between "sip:" and "@")
                    uri_parts = to_field[4:].split("@", 1)
                    if uri_parts:
                        return uri_parts[0]
                        
                # Handle TEL URIs like "tel:+1234567890"
                elif to_field.startswith("tel:"):
                    # Extract phone number part
                    return to_field[4:]
                    
                # Otherwise, return the whole 'to' field
                else:
                    return to_field
        except (KeyError, AttributeError):
            # If any exception occurs during extraction, return None
            pass
            
        return None
        
    async def _handle_request(self, request: Request, response: Response):
        """
        Internal handler for both GET and POST requests
        
        Args:
            request: FastAPI Request object
            response: FastAPI Response object
            
        Returns:
            Response with SWML document or error
        """
        # Check auth
        if not self._check_basic_auth(request):
            response.headers["WWW-Authenticate"] = "Basic"
            return HTTPException(status_code=401, detail="Unauthorized")
        
        # Process request body if it's a POST
        body = {}
        if request.method == "POST":
            try:
                raw_body = await request.body()
                if raw_body:
                    body = await request.json()
                    
                    # Check if we have a routing callback and should reroute the request
                    if self._routing_callback is not None:
                        self.log.debug("checking_routing", body_keys=list(body.keys()))
                        route = self._routing_callback(request, body)
                        
                        if route is not None:
                            self.log.info("routing_request", route=route)
                            # We should return a redirect to the new route
                            # Use 307 to preserve the POST method and its body
                            response = Response(status_code=307)
                            response.headers["Location"] = route
                            return response
            except Exception as e:
                self.log.error("error_parsing_body", error=str(e))
                # Continue with empty body if parsing fails
                pass
        
        # Allow for customized handling in subclasses
        modifications = self.on_request(body)
        
        # Apply any modifications if needed
        if modifications and isinstance(modifications, dict):
            # Get a copy of the current document
            document = self.get_document()
            
            # Apply modifications (simplified implementation)
            # In a real implementation, you might want a more sophisticated merge strategy
            for key, value in modifications.items():
                if key in document:
                    document[key] = value
            
            # Create a new document with the modifications
            modified_doc = json.dumps(document)
            return Response(content=modified_doc, media_type="application/json")
        
        # Get the current SWML document
        swml = self.render_document()
        
        # Return the SWML document
        return Response(content=swml, media_type="application/json")
    
    def on_request(self, request_data: Optional[dict] = None) -> Optional[dict]:
        """
        Called when SWML is requested, with request data when available
        
        Subclasses can override this to inspect or modify SWML based on the request
        
        Args:
            request_data: Optional dictionary containing the parsed POST body
            
        Returns:
            Optional dict to modify/augment the SWML document
        """
        # Default implementation does nothing
        return None
    
    def serve(self, host: Optional[str] = None, port: Optional[int] = None, 
              ssl_cert: Optional[str] = None, ssl_key: Optional[str] = None, 
              ssl_enabled: Optional[bool] = None, domain: Optional[str] = None) -> None:
        """
        Start a web server for this service
        
        Args:
            host: Optional host to override the default
            port: Optional port to override the default
            ssl_cert: Path to SSL certificate file
            ssl_key: Path to SSL private key file
            ssl_enabled: Whether to enable SSL/HTTPS
            domain: Domain name for the SSL certificate and external URLs
        """
        import uvicorn
        
        # Determine SSL settings from parameters or environment variables
        self.ssl_enabled = ssl_enabled if ssl_enabled is not None else os.environ.get('SWML_SSL_ENABLED', '').lower() in ('true', '1', 'yes')
        ssl_cert_path = ssl_cert or os.environ.get('SWML_SSL_CERT_PATH', '')
        ssl_key_path = ssl_key or os.environ.get('SWML_SSL_KEY_PATH', '')
        self.domain = domain or os.environ.get('SWML_DOMAIN', '')
        
        # Validate SSL configuration if enabled
        if self.ssl_enabled:
            if not ssl_cert_path or not os.path.exists(ssl_cert_path):
                self.log.warning("ssl_cert_not_found", path=ssl_cert_path)
                self.ssl_enabled = False
            elif not ssl_key_path or not os.path.exists(ssl_key_path):
                self.log.warning("ssl_key_not_found", path=ssl_key_path)
                self.ssl_enabled = False
            elif not self.domain:
                self.log.warning("ssl_domain_not_specified")
                # We'll continue, but URLs might not be correctly generated
        
        if self._app is None:
            app = FastAPI()
            router = self.as_router()
            app.include_router(router, prefix=self.route)
            self._app = app
        
        host = host or self.host
        port = port or self.port
        
        # Print the auth credentials
        username, password = self._basic_auth
        
        # Use correct protocol and host in displayed URL
        protocol = "https" if self.ssl_enabled else "http"
        display_host = self.domain if self.ssl_enabled and self.domain else f"{host}:{port}"
        
        self.log.info("starting_server", 
                     url=f"{protocol}://{display_host}{self.route}",
                     ssl_enabled=self.ssl_enabled,
                     username=username,
                     password_length=len(password))
        
        print(f"Service '{self.name}' is available at:")
        print(f"URL: {protocol}://{display_host}{self.route}")
        print(f"Basic Auth: {username}:{password}")
        
        # Check if SIP routing is enabled and print additional info
        if self._routing_callback is not None:
            print(f"SIP endpoint: {protocol}://{display_host}/sip")
        
        # Start uvicorn with or without SSL
        if self.ssl_enabled and ssl_cert_path and ssl_key_path:
            self.log.info("starting_with_ssl", cert=ssl_cert_path, key=ssl_key_path)
            uvicorn.run(
                self._app, 
                host=host, 
                port=port,
                ssl_certfile=ssl_cert_path,
                ssl_keyfile=ssl_key_path
            )
        else:
            uvicorn.run(self._app, host=host, port=port)
    
    def stop(self) -> None:
        """
        Stop the web server
        """
        self._running = False
    
    def _check_basic_auth(self, request: Request) -> bool:
        """
        Check if the request has valid basic auth credentials
        
        Args:
            request: FastAPI Request object
            
        Returns:
            True if auth is valid, False otherwise
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return False
        
        # Extract the credentials from the header
        try:
            scheme, credentials = auth_header.split()
            if scheme.lower() != "basic":
                return False
            
            decoded = base64.b64decode(credentials).decode("utf-8")
            username, password = decoded.split(":")
            
            # Compare with our credentials
            expected_username, expected_password = self._basic_auth
            return username == expected_username and password == expected_password
        except Exception:
            return False
    
    def get_basic_auth_credentials(self, include_source: bool = False) -> Union[Tuple[str, str], Tuple[str, str, str]]:
        """
        Get the basic auth credentials
        
        Args:
            include_source: Whether to include the source of the credentials
            
        Returns:
            (username, password) tuple or (username, password, source) tuple if include_source is True
        """
        username, password = self._basic_auth
        
        if include_source:
            # Determine source
            env_user = os.environ.get('SWML_BASIC_AUTH_USER')
            env_pass = os.environ.get('SWML_BASIC_AUTH_PASSWORD')
            
            if env_user and env_pass and env_user == username and env_pass == password:
                source = "environment"
            else:
                source = "auto-generated"
                
            return username, password, source
        
        return username, password
    
    # Keep the existing methods for backward compatibility
    
    def add_answer_verb(self, max_duration: Optional[int] = None, codecs: Optional[str] = None) -> bool:
        """
        Add an answer verb to the current document
        
        Args:
            max_duration: Maximum duration in seconds
            codecs: Comma-separated list of codecs
            
        Returns:
            True if added successfully, False otherwise
        """
        config = {}
        if max_duration is not None:
            config["max_duration"] = max_duration
        if codecs is not None:
            config["codecs"] = codecs
            
        return self.add_verb("answer", config)
    
    def add_hangup_verb(self, reason: Optional[str] = None) -> bool:
        """
        Add a hangup verb to the current document
        
        Args:
            reason: Hangup reason (hangup, busy, decline)
            
        Returns:
            True if added successfully, False otherwise
        """
        config = {}
        if reason is not None:
            config["reason"] = reason
            
        return self.add_verb("hangup", config)
    
    def add_ai_verb(self, 
               prompt_text: Optional[str] = None,
               prompt_pom: Optional[List[Dict[str, Any]]] = None,
               post_prompt: Optional[str] = None,
               post_prompt_url: Optional[str] = None,
               swaig: Optional[Dict[str, Any]] = None,
               **kwargs) -> bool:
        """
        Add an AI verb to the current document
        
        Args:
            prompt_text: Simple prompt text
            prompt_pom: Prompt object model
            post_prompt: Post-prompt text
            post_prompt_url: Post-prompt URL
            swaig: SWAIG configuration
            **kwargs: Additional parameters
            
        Returns:
            True if added successfully, False otherwise
        """
        config = {}
        
        # Handle prompt
        if prompt_text is not None:
            config["prompt"] = prompt_text
        elif prompt_pom is not None:
            config["prompt"] = prompt_pom
            
        # Handle post prompt
        if post_prompt is not None:
            config["post_prompt"] = post_prompt
        
        # Handle post prompt URL
        if post_prompt_url is not None:
            config["post_prompt_url"] = post_prompt_url
            
        # Handle SWAIG
        if swaig is not None:
            config["SWAIG"] = swaig
            
        # Handle additional parameters
        for key, value in kwargs.items():
            if value is not None:
                config[key] = value
                
        return self.add_verb("ai", config)
        
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
        if hasattr(self, '_proxy_url_base') and getattr(self, '_proxy_url_base', None):
            # For proxy URLs
            base = self._proxy_url_base.rstrip('/')
            
            # Always add auth credentials
            username, password = self._basic_auth
            url = urlparse(base)
            base = url._replace(netloc=f"{username}:{password}@{url.netloc}").geturl()
        else:
            # Determine protocol based on SSL settings
            protocol = "https" if getattr(self, 'ssl_enabled', False) else "http"
            
            # Use domain if available and SSL is enabled
            if getattr(self, 'ssl_enabled', False) and getattr(self, 'domain', None):
                host_part = self.domain
            else:
                # For local URLs
                if self.host in ("0.0.0.0", "127.0.0.1", "localhost"):
                    host = "localhost"
                else:
                    host = self.host
                
                host_part = f"{host}:{self.port}"
                
            # Always include auth credentials
            username, password = self._basic_auth
            base = f"{protocol}://{username}:{password}@{host_part}"
        
        # Ensure the endpoint has a trailing slash to prevent redirects
        if endpoint and not endpoint.endswith('/'):
            endpoint = f"{endpoint}/"
            
        # Simple path - use the route directly with the endpoint
        path = f"{self.route}/{endpoint}"
            
        # Construct full URL
        url = f"{base}{path}"
        
        # Add query parameters if any (only if they have values)
        if query_params:
            filtered_params = {k: v for k, v in query_params.items() if v}
            if filtered_params:
                params = "&".join([f"{k}={v}" for k, v in filtered_params.items()])
                url = f"{url}?{params}"
            
        return url 