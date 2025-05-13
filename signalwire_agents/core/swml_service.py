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
from typing import Dict, List, Any, Optional, Union, Callable, Tuple, Type

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
        
        # Try to find the schema file if not provided
        if schema_path is None:
            # Try different locations
            import sys
            
            # Get package directory
            package_dir = os.path.dirname(os.path.dirname(__file__))
            
            # Potential locations for schema.json
            potential_paths = [
                os.path.join(os.getcwd(), "schema.json"),  # Current working directory
                os.path.join(package_dir, "schema.json"),  # Package directory
                os.path.join(os.path.dirname(package_dir), "schema.json"),  # Parent of package directory
                os.path.join(sys.prefix, "schema.json"),  # Python installation directory
            ]
            
            # Try to find the schema file
            for path in potential_paths:
                if os.path.exists(path):
                    schema_path = path
                    break
        
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
    
    def add_verb(self, verb_name: str, config: Dict[str, Any]) -> bool:
        """
        Add a verb to the main section of the current document
        
        Args:
            verb_name: The name of the verb to add
            config: Configuration for the verb
            
        Returns:
            True if the verb was added successfully, False otherwise
        """
        # Check if we have a specialized handler for this verb
        if self.verb_registry.has_handler(verb_name):
            handler = self.verb_registry.get_handler(verb_name)
            is_valid, errors = handler.validate_config(config)
        else:
            # Use schema-based validation for standard verbs
            is_valid, errors = self.schema_utils.validate_verb(verb_name, config)
        
        if not is_valid:
            # Log validation errors
            print(f"Validation errors for verb '{verb_name}':")
            for error in errors:
                print(f"  - {error}")
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
    
    def add_verb_to_section(self, section_name: str, verb_name: str, config: Dict[str, Any]) -> bool:
        """
        Add a verb to a specific section
        
        Args:
            section_name: Name of the section to add to
            verb_name: The name of the verb to add
            config: Configuration for the verb
            
        Returns:
            True if the verb was added successfully, False otherwise
        """
        # Make sure the section exists
        if section_name not in self._current_document["sections"]:
            self.add_section(section_name)
        
        # Check if we have a specialized handler for this verb
        if self.verb_registry.has_handler(verb_name):
            handler = self.verb_registry.get_handler(verb_name)
            is_valid, errors = handler.validate_config(config)
        else:
            # Use schema-based validation for standard verbs
            is_valid, errors = self.schema_utils.validate_verb(verb_name, config)
        
        if not is_valid:
            # Log validation errors
            print(f"Validation errors for verb '{verb_name}' in section '{section_name}':")
            for error in errors:
                print(f"  - {error}")
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
        
        self._router = router
        return router
    
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
            except Exception:
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
    
    def serve(self, host: Optional[str] = None, port: Optional[int] = None) -> None:
        """
        Start a web server for this service
        
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
        
        # Print the auth credentials
        username, password = self._basic_auth
        print(f"Service '{self.name}' is available at:")
        print(f"URL: http://{host}:{port}{self.route}")
        print(f"Basic Auth: {username}:{password}")
        
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
    
    def get_basic_auth_credentials(self) -> Tuple[str, str]:
        """
        Get the basic auth credentials
        
        Returns:
            (username, password) tuple
        """
        return self._basic_auth

    def add_answer_verb(self, max_duration: Optional[int] = None, codecs: Optional[str] = None) -> bool:
        """
        Add an 'answer' verb to the main section
        
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
        Add a 'hangup' verb to the main section
        
        Args:
            reason: Optional reason for hangup
            
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
        Add an 'ai' verb to the main section
        
        Args:
            prompt_text: Text prompt for the AI (mutually exclusive with prompt_pom)
            prompt_pom: POM structure for the AI prompt (mutually exclusive with prompt_text)
            post_prompt: Optional post-prompt text
            post_prompt_url: Optional URL for post-prompt processing
            swaig: Optional SWAIG configuration
            **kwargs: Additional AI parameters
            
        Returns:
            True if added successfully, False otherwise
        """
        # Get the AI verb handler
        handler = self.verb_registry.get_handler("ai")
        if not handler:
            print("Error: AI verb handler not found")
            return False
        
        # Build the configuration
        try:
            config = handler.build_config(
                prompt_text=prompt_text,
                prompt_pom=prompt_pom,
                post_prompt=post_prompt,
                post_prompt_url=post_prompt_url,
                swaig=swaig,
                **kwargs
            )
        except ValueError as e:
            print(f"Error building AI verb configuration: {str(e)}")
            return False
        
        # Add the verb
        return self.add_verb("ai", config) 