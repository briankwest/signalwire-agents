#!/usr/bin/env python3
"""
SWAIG Function CLI Testing Tool

This tool loads an agent application and calls SWAIG functions with comprehensive
simulation of the SignalWire environment. It supports both webhook and DataMap functions.

Usage:
    python -m signalwire_agents.cli.test_swaig <agent_path> <tool_name> <args_json>
    
    # Or directly:
    python signalwire_agents/cli/test_swaig.py <agent_path> <tool_name> <args_json>
    
    # Or as installed command:
    swaig-test <agent_path> <tool_name> <args_json>
    
Examples:
    # Test DataSphere search
    swaig-test examples/datasphere_webhook_env_demo.py search_knowledge '{"query":"test search"}'
    
    # Test DataMap function
    swaig-test examples/my_agent.py my_datamap_func '{"input":"value"}' --datamap
    
    # Test with custom post_data
    swaig-test examples/my_agent.py my_tool '{"param":"value"}' --fake-full-data
    
    # Test with minimal data
    swaig-test examples/my_agent.py my_tool '{"param":"value"}' --minimal
    
    # List available tools
    swaig-test examples/my_agent.py --list-tools
    
    # Dump SWML document
    swaig-test examples/my_agent.py --dump-swml
    
    # Dump SWML with verbose output
    swaig-test examples/my_agent.py --dump-swml --verbose
    
    # Dump raw SWML JSON (for piping to jq/yq)
    swaig-test examples/my_agent.py --dump-swml --raw
    
    # Pipe to jq for pretty formatting
    swaig-test examples/my_agent.py --dump-swml --raw | jq '.'
    
    # Extract specific fields with jq
    swaig-test examples/my_agent.py --dump-swml --raw | jq '.sections.main[1].ai.SWAIG.functions'
"""

# CRITICAL: Set environment variable BEFORE any imports to suppress logs for --raw
import sys
import os

if "--raw" in sys.argv or "--dump-swml" in sys.argv:
    os.environ["SIGNALWIRE_LOG_MODE"] = "off"

import warnings
import json
import importlib.util
import argparse
import uuid
import time
import hashlib
import re
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import logging
import inspect

# Store original print function before any potential suppression
original_print = print

# Add the parent directory to the path so we can import signalwire_agents
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    # Try to import the AgentBase class
    from signalwire_agents.core.agent_base import AgentBase
    from signalwire_agents.core.function_result import SwaigFunctionResult
except ImportError:
    # If import fails, we'll handle it gracefully
    AgentBase = None
    SwaigFunctionResult = None

# Reset logging configuration if --raw flag was set
# This must happen AFTER signalwire_agents imports but BEFORE any logging is used
if "--raw" in sys.argv or "--dump-swml" in sys.argv:
    try:
        from signalwire_agents.core.logging_config import reset_logging_configuration, configure_logging
        reset_logging_configuration()
        configure_logging()  # Reconfigure with the new environment variable
    except ImportError:
        pass

# ===== MOCK REQUEST OBJECTS FOR DYNAMIC AGENT TESTING =====

class MockQueryParams:
    """Mock FastAPI QueryParams (case-sensitive dict-like)"""
    def __init__(self, params: Optional[Dict[str, str]] = None):
        self._params = params or {}
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self._params.get(key, default)
    
    def __getitem__(self, key: str) -> str:
        return self._params[key]
    
    def __contains__(self, key: str) -> bool:
        return key in self._params
    
    def items(self):
        return self._params.items()
    
    def keys(self):
        return self._params.keys()
    
    def values(self):
        return self._params.values()


class MockHeaders:
    """Mock FastAPI Headers (case-insensitive dict-like)"""
    def __init__(self, headers: Optional[Dict[str, str]] = None):
        # Store headers with lowercase keys for case-insensitive lookup
        self._headers = {}
        if headers:
            for k, v in headers.items():
                self._headers[k.lower()] = v
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self._headers.get(key.lower(), default)
    
    def __getitem__(self, key: str) -> str:
        return self._headers[key.lower()]
    
    def __contains__(self, key: str) -> bool:
        return key.lower() in self._headers
    
    def items(self):
        return self._headers.items()
    
    def keys(self):
        return self._headers.keys()
    
    def values(self):
        return self._headers.values()


class MockURL:
    """Mock FastAPI URL object"""
    def __init__(self, url: str = "http://localhost:8080/swml"):
        self._url = url
        # Parse basic components
        if "?" in url:
            self.path, query_string = url.split("?", 1)
            self.query = query_string
        else:
            self.path = url
            self.query = ""
        
        # Extract scheme and netloc
        if "://" in url:
            self.scheme, rest = url.split("://", 1)
            if "/" in rest:
                self.netloc = rest.split("/", 1)[0]
            else:
                self.netloc = rest
        else:
            self.scheme = "http"
            self.netloc = "localhost:8080"
    
    def __str__(self):
        return self._url


class MockRequest:
    """Mock FastAPI Request object for dynamic agent testing"""
    def __init__(self, method: str = "POST", url: str = "http://localhost:8080/swml",
                 headers: Optional[Dict[str, str]] = None,
                 query_params: Optional[Dict[str, str]] = None,
                 json_body: Optional[Dict[str, Any]] = None):
        self.method = method
        self.url = MockURL(url)
        self.headers = MockHeaders(headers)
        self.query_params = MockQueryParams(query_params)
        self._json_body = json_body or {}
        self._body = json.dumps(self._json_body).encode('utf-8')
    
    async def json(self) -> Dict[str, Any]:
        """Return the JSON body"""
        return self._json_body
    
    async def body(self) -> bytes:
        """Return the raw body bytes"""
        return self._body
    
    def client(self):
        """Mock client property"""
        return type('MockClient', (), {'host': '127.0.0.1', 'port': 0})()


def create_mock_request(method: str = "POST", url: str = "http://localhost:8080/swml",
                       headers: Optional[Dict[str, str]] = None,
                       query_params: Optional[Dict[str, str]] = None,
                       body: Optional[Dict[str, Any]] = None) -> MockRequest:
    """
    Factory function to create a mock FastAPI Request object
    """
    return MockRequest(method=method, url=url, headers=headers, 
                      query_params=query_params, json_body=body)


# ===== SERVERLESS ENVIRONMENT SIMULATION =====

class ServerlessSimulator:
    """Manages serverless environment simulation for different platforms"""
    
    # Default environment presets for each platform
    PLATFORM_PRESETS = {
        'lambda': {
            'AWS_LAMBDA_FUNCTION_NAME': 'test-agent-function',
            'AWS_LAMBDA_FUNCTION_URL': 'https://abc123.lambda-url.us-east-1.on.aws/',
            'AWS_REGION': 'us-east-1',
            '_HANDLER': 'lambda_function.lambda_handler'
        },
        'cgi': {
            'GATEWAY_INTERFACE': 'CGI/1.1',
            'HTTP_HOST': 'example.com',
            'SCRIPT_NAME': '/cgi-bin/agent.cgi',
            'HTTPS': 'on',
            'SERVER_NAME': 'example.com'
        },
        'cloud_function': {
            'GOOGLE_CLOUD_PROJECT': 'test-project',
            'FUNCTION_URL': 'https://my-function-abc123.cloudfunctions.net',
            'GOOGLE_CLOUD_REGION': 'us-central1',
            'K_SERVICE': 'agent'
        },
        'azure_function': {
            'AZURE_FUNCTIONS_ENVIRONMENT': 'Development',
            'FUNCTIONS_WORKER_RUNTIME': 'python',
            'WEBSITE_SITE_NAME': 'my-function-app'
        }
    }
    
    def __init__(self, platform: str, overrides: Optional[Dict[str, str]] = None):
        self.platform = platform
        self.original_env = dict(os.environ)
        self.preset_env = self.PLATFORM_PRESETS.get(platform, {}).copy()
        self.overrides = overrides or {}
        self.active = False
        self._cleared_vars = {}
    
    def activate(self, verbose: bool = False):
        """Apply serverless environment simulation"""
        if self.active:
            return
            
        # Clear conflicting environment variables
        self._clear_conflicting_env()
        
        # Apply preset environment
        os.environ.update(self.preset_env)
        
        # Apply user overrides
        os.environ.update(self.overrides)
        
        # Set appropriate logging mode for serverless simulation
        if self.platform == 'cgi' and 'SIGNALWIRE_LOG_MODE' not in self.overrides:
            # CGI mode should default to 'off' unless explicitly overridden
            os.environ['SIGNALWIRE_LOG_MODE'] = 'off'
        
        self.active = True
        
        if verbose:
            print(f"✓ Activated {self.platform} environment simulation")
            
            # Debug: Show key environment variables
            if self.platform == 'lambda':
                print(f"  AWS_LAMBDA_FUNCTION_NAME: {os.environ.get('AWS_LAMBDA_FUNCTION_NAME')}")
                print(f"  AWS_LAMBDA_FUNCTION_URL: {os.environ.get('AWS_LAMBDA_FUNCTION_URL')}")
                print(f"  AWS_REGION: {os.environ.get('AWS_REGION')}")
            elif self.platform == 'cgi':
                print(f"  GATEWAY_INTERFACE: {os.environ.get('GATEWAY_INTERFACE')}")
                print(f"  HTTP_HOST: {os.environ.get('HTTP_HOST')}")
                print(f"  SCRIPT_NAME: {os.environ.get('SCRIPT_NAME')}")
                print(f"  SIGNALWIRE_LOG_MODE: {os.environ.get('SIGNALWIRE_LOG_MODE')}")
            elif self.platform == 'cloud_function':
                print(f"  GOOGLE_CLOUD_PROJECT: {os.environ.get('GOOGLE_CLOUD_PROJECT')}")
                print(f"  FUNCTION_URL: {os.environ.get('FUNCTION_URL')}")
                print(f"  GOOGLE_CLOUD_REGION: {os.environ.get('GOOGLE_CLOUD_REGION')}")
            elif self.platform == 'azure_function':
                print(f"  AZURE_FUNCTIONS_ENVIRONMENT: {os.environ.get('AZURE_FUNCTIONS_ENVIRONMENT')}")
                print(f"  WEBSITE_SITE_NAME: {os.environ.get('WEBSITE_SITE_NAME')}")
            
            # Debug: Confirm SWML_PROXY_URL_BASE is cleared
            proxy_url = os.environ.get('SWML_PROXY_URL_BASE')
            if proxy_url:
                print(f"  WARNING: SWML_PROXY_URL_BASE still set: {proxy_url}")
            else:
                print(f"  ✓ SWML_PROXY_URL_BASE cleared successfully")
    
    def deactivate(self, verbose: bool = False):
        """Restore original environment"""
        if not self.active:
            return
            
        os.environ.clear()
        os.environ.update(self.original_env)
        self.active = False
        
        if verbose:
            print(f"✓ Deactivated {self.platform} environment simulation")
    
    def _clear_conflicting_env(self):
        """Clear environment variables that might conflict with simulation"""
        # Remove variables from other platforms
        conflicting_vars = []
        for platform, preset in self.PLATFORM_PRESETS.items():
            if platform != self.platform:
                conflicting_vars.extend(preset.keys())
        
        # Always clear SWML_PROXY_URL_BASE during serverless simulation
        # so that platform-specific URL generation takes precedence
        conflicting_vars.append('SWML_PROXY_URL_BASE')
        
        for var in conflicting_vars:
            if var in os.environ:
                self._cleared_vars[var] = os.environ[var]
                os.environ.pop(var)
    
    def add_override(self, key: str, value: str):
        """Add an environment variable override"""
        self.overrides[key] = value
        if self.active:
            os.environ[key] = value
    
    def get_current_env(self) -> Dict[str, str]:
        """Get the current environment that would be applied"""
        env = self.preset_env.copy()
        env.update(self.overrides)
        return env


def load_env_file(env_file_path: str) -> Dict[str, str]:
    """Load environment variables from a file"""
    env_vars = {}
    if not os.path.exists(env_file_path):
        raise FileNotFoundError(f"Environment file not found: {env_file_path}")
    
    with open(env_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars


# ===== FAKE SWML POST DATA GENERATION =====

def generate_fake_uuid() -> str:
    """Generate a fake UUID for testing"""
    return str(uuid.uuid4())


def generate_fake_node_id() -> str:
    """Generate a fake node ID for testing"""
    return f"test-node-{uuid.uuid4().hex[:8]}"


def generate_fake_sip_from(call_type: str) -> str:
    """Generate a fake 'from' address based on call type"""
    if call_type == "sip":
        return f"+1555{uuid.uuid4().hex[:7]}"  # Fake phone number
    else:  # webrtc
        return f"user-{uuid.uuid4().hex[:8]}@test.domain"


def generate_fake_sip_to(call_type: str) -> str:
    """Generate a fake 'to' address based on call type"""
    if call_type == "sip":
        return f"+1444{uuid.uuid4().hex[:7]}"  # Fake phone number
    else:  # webrtc
        return f"agent-{uuid.uuid4().hex[:8]}@test.domain"


def adapt_for_call_type(call_data: Dict[str, Any], call_type: str) -> Dict[str, Any]:
    """
    Adapt call data structure based on call type (sip vs webrtc)
    
    Args:
        call_data: Base call data structure
        call_type: "sip" or "webrtc"
        
    Returns:
        Adapted call data with appropriate addresses and metadata
    """
    call_data = call_data.copy()
    
    # Update addresses based on call type
    call_data["from"] = generate_fake_sip_from(call_type)
    call_data["to"] = generate_fake_sip_to(call_type)
    
    # Add call type specific metadata
    if call_type == "sip":
        call_data["type"] = "phone"
        call_data["headers"] = {
            "User-Agent": f"Test-SIP-Client/1.0.0",
            "From": f"<sip:{call_data['from']}@test.sip.provider>",
            "To": f"<sip:{call_data['to']}@test.sip.provider>",
            "Call-ID": call_data["call_id"]
        }
    else:  # webrtc
        call_data["type"] = "webrtc"
        call_data["headers"] = {
            "User-Agent": "Test-WebRTC-Client/1.0.0",
            "Origin": "https://test.webrtc.app",
            "Sec-WebSocket-Protocol": "sip"
        }
    
    return call_data


def generate_fake_swml_post_data(call_type: str = "webrtc", 
                                call_direction: str = "inbound",
                                call_state: str = "created") -> Dict[str, Any]:
    """
    Generate fake SWML post_data that matches real SignalWire structure
    
    Args:
        call_type: "sip" or "webrtc" (default: webrtc)
        call_direction: "inbound" or "outbound" (default: inbound)
        call_state: Call state (default: created)
        
    Returns:
        Fake post_data dict with call, vars, and envs structure
    """
    call_id = generate_fake_uuid()
    project_id = generate_fake_uuid()
    space_id = generate_fake_uuid()
    current_time = datetime.now().isoformat()
    
    # Base call structure
    call_data = {
        "call_id": call_id,
        "node_id": generate_fake_node_id(),
        "segment_id": generate_fake_uuid(),
        "call_session_id": generate_fake_uuid(),
        "tag": call_id,
        "state": call_state,
        "direction": call_direction,
        "type": call_type,
        "from": generate_fake_sip_from(call_type),
        "to": generate_fake_sip_to(call_type),
        "timeout": 30,
        "max_duration": 14400,
        "answer_on_bridge": False,
        "hangup_after_bridge": True,
        "ringback": [],
        "record": {},
        "project_id": project_id,
        "space_id": space_id,
        "created_at": current_time,
        "updated_at": current_time
    }
    
    # Adapt for specific call type
    call_data = adapt_for_call_type(call_data, call_type)
    
    # Complete post_data structure
    post_data = {
        "call": call_data,
        "vars": {
            "userVariables": {}  # Empty by default, can be filled via overrides
        },
        "envs": {}  # Empty by default, can be filled via overrides
    }
    
    return post_data


# ===== OVERRIDE SYSTEM =====

def set_nested_value(data: Dict[str, Any], path: str, value: Any) -> None:
    """
    Set a nested value using dot notation path
    
    Args:
        data: Dictionary to modify
        path: Dot-notation path (e.g., "call.call_id" or "vars.userVariables.custom")
        value: Value to set
    """
    keys = path.split('.')
    current = data
    
    # Navigate to the parent of the target key
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    # Set the final value
    current[keys[-1]] = value


def parse_value(value_str: str) -> Any:
    """
    Parse a string value into appropriate Python type
    
    Args:
        value_str: String representation of value
        
    Returns:
        Parsed value (str, int, float, bool, None, or JSON object)
    """
    # Handle special values
    if value_str.lower() == 'null':
        return None
    elif value_str.lower() == 'true':
        return True
    elif value_str.lower() == 'false':
        return False
    
    # Try parsing as number
    try:
        if '.' in value_str:
            return float(value_str)
        else:
            return int(value_str)
    except ValueError:
        pass
    
    # Try parsing as JSON (for objects/arrays)
    try:
        return json.loads(value_str)
    except json.JSONDecodeError:
        pass
    
    # Return as string
    return value_str


def apply_overrides(data: Dict[str, Any], overrides: List[str], 
                   json_overrides: List[str]) -> Dict[str, Any]:
    """
    Apply override values to data using dot notation paths
    
    Args:
        data: Data dictionary to modify
        overrides: List of "path=value" strings
        json_overrides: List of "path=json_value" strings
        
    Returns:
        Modified data dictionary
    """
    data = data.copy()
    
    # Apply simple overrides
    for override in overrides:
        if '=' not in override:
            continue
        path, value_str = override.split('=', 1)
        value = parse_value(value_str)
        set_nested_value(data, path, value)
    
    # Apply JSON overrides
    for json_override in json_overrides:
        if '=' not in json_override:
            continue
        path, json_str = json_override.split('=', 1)
        try:
            value = json.loads(json_str)
            set_nested_value(data, path, value)
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in override '{json_override}': {e}")
    
    return data


def apply_convenience_mappings(data: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    """
    Apply convenience CLI arguments to data structure
    
    Args:
        data: Data dictionary to modify
        args: Parsed CLI arguments
        
    Returns:
        Modified data dictionary
    """
    data = data.copy()
    
    # Map high-level arguments to specific paths
    if hasattr(args, 'call_id') and args.call_id:
        set_nested_value(data, "call.call_id", args.call_id)
        set_nested_value(data, "call.tag", args.call_id)  # tag often matches call_id
    
    if hasattr(args, 'project_id') and args.project_id:
        set_nested_value(data, "call.project_id", args.project_id)
    
    if hasattr(args, 'space_id') and args.space_id:
        set_nested_value(data, "call.space_id", args.space_id)
    
    if hasattr(args, 'call_state') and args.call_state:
        set_nested_value(data, "call.state", args.call_state)
    
    if hasattr(args, 'call_direction') and args.call_direction:
        set_nested_value(data, "call.direction", args.call_direction)
    
    # Handle from/to addresses with fake generation if needed
    if hasattr(args, 'from_number') and args.from_number:
        # If looks like phone number, use as-is, otherwise generate fake
        if args.from_number.startswith('+') or args.from_number.isdigit():
            set_nested_value(data, "call.from", args.from_number)
        else:
            # Generate fake phone number or SIP address
            call_type = getattr(args, 'call_type', 'webrtc')
            if call_type == 'sip':
                set_nested_value(data, "call.from", f"+1555{uuid.uuid4().hex[:7]}")
            else:
                set_nested_value(data, "call.from", f"{args.from_number}@test.domain")
    
    if hasattr(args, 'to_extension') and args.to_extension:
        # Similar logic for 'to' address
        if args.to_extension.startswith('+') or args.to_extension.isdigit():
            set_nested_value(data, "call.to", args.to_extension)
        else:
            call_type = getattr(args, 'call_type', 'webrtc')
            if call_type == 'sip':
                set_nested_value(data, "call.to", f"+1444{uuid.uuid4().hex[:7]}")
            else:
                set_nested_value(data, "call.to", f"{args.to_extension}@test.domain")
    
    # Merge user variables
    user_vars = {}
    
    # Add user_vars if provided
    if hasattr(args, 'user_vars') and args.user_vars:
        try:
            user_vars.update(json.loads(args.user_vars))
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in --user-vars: {e}")
    
    # Add query_params if provided (merged into userVariables)
    if hasattr(args, 'query_params') and args.query_params:
        try:
            user_vars.update(json.loads(args.query_params))
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in --query-params: {e}")
    
    # Set merged user variables
    if user_vars:
        set_nested_value(data, "vars.userVariables", user_vars)
    
    return data


def handle_dump_swml(agent: 'AgentBase', args: argparse.Namespace) -> int:
    """
    Handle SWML dumping with fake post_data and mock request support
    
    Args:
        agent: The loaded agent instance
        args: Parsed CLI arguments
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    if not args.raw:
        if args.verbose:
            print(f"Agent: {agent.get_name()}")
            print(f"Route: {agent.route}")
            
            # Show loaded skills
            skills = agent.list_skills()
            if skills:
                print(f"Skills: {', '.join(skills)}")
                
            # Show available functions
            if hasattr(agent, '_swaig_functions') and agent._swaig_functions:
                print(f"Functions: {', '.join(agent._swaig_functions.keys())}")
            
            print("-" * 60)
    
    try:
        # Generate fake SWML post_data
        post_data = generate_fake_swml_post_data(
            call_type=args.call_type,
            call_direction=args.call_direction,
            call_state=args.call_state
        )
        
        # Apply convenience mappings from CLI args
        post_data = apply_convenience_mappings(post_data, args)
        
        # Apply explicit overrides
        post_data = apply_overrides(post_data, args.override, args.override_json)
        
        # Parse headers for mock request
        headers = {}
        for header in args.header:
            if '=' in header:
                key, value = header.split('=', 1)
                headers[key] = value
        
        # Parse query params for mock request (separate from userVariables)
        query_params = {}
        if args.query_params:
            try:
                query_params = json.loads(args.query_params)
            except json.JSONDecodeError as e:
                if not args.raw:
                    print(f"Warning: Invalid JSON in --query-params: {e}")
        
        # Parse request body
        request_body = {}
        if args.body:
            try:
                request_body = json.loads(args.body)
            except json.JSONDecodeError as e:
                if not args.raw:
                    print(f"Warning: Invalid JSON in --body: {e}")
        
        # Create mock request object
        mock_request = create_mock_request(
            method=args.method,
            headers=headers,
            query_params=query_params,
            body=request_body
        )
        
        if args.verbose and not args.raw:
            print(f"Using fake SWML post_data:")
            print(json.dumps(post_data, indent=2))
            print(f"\nMock request headers: {dict(mock_request.headers.items())}")
            print(f"Mock request query params: {dict(mock_request.query_params.items())}")
            print(f"Mock request method: {mock_request.method}")
            print("-" * 60)
        
        # For dynamic agents, call on_swml_request if available
        if hasattr(agent, 'on_swml_request'):
            try:
                # Dynamic agents expect (request_data, callback_path, request)
                call_id = post_data.get('call', {}).get('call_id', 'test-call-id')
                modifications = agent.on_swml_request(post_data, "/swml", mock_request)
                
                if args.verbose and not args.raw:
                    print(f"Dynamic agent modifications: {modifications}")
                
                # Generate SWML with modifications
                swml_doc = agent._render_swml(call_id, modifications)
            except Exception as e:
                if args.verbose and not args.raw:
                    print(f"Dynamic agent callback failed, falling back to static SWML: {e}")
                # Fall back to static SWML generation
                swml_doc = agent._render_swml()
        else:
            # Static agent - generate SWML normally
            swml_doc = agent._render_swml()
        
        if args.raw:
            # Temporarily restore print for JSON output
            if '--raw' in sys.argv and 'original_print' in globals():
                import builtins
                builtins.print = original_print
            
            # Output only the raw JSON for piping to jq/yq
            print(swml_doc)
        else:
            # Output formatted JSON (like raw but pretty-printed)
            try:
                swml_parsed = json.loads(swml_doc)
                print(json.dumps(swml_parsed, indent=2))
            except json.JSONDecodeError:
                # If not valid JSON, show raw
                print(swml_doc)
        
        return 0
        
    except Exception as e:
        if args.raw:
            # For raw mode, output error to stderr to not interfere with JSON output
            original_print(f"Error generating SWML: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc(file=sys.stderr)
        else:
            print(f"Error generating SWML: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
        return 1


def setup_raw_mode_suppression():
    """Set up output suppression for raw mode using central logging system"""
    # The central logging system is already configured via environment variable
    # Just suppress any remaining warnings
    warnings.filterwarnings("ignore")
    
    # Capture and suppress print statements in raw mode if needed
    def suppressed_print(*args, **kwargs):
        pass
    
    # Replace print function globally for raw mode
    import builtins
    builtins.print = suppressed_print


def generate_comprehensive_post_data(function_name: str, args: Dict[str, Any], 
                                    custom_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generate comprehensive post_data that matches what SignalWire would send
    
    Args:
        function_name: Name of the SWAIG function being called
        args: Function arguments
        custom_data: Optional custom data to override defaults
        
    Returns:
        Complete post_data dict with all possible keys
    """
    call_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    current_time = datetime.now().isoformat()
    
    # Generate meta_data_token (normally function name + webhook URL hash)
    meta_data_token = hashlib.md5(f"{function_name}_test_webhook".encode()).hexdigest()[:16]
    
    base_data = {
        # Core identification 
        "function": function_name,
        "argument": args,
        "call_id": call_id,
        "call_session_id": session_id,
        "node_id": "test-node-001",
        
        # Metadata and function-level data
        "meta_data_token": meta_data_token,
        "meta_data": {
            "test_mode": True,
            "function_name": function_name,
            "last_updated": current_time
        },
        
        # Global application data
        "global_data": {
            "app_name": "test_application",
            "environment": "test",
            "user_preferences": {"language": "en"},
            "session_data": {"start_time": current_time}
        },
        
        # Conversation context
        "call_log": [
            {
                "role": "system",
                "content": "You are a helpful AI assistant created with SignalWire AI Agents."
            },
            {
                "role": "user", 
                "content": f"Please call the {function_name} function"
            },
            {
                "role": "assistant",
                "content": f"I'll call the {function_name} function for you.",
                "tool_calls": [
                    {
                        "id": f"call_{call_id[:8]}",
                        "type": "function",
                        "function": {
                            "name": function_name,
                            "arguments": json.dumps(args)
                        }
                    }
                ]
            }
        ],
        "raw_call_log": [
            {
                "role": "system",
                "content": "You are a helpful AI assistant created with SignalWire AI Agents."
            },
            {
                "role": "user",
                "content": "Hello"
            },
            {
                "role": "assistant", 
                "content": "Hello! How can I help you today?"
            },
            {
                "role": "user",
                "content": f"Please call the {function_name} function"
            },
            {
                "role": "assistant",
                "content": f"I'll call the {function_name} function for you.",
                "tool_calls": [
                    {
                        "id": f"call_{call_id[:8]}",
                        "type": "function", 
                        "function": {
                            "name": function_name,
                            "arguments": json.dumps(args)
                        }
                    }
                ]
            }
        ],
        
        # SWML and prompt variables
        "prompt_vars": {
            # From SWML prompt variables
            "ai_instructions": "You are a helpful assistant",
            "temperature": 0.7,
            "max_tokens": 1000,
            # From global_data 
            "app_name": "test_application",
            "environment": "test",
            "user_preferences": {"language": "en"},
            "session_data": {"start_time": current_time},
            # SWML system variables
            "current_timestamp": current_time,
            "call_duration": "00:02:15",
            "caller_number": "+15551234567",
            "to_number": "+15559876543"
        },
        
        # Permission flags (from SWML parameters)
        "swaig_allow_swml": True,
        "swaig_post_conversation": True, 
        "swaig_post_swml_vars": True,
        
        # Additional context
        "http_method": "POST",
        "webhook_url": f"https://test.example.com/webhook/{function_name}",
        "user_agent": "SignalWire-AI-Agent/1.0",
        "request_headers": {
            "Content-Type": "application/json",
            "User-Agent": "SignalWire-AI-Agent/1.0",
            "X-Signalwire-Call-Id": call_id,
            "X-Signalwire-Session-Id": session_id
        }
    }
    
    # Merge custom data if provided
    if custom_data:
        def deep_merge(base: Dict, custom: Dict) -> Dict:
            result = base.copy()
            for key, value in custom.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        base_data = deep_merge(base_data, custom_data)
    
    return base_data


def generate_minimal_post_data(function_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Generate minimal post_data with only essential keys"""
    return {
        "function": function_name,
        "argument": args,
        "call_id": str(uuid.uuid4()),
        "meta_data": {},
        "global_data": {}
    }


def simple_template_expand(template: str, data: Dict[str, Any]) -> str:
    """
    Simple template expansion for DataMap testing
    Supports both ${key} and %{key} syntax with nested object access and array indexing
    
    Args:
        template: Template string with ${} or %{} variables
        data: Data dictionary for expansion
        
    Returns:
        Expanded string
    """
    if not template:
        return ""
        
    result = template
    
    # Handle both ${variable.path} and %{variable.path} syntax
    patterns = [
        r'\$\{([^}]+)\}',  # ${variable} syntax
        r'%\{([^}]+)\}'    # %{variable} syntax
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, result):
            var_path = match.group(1)
            
            # Handle array indexing syntax like "array[0].joke"
            if '[' in var_path and ']' in var_path:
                # Split path with array indexing
                parts = []
                current_part = ""
                i = 0
                while i < len(var_path):
                    if var_path[i] == '[':
                        if current_part:
                            parts.append(current_part)
                            current_part = ""
                        # Find the closing bracket
                        j = i + 1
                        while j < len(var_path) and var_path[j] != ']':
                            j += 1
                        if j < len(var_path):
                            index = var_path[i+1:j]
                            parts.append(f"[{index}]")
                            i = j + 1
                            if i < len(var_path) and var_path[i] == '.':
                                i += 1  # Skip the dot after ]
                        else:
                            current_part += var_path[i]
                            i += 1
                    elif var_path[i] == '.':
                        if current_part:
                            parts.append(current_part)
                            current_part = ""
                        i += 1
                    else:
                        current_part += var_path[i]
                        i += 1
                
                if current_part:
                    parts.append(current_part)
                    
                # Navigate through the data structure
                value = data
                try:
                    for part in parts:
                        if part.startswith('[') and part.endswith(']'):
                            # Array index
                            index = int(part[1:-1])
                            if isinstance(value, list) and 0 <= index < len(value):
                                value = value[index]
                            else:
                                value = f"<MISSING:{var_path}>"
                                break
                        else:
                            # Object property
                            if isinstance(value, dict) and part in value:
                                value = value[part]
                            else:
                                value = f"<MISSING:{var_path}>"
                                break
                except (ValueError, TypeError, IndexError):
                    value = f"<MISSING:{var_path}>"
                    
            else:
                # Regular nested object access (no array indexing)
                path_parts = var_path.split('.')
                value = data
                for part in path_parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        value = f"<MISSING:{var_path}>"
                        break
            
            # Replace the variable with its value
            result = result.replace(match.group(0), str(value))
    
    return result


def execute_datamap_function(datamap_config: Dict[str, Any], args: Dict[str, Any], 
                           verbose: bool = False) -> Dict[str, Any]:
    """
    Execute a DataMap function following the actual DataMap processing pipeline:
    1. Expressions (pattern matching)
    2. Webhooks (try each sequentially until one succeeds)
    3. Foreach (within successful webhook)
    4. Output (from successful webhook)
    5. Fallback output (if all webhooks fail)
    
    Args:
        datamap_config: DataMap configuration dictionary
        args: Function arguments
        verbose: Enable verbose output
        
    Returns:
        Function result (should be string or dict with 'response' key)
    """
    if verbose:
        print("=== DataMap Function Execution ===")
        print(f"Config: {json.dumps(datamap_config, indent=2)}")
        print(f"Args: {json.dumps(args, indent=2)}")
    
    # Extract the actual data_map configuration
    # DataMap configs have the structure: {"function": "...", "data_map": {...}}
    actual_datamap = datamap_config.get("data_map", datamap_config)
    
    if verbose:
        print(f"Extracted data_map: {json.dumps(actual_datamap, indent=2)}")
    
    # Initialize context with function arguments
    context = {"args": args}
    context.update(args)  # Also make args available at top level for backward compatibility
    
    if verbose:
        print(f"Initial context: {json.dumps(context, indent=2)}")
    
    # Step 1: Process expressions first (pattern matching)
    if "expressions" in actual_datamap:
        if verbose:
            print("\n--- Processing Expressions ---")
        for expr in actual_datamap["expressions"]:
            # Simple expression evaluation - in real implementation this would be more sophisticated
            if "pattern" in expr and "output" in expr:
                # For testing, we'll just match simple strings
                pattern = expr["pattern"]
                if pattern in str(args):
                    if verbose:
                        print(f"Expression matched: {pattern}")
                    result = simple_template_expand(str(expr["output"]), context)
                    if verbose:
                        print(f"Expression result: {result}")
                    return result
    
    # Step 2: Process webhooks sequentially
    if "webhooks" in actual_datamap:
        if verbose:
            print("\n--- Processing Webhooks ---")
        
        for i, webhook in enumerate(actual_datamap["webhooks"]):
            if verbose:
                print(f"\n=== Webhook {i+1}/{len(actual_datamap['webhooks'])} ===")
            
            url = webhook.get("url", "")
            method = webhook.get("method", "POST").upper()
            headers = webhook.get("headers", {})
            
            # Expand template variables in URL and headers
            url = simple_template_expand(url, context)
            expanded_headers = {}
            for key, value in headers.items():
                expanded_headers[key] = simple_template_expand(str(value), context)
            
            if verbose:
                print(f"Making {method} request to: {url}")
                print(f"Headers: {json.dumps(expanded_headers, indent=2)}")
            
            # Prepare request data
            request_data = None
            if method in ["POST", "PUT", "PATCH"]:
                # Check for 'params' (SignalWire style) or 'data' (generic style) or 'body'
                if "params" in webhook:
                    # Expand template variables in params
                    expanded_params = {}
                    for key, value in webhook["params"].items():
                        expanded_params[key] = simple_template_expand(str(value), context)
                    request_data = json.dumps(expanded_params)
                elif "body" in webhook:
                    # Expand template variables in body
                    if isinstance(webhook["body"], str):
                        request_data = simple_template_expand(webhook["body"], context)
                    else:
                        expanded_body = {}
                        for key, value in webhook["body"].items():
                            expanded_body[key] = simple_template_expand(str(value), context)
                        request_data = json.dumps(expanded_body)
                elif "data" in webhook:
                    # Expand template variables in data
                    if isinstance(webhook["data"], str):
                        request_data = simple_template_expand(webhook["data"], context)
                    else:
                        request_data = json.dumps(webhook["data"])
                
                if verbose and request_data:
                    print(f"Request data: {request_data}")
            
            webhook_failed = False
            response_data = None
            
            try:
                # Make the HTTP request
                if method == "GET":
                    response = requests.get(url, headers=expanded_headers, timeout=30)
                elif method == "POST":
                    response = requests.post(url, data=request_data, headers=expanded_headers, timeout=30)
                elif method == "PUT":
                    response = requests.put(url, data=request_data, headers=expanded_headers, timeout=30)
                elif method == "PATCH":
                    response = requests.patch(url, data=request_data, headers=expanded_headers, timeout=30)
                elif method == "DELETE":
                    response = requests.delete(url, headers=expanded_headers, timeout=30)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                if verbose:
                    print(f"Response status: {response.status_code}")
                    print(f"Response headers: {dict(response.headers)}")
                
                # Parse response
                try:
                    response_data = response.json()
                except json.JSONDecodeError:
                    response_data = {"text": response.text, "status_code": response.status_code}
                    # Add parse_error like server does
                    response_data["parse_error"] = True
                    response_data["raw_response"] = response.text
                
                if verbose:
                    print(f"Response data: {json.dumps(response_data, indent=2)}")
                
                # Check for webhook failure following server logic
                
                # 1. Check HTTP status code (fix the server bug - should be OR not AND)
                if response.status_code < 200 or response.status_code > 299:
                    webhook_failed = True
                    if verbose:
                        print(f"Webhook failed: HTTP status {response.status_code} outside 200-299 range")
                
                # 2. Check for explicit error keys (parse_error, protocol_error)
                if not webhook_failed:
                    explicit_error_keys = ["parse_error", "protocol_error"]
                    for error_key in explicit_error_keys:
                        if error_key in response_data and response_data[error_key]:
                            webhook_failed = True
                            if verbose:
                                print(f"Webhook failed: Found explicit error key '{error_key}' = {response_data[error_key]}")
                            break
                
                # 3. Check for custom error_keys from webhook config
                if not webhook_failed and "error_keys" in webhook:
                    error_keys = webhook["error_keys"]
                    if isinstance(error_keys, str):
                        error_keys = [error_keys]  # Convert single string to list
                    elif not isinstance(error_keys, list):
                        error_keys = []
                    
                    for error_key in error_keys:
                        if error_key in response_data and response_data[error_key]:
                            webhook_failed = True
                            if verbose:
                                print(f"Webhook failed: Found custom error key '{error_key}' = {response_data[error_key]}")
                            break
                
            except Exception as e:
                webhook_failed = True
                if verbose:
                    print(f"Webhook failed: HTTP request exception: {e}")
                # Create error response like server does
                response_data = {
                    "protocol_error": True,
                    "error": str(e)
                }
            
            # If webhook succeeded, process its output
            if not webhook_failed:
                if verbose:
                    print(f"Webhook {i+1} succeeded!")
                
                # Add response data to context
                webhook_context = context.copy()
                
                # Handle different response types
                if isinstance(response_data, list):
                    # For array responses, use ${array[0].field} syntax
                    webhook_context["array"] = response_data
                    if verbose:
                        print(f"Array response: {len(response_data)} items")
                else:
                    # For object responses, use ${response.field} syntax
                    webhook_context["response"] = response_data
                    if verbose:
                        print("Object response")
                
                # Step 3: Process webhook-level foreach (if present)
                if "foreach" in webhook:
                    foreach_config = webhook["foreach"]
                    if verbose:
                        print(f"\n--- Processing Webhook Foreach ---")
                        print(f"Foreach config: {json.dumps(foreach_config, indent=2)}")
                    
                    input_key = foreach_config.get("input_key", "data")
                    output_key = foreach_config.get("output_key", "result")
                    max_items = foreach_config.get("max", 100)
                    append_template = foreach_config.get("append", "${this.value}")
                    
                    # Look for the input data in the response
                    input_data = None
                    if input_key in response_data and isinstance(response_data[input_key], list):
                        input_data = response_data[input_key]
                        if verbose:
                            print(f"Found array data in response.{input_key}: {len(input_data)} items")
                    
                    if input_data:
                        result_parts = []
                        items_to_process = input_data[:max_items]
                        
                        for item in items_to_process:
                            if isinstance(item, dict):
                                # For objects, make properties available as ${this.property}
                                item_context = {"this": item}
                                expanded = simple_template_expand(append_template, item_context)
                            else:
                                # For non-dict items, make them available as ${this.value}
                                item_context = {"this": {"value": item}}
                                expanded = simple_template_expand(append_template, item_context)
                            result_parts.append(expanded)
                        
                        # Store the concatenated result
                        foreach_result = "".join(result_parts)
                        webhook_context[output_key] = foreach_result
                        
                        if verbose:
                            print(f"Processed {len(items_to_process)} items")
                            print(f"Foreach result ({output_key}): {foreach_result[:200]}{'...' if len(foreach_result) > 200 else ''}")
                    else:
                        if verbose:
                            print(f"No array data found for foreach input_key: {input_key}")
                
                # Step 4: Process webhook-level output (this is the final result)
                if "output" in webhook:
                    webhook_output = webhook["output"]
                    if verbose:
                        print(f"\n--- Processing Webhook Output ---")
                        print(f"Output template: {json.dumps(webhook_output, indent=2)}")
                    
                    if isinstance(webhook_output, dict):
                        # Process each key-value pair in the output
                        final_result = {}
                        for key, template in webhook_output.items():
                            expanded_value = simple_template_expand(str(template), webhook_context)
                            final_result[key] = expanded_value
                            if verbose:
                                print(f"Set {key} = {expanded_value}")
                    else:
                        # Single output value (string template)
                        final_result = simple_template_expand(str(webhook_output), webhook_context)
                        if verbose:
                            print(f"Final result = {final_result}")
                    
                    if verbose:
                        print(f"\n--- Webhook {i+1} Final Result ---")
                        print(f"Result: {json.dumps(final_result, indent=2) if isinstance(final_result, dict) else final_result}")
                    
                    return final_result
                
                else:
                    # No output template defined, return the response data
                    if verbose:
                        print("No output template defined, returning response data")
                    return response_data
            
            else:
                # This webhook failed, try next webhook
                if verbose:
                    print(f"Webhook {i+1} failed, trying next webhook...")
                continue
    
    # Step 5: All webhooks failed, use fallback output if available
    if "output" in actual_datamap:
        if verbose:
            print(f"\n--- Using DataMap Fallback Output ---")
        datamap_output = actual_datamap["output"]
        if verbose:
            print(f"Fallback output template: {json.dumps(datamap_output, indent=2)}")
        
        if isinstance(datamap_output, dict):
            # Process each key-value pair in the fallback output
            final_result = {}
            for key, template in datamap_output.items():
                expanded_value = simple_template_expand(str(template), context)
                final_result[key] = expanded_value
                if verbose:
                    print(f"Fallback: Set {key} = {expanded_value}")
            result = final_result
        else:
            # Single fallback output value
            result = simple_template_expand(str(datamap_output), context)
            if verbose:
                print(f"Fallback result = {result}")
        
        if verbose:
            print(f"\n--- DataMap Fallback Final Result ---")
            print(f"Result: {json.dumps(result, indent=2) if isinstance(result, dict) else result}")
        
        return result
    
    # No fallback defined, return generic error
    error_result = {"error": "All webhooks failed and no fallback output defined", "status": "failed"}
    if verbose:
        print(f"\n--- DataMap Error Result ---")
        print(f"Result: {json.dumps(error_result, indent=2)}")
    
    return error_result


def execute_external_webhook_function(func: 'SWAIGFunction', function_name: str, function_args: Dict[str, Any], 
                                    post_data: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
    """
    Execute an external webhook SWAIG function by making an HTTP request to the external service.
    This simulates what SignalWire would do when calling an external webhook function.
    
    Args:
        func: The SWAIGFunction object with webhook_url
        function_name: Name of the function being called
        function_args: Parsed function arguments
        post_data: Complete post data to send to the webhook
        verbose: Whether to show verbose output
        
    Returns:
        Response from the external webhook service
    """
    webhook_url = func.webhook_url
    
    if verbose:
        print(f"\nCalling EXTERNAL webhook: {function_name}")
        print(f"URL: {webhook_url}")
        print(f"Arguments: {json.dumps(function_args, indent=2)}")
        print("-" * 60)
    
    # Prepare the SWAIG function call payload that SignalWire would send
    swaig_payload = {
        "function": function_name,
        "argument": {
            "parsed": [function_args] if function_args else [{}],
            "raw": json.dumps(function_args) if function_args else "{}"
        }
    }
    
    # Add call_id and other data from post_data if available
    if "call_id" in post_data:
        swaig_payload["call_id"] = post_data["call_id"]
    
    # Add any other relevant fields from post_data
    for key in ["call", "device", "vars"]:
        if key in post_data:
            swaig_payload[key] = post_data[key]
    
    if verbose:
        print(f"Sending payload: {json.dumps(swaig_payload, indent=2)}")
        print(f"Making POST request to: {webhook_url}")
    
    try:
        # Make the HTTP request to the external webhook
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SignalWire-SWAIG-Test/1.0"
        }
        
        response = requests.post(
            webhook_url,
            json=swaig_payload,
            headers=headers,
            timeout=30  # 30 second timeout
        )
        
        if verbose:
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if verbose:
                    print(f"✓ External webhook succeeded")
                    print(f"Response: {json.dumps(result, indent=2)}")
                return result
            except json.JSONDecodeError:
                # If response is not JSON, wrap it in a response field
                result = {"response": response.text}
                if verbose:
                    print(f"✓ External webhook succeeded (text response)")
                    print(f"Response: {response.text}")
                return result
        else:
            error_msg = f"External webhook returned HTTP {response.status_code}"
            if verbose:
                print(f"✗ External webhook failed: {error_msg}")
                try:
                    error_detail = response.json()
                    print(f"Error details: {json.dumps(error_detail, indent=2)}")
                except:
                    print(f"Error response: {response.text}")
            
            return {
                "error": error_msg,
                "status_code": response.status_code,
                "response": response.text
            }
    
    except requests.Timeout:
        error_msg = f"External webhook timed out after 30 seconds"
        if verbose:
            print(f"✗ {error_msg}")
        return {"error": error_msg}
    
    except requests.ConnectionError as e:
        error_msg = f"Could not connect to external webhook: {e}"
        if verbose:
            print(f"✗ {error_msg}")
        return {"error": error_msg}
    
    except requests.RequestException as e:
        error_msg = f"Request to external webhook failed: {e}"
        if verbose:
            print(f"✗ {error_msg}")
        return {"error": error_msg}


def display_agent_tools(agent: 'AgentBase', verbose: bool = False) -> None:
    """
    Display the available SWAIG functions for an agent
    
    Args:
        agent: The agent instance
        verbose: Whether to show verbose details
    """
    print("\nAvailable SWAIG functions:")
    if hasattr(agent, '_swaig_functions') and agent._swaig_functions:
        for name, func in agent._swaig_functions.items():
            if isinstance(func, dict):
                # DataMap function
                description = func.get('description', 'DataMap function (serverless)')
                print(f"  {name} - {description}")
                
                # Show parameters for DataMap functions
                if 'parameters' in func and func['parameters']:
                    params = func['parameters']
                    # Handle both formats: direct properties dict or full schema
                    if 'properties' in params:
                        properties = params['properties']
                        required_fields = params.get('required', [])
                    else:
                        properties = params
                        required_fields = []
                    
                    if properties:
                        print(f"    Parameters:")
                        for param_name, param_def in properties.items():
                            param_type = param_def.get('type', 'unknown')
                            param_desc = param_def.get('description', 'No description')
                            is_required = param_name in required_fields
                            required_marker = " (required)" if is_required else ""
                            print(f"      {param_name} ({param_type}){required_marker}: {param_desc}")
                    else:
                        print(f"    Parameters: None")
                else:
                    print(f"    Parameters: None")
                    
                if verbose:
                    print(f"    Config: {json.dumps(func, indent=6)}")
            else:
                # Regular SWAIG function
                func_type = ""
                if hasattr(func, 'webhook_url') and func.webhook_url and func.is_external:
                    func_type = " (EXTERNAL webhook)"
                elif hasattr(func, 'webhook_url') and func.webhook_url:
                    func_type = " (webhook)"
                else:
                    func_type = " (LOCAL webhook)"
                
                print(f"  {name} - {func.description}{func_type}")
                
                # Show external URL if applicable
                if hasattr(func, 'webhook_url') and func.webhook_url and func.is_external:
                    print(f"    External URL: {func.webhook_url}")
                
                # Show parameters
                if hasattr(func, 'parameters') and func.parameters:
                    params = func.parameters
                    # Handle both formats: direct properties dict or full schema
                    if 'properties' in params:
                        properties = params['properties']
                        required_fields = params.get('required', [])
                    else:
                        properties = params
                        required_fields = []
                    
                    if properties:
                        print(f"    Parameters:")
                        for param_name, param_def in properties.items():
                            param_type = param_def.get('type', 'unknown')
                            param_desc = param_def.get('description', 'No description')
                            is_required = param_name in required_fields
                            required_marker = " (required)" if is_required else ""
                            print(f"      {param_name} ({param_type}){required_marker}: {param_desc}")
                    else:
                        print(f"    Parameters: None")
                else:
                    print(f"    Parameters: None")
                    
                if verbose:
                    print(f"    Function object: {func}")
    else:
        print("  No SWAIG functions registered")


def discover_agents_in_file(agent_path: str) -> List[Dict[str, Any]]:
    """
    Discover all available agents in a Python file without instantiating them
    
    Args:
        agent_path: Path to the Python file containing agents
        
    Returns:
        List of dictionaries with agent information
        
    Raises:
        ImportError: If the file cannot be imported
        FileNotFoundError: If the file doesn't exist
    """
    agent_path = Path(agent_path).resolve()
    
    if not agent_path.exists():
        raise FileNotFoundError(f"Agent file not found: {agent_path}")
    
    if not agent_path.suffix == '.py':
        raise ValueError(f"Agent file must be a Python file (.py): {agent_path}")
    
    # Load the module, but prevent main() execution by setting __name__ to something other than "__main__"
    spec = importlib.util.spec_from_file_location("agent_module", agent_path)
    module = importlib.util.module_from_spec(spec)
    
    try:
        # Set __name__ to prevent if __name__ == "__main__": blocks from running
        module.__name__ = "agent_module"
        spec.loader.exec_module(module)
    except Exception as e:
        raise ImportError(f"Failed to load agent module: {e}")
    
    agents_found = []
    
    # Look for AgentBase instances
    for name, obj in vars(module).items():
        if isinstance(obj, AgentBase):
            agents_found.append({
                'name': name,
                'class_name': obj.__class__.__name__,
                'type': 'instance',
                'agent_name': getattr(obj, 'name', 'Unknown'),
                'route': getattr(obj, 'route', 'Unknown'),
                'description': obj.__class__.__doc__,
                'object': obj
            })
    
    # Look for AgentBase subclasses (that could be instantiated)
    for name, obj in vars(module).items():
        if (isinstance(obj, type) and 
            issubclass(obj, AgentBase) and 
            obj != AgentBase):
            # Check if we already found an instance of this class
            instance_found = any(agent['class_name'] == name for agent in agents_found)
            if not instance_found:
                try:
                    # Try to get class information without instantiating
                    agent_info = {
                        'name': name,
                        'class_name': name,
                        'type': 'class',
                        'agent_name': 'Unknown (not instantiated)',
                        'route': 'Unknown (not instantiated)',
                        'description': obj.__doc__,
                        'object': obj
                    }
                    agents_found.append(agent_info)
                except Exception:
                    # If we can't get info, still record that the class exists
                    agents_found.append({
                        'name': name,
                        'class_name': name,
                        'type': 'class',
                        'agent_name': 'Unknown (not instantiated)',
                        'route': 'Unknown (not instantiated)',
                        'description': obj.__doc__ or 'No description available',
                        'object': obj
                    })
    
    return agents_found


def load_agent_from_file(agent_path: str, agent_class_name: Optional[str] = None) -> 'AgentBase':
    """
    Load an agent from a Python file
    
    Args:
        agent_path: Path to the Python file containing the agent
        agent_class_name: Optional name of the agent class to instantiate
        
    Returns:
        AgentBase instance
        
    Raises:
        ImportError: If the file cannot be imported
        ValueError: If no agent is found in the file
    """
    agent_path = Path(agent_path).resolve()
    
    if not agent_path.exists():
        raise FileNotFoundError(f"Agent file not found: {agent_path}")
    
    if not agent_path.suffix == '.py':
        raise ValueError(f"Agent file must be a Python file (.py): {agent_path}")
    
    # Load the module, but prevent main() execution by setting __name__ to something other than "__main__"
    spec = importlib.util.spec_from_file_location("agent_module", agent_path)
    module = importlib.util.module_from_spec(spec)
    
    try:
        # Set __name__ to prevent if __name__ == "__main__": blocks from running
        module.__name__ = "agent_module"
        spec.loader.exec_module(module)
    except Exception as e:
        raise ImportError(f"Failed to load agent module: {e}")
    
    # Find the agent instance
    agent = None
    
    # If agent_class_name is specified, try to instantiate that specific class first
    if agent_class_name:
        if hasattr(module, agent_class_name):
            obj = getattr(module, agent_class_name)
            if isinstance(obj, type) and issubclass(obj, AgentBase) and obj != AgentBase:
                try:
                    agent = obj()
                    if agent and not agent.route.endswith('dummy'):  # Avoid test agents with dummy routes
                        pass  # Successfully created specific agent
                    else:
                        agent = obj()  # Create anyway if requested specifically
                except Exception as e:
                    raise ValueError(f"Failed to instantiate agent class '{agent_class_name}': {e}")
            else:
                raise ValueError(f"'{agent_class_name}' is not a valid AgentBase subclass")
        else:
            raise ValueError(f"Agent class '{agent_class_name}' not found in {agent_path}")
    
    # Strategy 1: Look for 'agent' variable (most common pattern)
    if agent is None and hasattr(module, 'agent') and isinstance(module.agent, AgentBase):
        agent = module.agent
    
    # Strategy 2: Look for any AgentBase instance in module globals
    if agent is None:
        agents_found = []
        for name, obj in vars(module).items():
            if isinstance(obj, AgentBase):
                agents_found.append((name, obj))
        
        if len(agents_found) == 1:
            agent = agents_found[0][1]
        elif len(agents_found) > 1:
            # Multiple agents found, prefer one named 'agent'
            for name, obj in agents_found:
                if name == 'agent':
                    agent = obj
                    break
            # If no 'agent' variable, use the first one
            if agent is None:
                agent = agents_found[0][1]
                print(f"Warning: Multiple agents found, using '{agents_found[0][0]}'")
                print(f"Hint: Use --agent-class parameter to choose specific agent")
    
    # Strategy 3: Look for AgentBase subclass and try to instantiate it
    if agent is None:
        agent_classes_found = []
        for name, obj in vars(module).items():
            if (isinstance(obj, type) and 
                issubclass(obj, AgentBase) and 
                obj != AgentBase):
                agent_classes_found.append((name, obj))
        
        if len(agent_classes_found) == 1:
            try:
                agent = agent_classes_found[0][1]()
            except Exception as e:
                print(f"Warning: Failed to instantiate {agent_classes_found[0][0]}: {e}")
        elif len(agent_classes_found) > 1:
            # Multiple agent classes found
            class_names = [name for name, _ in agent_classes_found]
            raise ValueError(f"Multiple agent classes found: {', '.join(class_names)}. "
                           f"Please specify which agent class to use with --agent-class parameter. "
                           f"Usage: swaig-test {agent_path} [tool_name] [args] --agent-class <AgentClassName>")
        else:
            # Try instantiating any AgentBase class we can find
            for name, obj in vars(module).items():
                if (isinstance(obj, type) and 
                    issubclass(obj, AgentBase) and 
                    obj != AgentBase):
                    try:
                        agent = obj()
                        break
                    except Exception as e:
                        print(f"Warning: Failed to instantiate {name}: {e}")
    
    # Strategy 4: Try calling a modified main() function that doesn't start the server
    if agent is None and hasattr(module, 'main'):
        print("Warning: No agent instance found, attempting to call main() without server startup")
        try:
            # Temporarily patch AgentBase.serve to prevent server startup
            original_serve = AgentBase.serve
            captured_agent = []
            
            def mock_serve(self, *args, **kwargs):
                captured_agent.append(self)
                print(f"  (Intercepted serve() call, agent captured for testing)")
                return self
            
            AgentBase.serve = mock_serve
            
            try:
                result = module.main()
                if isinstance(result, AgentBase):
                    agent = result
                elif captured_agent:
                    agent = captured_agent[0]
            finally:
                # Restore original serve method
                AgentBase.serve = original_serve
                
        except Exception as e:
            print(f"Warning: Failed to call main() function: {e}")
    
    if agent is None:
        raise ValueError(f"No AgentBase instance found in {agent_path}. "
                        f"Make sure the file contains an agent variable or AgentBase subclass.")
    
    return agent


def format_result(result: Any) -> str:
    """
    Format the result of a SWAIG function call for display
    
    Args:
        result: The result from the SWAIG function
        
    Returns:
        Formatted string representation
    """
    if isinstance(result, SwaigFunctionResult):
        return f"SwaigFunctionResult: {result.response}"
    elif isinstance(result, dict):
        if 'response' in result:
            return f"Response: {result['response']}"
        else:
            return f"Dict: {json.dumps(result, indent=2)}"
    elif isinstance(result, str):
        return f"String: {result}"
    else:
        return f"Other ({type(result).__name__}): {result}"


def parse_function_arguments(function_args_list: List[str], func_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse function arguments from command line with type coercion based on schema
    
    Args:
        function_args_list: List of command line arguments after --args
        func_schema: Function schema with parameter definitions
        
    Returns:
        Dictionary of parsed function arguments
    """
    parsed_args = {}
    i = 0
    
    # Get parameter schema
    parameters = {}
    required_params = []
    
    if isinstance(func_schema, dict):
        # DataMap function
        if 'parameters' in func_schema:
            params = func_schema['parameters']
            if 'properties' in params:
                parameters = params['properties']
                required_params = params.get('required', [])
            else:
                parameters = params
        else:
            parameters = func_schema
    else:
        # Regular SWAIG function
        if hasattr(func_schema, 'parameters') and func_schema.parameters:
            params = func_schema.parameters
            if 'properties' in params:
                parameters = params['properties']
                required_params = params.get('required', [])
            else:
                parameters = params
    
    # Parse arguments
    while i < len(function_args_list):
        arg = function_args_list[i]
        
        if arg.startswith('--'):
            param_name = arg[2:]  # Remove --
            
            # Convert kebab-case to snake_case for parameter lookup
            param_key = param_name.replace('-', '_')
            
            # Check if this parameter exists in schema
            param_schema = parameters.get(param_key, {})
            param_type = param_schema.get('type', 'string')
            
            if param_type == 'boolean':
                # Check if next arg is a boolean value or if this is a flag
                if i + 1 < len(function_args_list) and function_args_list[i + 1].lower() in ['true', 'false']:
                    parsed_args[param_key] = function_args_list[i + 1].lower() == 'true'
                    i += 2
                else:
                    # Treat as flag (present = true)
                    parsed_args[param_key] = True
                    i += 1
            else:
                # Need a value
                if i + 1 >= len(function_args_list):
                    raise ValueError(f"Parameter --{param_name} requires a value")
                
                value = function_args_list[i + 1]
                
                # Type coercion
                if param_type == 'integer':
                    try:
                        parsed_args[param_key] = int(value)
                    except ValueError:
                        raise ValueError(f"Parameter --{param_name} must be an integer, got: {value}")
                elif param_type == 'number':
                    try:
                        parsed_args[param_key] = float(value)
                    except ValueError:
                        raise ValueError(f"Parameter --{param_name} must be a number, got: {value}")
                elif param_type == 'array':
                    # Handle comma-separated arrays
                    parsed_args[param_key] = [item.strip() for item in value.split(',')]
                else:
                    # String (default)
                    parsed_args[param_key] = value
                
                i += 2
        else:
            raise ValueError(f"Expected parameter name starting with --, got: {arg}")
    
    return parsed_args


def main():
    """Main entry point for the CLI tool"""
    # Check for --raw flag and set up suppression early
    if "--raw" in sys.argv:
        setup_raw_mode_suppression()
    
    # Check for --exec and split arguments  
    cli_args = sys.argv[1:]
    function_args_list = []
    exec_function_name = None
    
    if '--exec' in sys.argv:
        exec_index = sys.argv.index('--exec')
        if exec_index + 1 < len(sys.argv):
            exec_function_name = sys.argv[exec_index + 1]
            # CLI args: everything before --exec
            cli_args = sys.argv[1:exec_index]
            # Function args: everything after the function name
            function_args_list = sys.argv[exec_index + 2:]
        else:
            print("Error: --exec requires a function name")
            return 1
    
    # Temporarily modify sys.argv for argparse (exclude --exec and its args)
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]] + cli_args
    
    # Custom ArgumentParser class with better error handling
    class CustomArgumentParser(argparse.ArgumentParser):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._suppress_usage = False
        
        def _print_message(self, message, file=None):
            """Override to suppress usage output for specific errors"""
            if self._suppress_usage:
                return
            super()._print_message(message, file)
        
        def error(self, message):
            """Override error method to provide user-friendly error messages"""
            if "required" in message.lower() and "agent_path" in message:
                self._suppress_usage = True
                print("Error: Missing required argument.")
                print()
                print(f"Usage: {self.prog} <agent_path> [options]")
                print()
                print("Examples:")
                print(f"  {self.prog} examples/my_agent.py --list-tools")
                print(f"  {self.prog} examples/my_agent.py --dump-swml")
                print(f"  {self.prog} examples/my_agent.py --exec my_function --param value")
                print()
                print(f"For full help: {self.prog} --help")
                sys.exit(2)
            else:
                # For other errors, use the default behavior
                super().error(message)
        
        def print_usage(self, file=None):
            """Override print_usage to suppress output when we want custom error handling"""
            if self._suppress_usage:
                return
            super().print_usage(file)
        
        def parse_args(self, args=None, namespace=None):
            """Override parse_args to provide custom error handling for missing arguments"""
            # Check if no arguments provided (just the program name)
            import sys
            if args is None:
                args = sys.argv[1:]
            
            # If no arguments provided, show custom error
            if not args:
                print("Error: Missing required argument.")
                print()
                print(f"Usage: {self.prog} <agent_path> [options]")
                print()
                print("Examples:")
                print(f"  {self.prog} examples/my_agent.py --list-tools")
                print(f"  {self.prog} examples/my_agent.py --dump-swml")
                print(f"  {self.prog} examples/my_agent.py --exec my_function --param value")
                print()
                print(f"For full help: {self.prog} --help")
                sys.exit(2)
            
            # Otherwise, use default parsing
            return super().parse_args(args, namespace)
    
    parser = CustomArgumentParser(
        description="Test SWAIG functions from agent applications with comprehensive simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage="%(prog)s <agent_path> [options]",
        epilog="""
Examples:
  # Function testing with --exec syntax  
  %(prog)s examples/agent.py --verbose --exec search --query "AI" --limit 5
  %(prog)s examples/web_search_agent.py --exec web_search --query "test"
  
  # Legacy JSON syntax (still supported)
  %(prog)s examples/web_search_agent.py web_search '{"query":"test"}'
  
  # Multiple agents - auto-select when only one, or specify with --agent-class  
  %(prog)s matti_and_sigmond/dual_agent_app.py --agent-class MattiAgent --exec transfer --name sigmond
  %(prog)s matti_and_sigmond/dual_agent_app.py --verbose --agent-class SigmondAgent --exec get_weather --location "New York"
  
  # SWML testing (enhanced with fake post_data)
  %(prog)s examples/my_agent.py --dump-swml
  %(prog)s examples/my_agent.py --dump-swml --raw | jq '.'
  %(prog)s examples/my_agent.py --dump-swml --verbose
  
  # SWML testing with specific agent class
  %(prog)s matti_and_sigmond/dual_agent_app.py --dump-swml --agent-class MattiAgent
  
  # SWML testing with call customization
  %(prog)s examples/agent.py --dump-swml --call-type sip --call-direction outbound
  %(prog)s examples/agent.py --dump-swml --call-state answered --from-number +15551234567
  
  # SWML testing with data overrides
  %(prog)s examples/agent.py --dump-swml --override call.project_id=my-project
  %(prog)s examples/agent.py --dump-swml --user-vars '{"customer_id":"12345","tier":"gold"}'
  %(prog)s examples/agent.py --dump-swml --override call.timeout=60 --override call.state=answered
  
  # Dynamic agent testing with mock request
  %(prog)s examples/dynamic_agent.py --dump-swml --header "Authorization=Bearer token"
  %(prog)s examples/dynamic_agent.py --dump-swml --query-params '{"source":"api","debug":"true"}'
  %(prog)s examples/dynamic_agent.py --dump-swml --method GET --body '{"custom":"data"}'
  
  # Serverless environment simulation
  %(prog)s examples/my_agent.py --simulate-serverless lambda --dump-swml
  %(prog)s examples/my_agent.py --simulate-serverless lambda --exec my_function --param value
  %(prog)s examples/my_agent.py --simulate-serverless cgi --cgi-host example.com --dump-swml
  %(prog)s examples/my_agent.py --simulate-serverless cloud_function --gcp-project my-project --exec my_function
  
  # Serverless with environment variables
  %(prog)s examples/my_agent.py --simulate-serverless lambda --env API_KEY=secret --env DEBUG=1 --exec my_function
  %(prog)s examples/my_agent.py --simulate-serverless lambda --env-file production.env --exec my_function
  
  # Platform-specific serverless configuration
  %(prog)s examples/my_agent.py --simulate-serverless lambda --aws-function-name prod-function --aws-region us-west-2 --dump-swml
  %(prog)s examples/my_agent.py --simulate-serverless cgi --cgi-host production.com --cgi-https --exec my_function
  
  # Combined testing scenarios
  %(prog)s examples/agent.py --dump-swml --call-type sip --user-vars '{"vip":"true"}' --header "X-Source=test" --verbose
  %(prog)s examples/agent.py --simulate-serverless lambda --dump-swml --call-type sip --verbose
  
  # Discovery commands
  %(prog)s examples/my_agent.py --list-agents
  %(prog)s examples/my_agent.py --list-tools
  %(prog)s matti_and_sigmond/dual_agent_app.py --list-agents
  %(prog)s matti_and_sigmond/dual_agent_app.py --agent-class MattiAgent --list-tools
  
  # Auto-discovery (lists agents when no other args provided)
  %(prog)s matti_and_sigmond/dual_agent_app.py
        """
    )
    
    # Required positional arguments
    parser.add_argument(
        "agent_path",
        help="Path to the Python file containing the agent"
    )
    
    parser.add_argument(
        "tool_name", 
        nargs="?",
        help="Name of the SWAIG function/tool to call (optional, can use --exec instead)"
    )
    
    parser.add_argument(
        "args_json",
        nargs="?",
        help="JSON string containing the arguments to pass to the function (when using positional tool_name)"
    )
    
    # Function Execution Options
    func_group = parser.add_argument_group('Function Execution Options')
    func_group.add_argument(
        "--exec",
        metavar="FUNCTION",
        help="Execute a function with CLI-style arguments (replaces tool_name and --args)"
    )
    
    func_group.add_argument(
        "--custom-data",
        help="Optional JSON string containing custom post_data overrides",
        default="{}"
    )
    
    # Agent Discovery and Selection
    agent_group = parser.add_argument_group('Agent Discovery and Selection')
    agent_group.add_argument(
        "--agent-class",
        help="Name of the agent class to use (required only if multiple agents in file)"
    )
    
    agent_group.add_argument(
        "--list-agents",
        action="store_true",
        help="List all available agents in the file and exit"
    )
    
    agent_group.add_argument(
        "--list-tools",
        action="store_true",
        help="List all available tools in the agent and exit"
    )
    
    # Output and Debugging Options
    output_group = parser.add_argument_group('Output and Debugging Options')
    output_group.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    output_group.add_argument(
        "--raw",
        action="store_true",
        help="Output raw SWML JSON only (no headers, useful for piping to jq/yq)"
    )
    
    # SWML Generation and Testing
    swml_group = parser.add_argument_group('SWML Generation and Testing')
    swml_group.add_argument(
        "--dump-swml",
        action="store_true",
        help="Dump the SWML document from the agent and exit"
    )
    
    swml_group.add_argument(
        "--fake-full-data",
        action="store_true", 
        help="Generate comprehensive fake post_data with all possible keys"
    )
    
    swml_group.add_argument(
        "--minimal",
        action="store_true",
        help="Use minimal post_data (only essential keys)"
    )
    
    # Call Configuration Options
    call_group = parser.add_argument_group('Call Configuration Options')
    call_group.add_argument(
        "--call-type",
        choices=["sip", "webrtc"],
        default="webrtc",
        help="Type of call for SWML generation (default: webrtc)"
    )
    
    call_group.add_argument(
        "--call-direction",
        choices=["inbound", "outbound"],
        default="inbound",
        help="Direction of call for SWML generation (default: inbound)"
    )
    
    call_group.add_argument(
        "--call-state",
        default="created",
        help="State of call for SWML generation (default: created)"
    )
    
    call_group.add_argument(
        "--call-id",
        help="Override call_id in fake SWML post_data"
    )
    
    call_group.add_argument(
        "--from-number",
        help="Override 'from' address in fake SWML post_data"
    )
    
    call_group.add_argument(
        "--to-extension",
        help="Override 'to' address in fake SWML post_data"
    )
    
    # SignalWire Platform Configuration
    platform_group = parser.add_argument_group('SignalWire Platform Configuration')
    platform_group.add_argument(
        "--project-id",
        help="Override project_id in fake SWML post_data"
    )
    
    platform_group.add_argument(
        "--space-id", 
        help="Override space_id in fake SWML post_data"
    )
    
    # User Variables and Query Parameters
    vars_group = parser.add_argument_group('User Variables and Query Parameters')
    vars_group.add_argument(
        "--user-vars",
        help="JSON string for vars.userVariables in fake SWML post_data"
    )
    
    vars_group.add_argument(
        "--query-params",
        help="JSON string for query parameters (merged into userVariables)"
    )
    
    # Data Override Options
    override_group = parser.add_argument_group('Data Override Options')
    override_group.add_argument(
        "--override",
        action="append",
        default=[],
        help="Override specific values using dot notation (e.g., --override call.state=answered)"
    )
    
    override_group.add_argument(
        "--override-json",
        action="append", 
        default=[],
        help="Override with JSON values using dot notation (e.g., --override-json vars.custom='{\"key\":\"value\"}')"
    )
    
    # HTTP Request Simulation
    http_group = parser.add_argument_group('HTTP Request Simulation')
    http_group.add_argument(
        "--header",
        action="append",
        default=[],
        help="Add HTTP headers for mock request (e.g., --header Authorization=Bearer token)"
    )
    
    http_group.add_argument(
        "--method",
        default="POST",
        help="HTTP method for mock request (default: POST)"
    )
    
    http_group.add_argument(
        "--body",
        help="JSON string for mock request body"
    )
    
    # Serverless Environment Simulation
    serverless_group = parser.add_argument_group('Serverless Environment Simulation')
    serverless_group.add_argument(
        "--simulate-serverless",
        choices=["lambda", "cgi", "cloud_function", "azure_function"],
        help="Simulate serverless platform environment (lambda, cgi, cloud_function, azure_function)"
    )
    
    serverless_group.add_argument(
        "--env",
        action="append",
        default=[],
        help="Set environment variable (e.g., --env API_KEY=secret123)"
    )
    
    serverless_group.add_argument(
        "--env-file",
        help="Load environment variables from file"
    )
    
    serverless_group.add_argument(
        "--serverless-mode",
        help="Legacy option for serverless mode (use --simulate-serverless instead)"
    )
    
    # AWS Lambda Configuration
    aws_group = parser.add_argument_group('AWS Lambda Configuration')
    aws_group.add_argument(
        "--aws-function-name",
        help="AWS Lambda function name (overrides default)"
    )
    
    aws_group.add_argument(
        "--aws-function-url",
        help="AWS Lambda function URL (overrides default)"
    )
    
    aws_group.add_argument(
        "--aws-region",
        help="AWS region (overrides default)"
    )
    
    aws_group.add_argument(
        "--aws-api-gateway-id",
        help="AWS API Gateway ID for API Gateway URLs"
    )
    
    aws_group.add_argument(
        "--aws-stage",
        help="AWS API Gateway stage (default: prod)"
    )
    
    # CGI Configuration
    cgi_group = parser.add_argument_group('CGI Configuration')
    cgi_group.add_argument(
        "--cgi-host",
        help="CGI server hostname (required for CGI simulation)"
    )
    
    cgi_group.add_argument(
        "--cgi-script-name",
        help="CGI script name/path (overrides default)"
    )
    
    cgi_group.add_argument(
        "--cgi-https",
        action="store_true",
        help="Use HTTPS for CGI URLs"
    )
    
    cgi_group.add_argument(
        "--cgi-path-info",
        help="CGI PATH_INFO value"
    )
    
    # Google Cloud Platform Configuration
    gcp_group = parser.add_argument_group('Google Cloud Platform Configuration')
    gcp_group.add_argument(
        "--gcp-project",
        help="Google Cloud project ID (overrides default)"
    )
    
    gcp_group.add_argument(
        "--gcp-function-url",
        help="Google Cloud Function URL (overrides default)"
    )
    
    gcp_group.add_argument(
        "--gcp-region",
        help="Google Cloud region (overrides default)"
    )
    
    gcp_group.add_argument(
        "--gcp-service",
        help="Google Cloud service name (overrides default)"
    )
    
    # Azure Functions Configuration
    azure_group = parser.add_argument_group('Azure Functions Configuration')
    azure_group.add_argument(
        "--azure-env",
        help="Azure Functions environment (overrides default)"
    )
    
    azure_group.add_argument(
        "--azure-function-url",
        help="Azure Function URL (overrides default)"
    )
    
    args = parser.parse_args()
    
    # Restore original sys.argv
    sys.argv = original_argv
    
    # Handle --exec vs positional tool_name
    if exec_function_name:
        # Using --exec syntax, override any positional tool_name
        args.tool_name = exec_function_name
        # function_args_list is already set from --exec parsing
    
    # Validate arguments
    if not args.list_tools and not args.dump_swml and not args.list_agents:
        if not args.tool_name:
            # If no tool_name and no special flags, default to listing agents
            args.list_agents = True
        else:
            # When using positional syntax, args_json is required
            # When using --exec syntax, function_args_list is automatically populated
            if not args.args_json and not function_args_list:
                if exec_function_name:
                    # --exec syntax doesn't require additional arguments (can be empty)
                    pass
                else:
                    parser.error("Positional tool_name requires args_json parameter. Use --exec for CLI-style arguments.")
    
    # ===== SERVERLESS SIMULATION SETUP =====
    serverless_simulator = None
    
    # Handle legacy --serverless-mode option
    if args.serverless_mode and not args.simulate_serverless:
        args.simulate_serverless = args.serverless_mode
        if not args.raw:
            print("Warning: --serverless-mode is deprecated, use --simulate-serverless instead")
    
    if args.simulate_serverless:
        # Validate CGI requirements
        if args.simulate_serverless == 'cgi' and not args.cgi_host:
            parser.error("CGI simulation requires --cgi-host")
        
        # Collect environment variable overrides
        env_overrides = {}
        
        # Load from environment file first
        if args.env_file:
            try:
                file_env = load_env_file(args.env_file)
                env_overrides.update(file_env)
                if args.verbose and not args.raw:
                    print(f"Loaded {len(file_env)} environment variables from {args.env_file}")
            except FileNotFoundError as e:
                print(f"Error: {e}")
                return 1
        
        # Parse --env arguments
        for env_arg in args.env:
            if '=' not in env_arg:
                print(f"Error: Invalid environment variable format: {env_arg}")
                print("Expected format: --env KEY=value")
                return 1
            key, value = env_arg.split('=', 1)
            env_overrides[key] = value
        
        # Add platform-specific overrides
        if args.simulate_serverless == 'lambda':
            if args.aws_function_name:
                env_overrides['AWS_LAMBDA_FUNCTION_NAME'] = args.aws_function_name
            if args.aws_function_url:
                env_overrides['AWS_LAMBDA_FUNCTION_URL'] = args.aws_function_url
            if args.aws_region:
                env_overrides['AWS_REGION'] = args.aws_region
            if args.aws_api_gateway_id:
                env_overrides['AWS_API_GATEWAY_ID'] = args.aws_api_gateway_id
            if args.aws_stage:
                env_overrides['AWS_API_GATEWAY_STAGE'] = args.aws_stage
        
        elif args.simulate_serverless == 'cgi':
            if args.cgi_host:
                env_overrides['HTTP_HOST'] = args.cgi_host
            if args.cgi_script_name:
                env_overrides['SCRIPT_NAME'] = args.cgi_script_name
            if args.cgi_https:
                env_overrides['HTTPS'] = 'on'
            if args.cgi_path_info:
                env_overrides['PATH_INFO'] = args.cgi_path_info
        
        elif args.simulate_serverless == 'cloud_function':
            if args.gcp_project:
                env_overrides['GOOGLE_CLOUD_PROJECT'] = args.gcp_project
            if args.gcp_function_url:
                env_overrides['FUNCTION_URL'] = args.gcp_function_url
            if args.gcp_region:
                env_overrides['GOOGLE_CLOUD_REGION'] = args.gcp_region
            if args.gcp_service:
                env_overrides['K_SERVICE'] = args.gcp_service
        
        elif args.simulate_serverless == 'azure_function':
            if args.azure_env:
                env_overrides['AZURE_FUNCTIONS_ENVIRONMENT'] = args.azure_env
            if args.azure_function_url:
                env_overrides['AZURE_FUNCTION_URL'] = args.azure_function_url
        
        # Create and activate serverless simulator
        serverless_simulator = ServerlessSimulator(args.simulate_serverless, env_overrides)
        try:
            serverless_simulator.activate(args.verbose and not args.raw)
        except Exception as e:
            print(f"Error setting up serverless simulation: {e}")
            return 1
    
    try:
        # Handle agent listing first (doesn't require loading a specific agent)
        if args.list_agents:
            if args.verbose and not args.raw:
                print(f"Discovering agents in: {args.agent_path}")
            
            try:
                agents = discover_agents_in_file(args.agent_path)
                
                if not agents:
                    print("No agents found in the file.")
                    return 1
                
                print(f"Available agents in {args.agent_path}:")
                print()
                
                for agent_info in agents:
                    print(f"  {agent_info['class_name']}")
                    
                    if agent_info['type'] == 'instance':
                        print(f"    Type: Ready instance")
                        print(f"    Name: {agent_info['agent_name']}")
                        print(f"    Route: {agent_info['route']}")
                    else:
                        print(f"    Type: Available class (needs instantiation)")
                    
                    if agent_info['description']:
                        # Clean up the description
                        desc = agent_info['description'].strip()
                        if desc:
                            # Take first line or sentence
                            first_line = desc.split('\n')[0].strip()
                            print(f"    Description: {first_line}")
                    
                    print()
                
                # Show tools if there's only one agent or if --agent-class is specified
                show_tools = False
                selected_agent = None
                
                if len(agents) == 1:
                    # Single agent - show tools automatically
                    show_tools = True
                    selected_agent = agents[0]['object']
                    print("This file contains a single agent, no --agent-class needed.")
                elif args.agent_class:
                    # Specific agent class requested - show tools for that agent
                    for agent_info in agents:
                        if agent_info['class_name'] == args.agent_class:
                            show_tools = True
                            selected_agent = agent_info['object']
                            break
                    
                    if not selected_agent:
                        print(f"Error: Agent class '{args.agent_class}' not found.")
                        print(f"Available agents: {[a['class_name'] for a in agents]}")
                        return 1
                else:
                    # Multiple agents, no specific class - show usage examples
                    print("To use a specific agent with this tool:")
                    print(f"  swaig-test {args.agent_path} [tool_name] [args] --agent-class <AgentClassName>")
                    print()
                    print("Examples:")
                    for agent_info in agents:
                        print(f"  swaig-test {args.agent_path} --list-tools --agent-class {agent_info['class_name']}")
                        print(f"  swaig-test {args.agent_path} --dump-swml --agent-class {agent_info['class_name']}")
                    print()
                
                # Show tools if we have a selected agent
                if show_tools and selected_agent:
                    try:
                        # If it's a class, try to instantiate it
                        if not isinstance(selected_agent, AgentBase):
                            if isinstance(selected_agent, type) and issubclass(selected_agent, AgentBase):
                                selected_agent = selected_agent()
                            else:
                                print(f"Warning: Cannot instantiate agent to show tools")
                                return 0
                        
                        display_agent_tools(selected_agent, args.verbose)
                    except Exception as e:
                        print(f"Warning: Could not load agent tools: {e}")
                        if args.verbose:
                            import traceback
                            traceback.print_exc()
                
                return 0
                
            except Exception as e:
                print(f"Error discovering agents: {e}")
                if args.verbose:
                    import traceback
                    traceback.print_exc()
                return 1
        
        # Load the agent for other operations
        if args.verbose and not args.raw:
            print(f"Loading agent from: {args.agent_path}")
        
        # Auto-select agent if only one exists and no --agent-class specified
        agent_class_name = getattr(args, 'agent_class', None)
        if not agent_class_name:
            # Try to auto-discover if there's only one agent
            try:
                discovered_agents = discover_agents_in_file(args.agent_path)
                if len(discovered_agents) == 1:
                    agent_class_name = discovered_agents[0]['class_name']
                    if args.verbose and not args.raw:
                        print(f"Auto-selected agent: {agent_class_name}")
                elif len(discovered_agents) > 1:
                    if not args.raw:
                        print(f"Multiple agents found: {[a['class_name'] for a in discovered_agents]}")
                        print(f"Please specify --agent-class parameter")
                    return 1
            except Exception:
                # If discovery fails, fall back to normal loading behavior
                pass
        
        agent = load_agent_from_file(args.agent_path, agent_class_name)
        
        if args.verbose and not args.raw:
            print(f"Loaded agent: {agent.get_name()}")
            print(f"Agent route: {agent.route}")
            
            # Show loaded skills
            skills = agent.list_skills()
            if skills:
                print(f"Loaded skills: {', '.join(skills)}")
            else:
                print("No skills loaded")
        
        # List tools if requested
        if args.list_tools:
            display_agent_tools(agent, args.verbose)
            return 0
        
        # Dump SWML if requested
        if args.dump_swml:
            return handle_dump_swml(agent, args)
        
        # Parse function arguments
        if function_args_list:
            # Using --exec syntax, need to get the function to parse arguments with schema
            if not hasattr(agent, '_swaig_functions') or args.tool_name not in agent._swaig_functions:
                print(f"Error: Function '{args.tool_name}' not found in agent")
                print(f"Available functions: {list(agent._swaig_functions.keys()) if hasattr(agent, '_swaig_functions') else 'None'}")
                return 1
            
            func = agent._swaig_functions[args.tool_name]
            
            try:
                function_args = parse_function_arguments(function_args_list, func)
                if args.verbose and not args.raw:
                    print(f"Parsed arguments: {json.dumps(function_args, indent=2)}")
            except ValueError as e:
                print(f"Error: {e}")
                return 1
        elif args.args_json:
            # Using legacy JSON syntax
            try:
                function_args = json.loads(args.args_json)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in args: {e}")
                return 1
        else:
            # No arguments provided
            function_args = {}
        
        try:
            custom_data = json.loads(args.custom_data)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in custom-data: {e}")
            return 1
        
        # Check if the function exists (if not already checked)
        if not function_args_list:
            if not hasattr(agent, '_swaig_functions') or args.tool_name not in agent._swaig_functions:
                print(f"Error: Function '{args.tool_name}' not found in agent")
                print(f"Available functions: {list(agent._swaig_functions.keys()) if hasattr(agent, '_swaig_functions') else 'None'}")
                return 1
            
            func = agent._swaig_functions[args.tool_name]
        else:
            # Function already retrieved during argument parsing
            func = agent._swaig_functions[args.tool_name]
        
        # Determine function type automatically - no --datamap flag needed
        # DataMap functions are stored as dicts with 'data_map' key, webhook functions as SWAIGFunction objects
        is_datamap = isinstance(func, dict) and 'data_map' in func
        
        if is_datamap:
            # DataMap function execution
            if args.verbose:
                print(f"\nExecuting DataMap function: {args.tool_name}")
                print(f"Arguments: {json.dumps(function_args, indent=2)}")
                print("-" * 60)
            
            try:
                result = execute_datamap_function(func, function_args, args.verbose)
                
                print("RESULT:")
                print(format_result(result))
                
                if args.verbose:
                    print(f"\nRaw result type: {type(result).__name__}")
                    print(f"Raw result: {repr(result)}")
                
            except Exception as e:
                print(f"Error executing DataMap function: {e}")
                if args.verbose:
                    import traceback
                    traceback.print_exc()
                return 1
        
        else:
            # Webhook function execution
            if args.verbose:
                print(f"\nCalling webhook function: {args.tool_name}")
                print(f"Arguments: {json.dumps(function_args, indent=2)}")
                print(f"Function description: {func.description}")
            
            # Check if this is an external webhook function
            is_external_webhook = hasattr(func, 'webhook_url') and func.webhook_url and func.is_external
            
            if args.verbose and is_external_webhook:
                print(f"Function type: EXTERNAL webhook")
                print(f"External URL: {func.webhook_url}")
            elif args.verbose:
                print(f"Function type: LOCAL webhook")
            
            # Generate post_data based on options
            if args.minimal:
                post_data = generate_minimal_post_data(args.tool_name, function_args)
                if custom_data:
                    post_data.update(custom_data)
            elif args.fake_full_data or custom_data:
                post_data = generate_comprehensive_post_data(args.tool_name, function_args, custom_data)
            else:
                # Default behavior - minimal data
                post_data = generate_minimal_post_data(args.tool_name, function_args)
            
            if args.verbose:
                print(f"Post data: {json.dumps(post_data, indent=2)}")
                print("-" * 60)
            
            # Call the function
            try:
                if is_external_webhook:
                    # For external webhook functions, make HTTP request to external service
                    result = execute_external_webhook_function(func, args.tool_name, function_args, post_data, args.verbose)
                else:
                    # For local webhook functions, call the agent's handler
                    result = agent.on_function_call(args.tool_name, function_args, post_data)
                
                print("RESULT:")
                print(format_result(result))
                
                if args.verbose:
                    print(f"\nRaw result type: {type(result).__name__}")
                    print(f"Raw result: {repr(result)}")
                
            except Exception as e:
                print(f"Error calling function: {e}")
                if args.verbose:
                    import traceback
                    traceback.print_exc()
                return 1
            
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    finally:
        # Clean up serverless simulation
        if serverless_simulator:
            serverless_simulator.deactivate(args.verbose and not args.raw)
    
    return 0


def console_entry_point():
    """Console script entry point for pip installation"""
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main()) 
