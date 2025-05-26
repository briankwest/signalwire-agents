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

import sys
import os
import json
import importlib.util
import argparse
import uuid
import time
import hashlib
import re
import requests
import warnings
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

# Early warning suppression for module execution warnings
if "--raw" in sys.argv:
    warnings.filterwarnings("ignore")

# Store original print function before any potential suppression
original_print = print

# Add the parent directory to the path so we can import signalwire_agents
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult


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
    
    Args:
        method: HTTP method (default: POST)
        url: Request URL (default: http://localhost:8080/swml)
        headers: HTTP headers dict
        query_params: Query parameters dict
        body: JSON body dict
        
    Returns:
        MockRequest object compatible with agent callbacks
    """
    return MockRequest(
        method=method,
        url=url,
        headers=headers,
        query_params=query_params,
        json_body=body
    )


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
        print("\nGenerating SWML document...")
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
            # Normal output with headers
            print("SWML Document:")
            print("=" * 50)
            print(swml_doc)
            print("=" * 50)
            
            if args.verbose:
                # Parse and show formatted JSON for better readability
                try:
                    swml_parsed = json.loads(swml_doc)
                    print("\nFormatted SWML:")
                    print(json.dumps(swml_parsed, indent=2))
                except json.JSONDecodeError:
                    print("\nNote: SWML document is not valid JSON format")
        
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
    """Set up comprehensive output suppression for raw mode"""
    # Suppress all warnings including RuntimeWarnings
    warnings.filterwarnings("ignore")
    
    # More aggressive logging suppression for raw mode
    logging.getLogger().setLevel(logging.CRITICAL + 1)  # Suppress everything
    logging.getLogger().addHandler(logging.NullHandler())
    
    # Monkey-patch specific loggers to completely silence them
    def silent_log(*args, **kwargs):
        pass
    
    # Capture and suppress print statements in raw mode
    def suppressed_print(*args, **kwargs):
        pass
    
    # Replace print function globally
    import builtins
    builtins.print = suppressed_print
    
    # Also suppress specific loggers
    loggers_to_suppress = [
        "skill_registry",
        "simple_agent", 
        "swml_service",
        "agent_base",
        "signalwire_agents"
    ]
    
    for logger_name in loggers_to_suppress:
        # Suppress standard Python logger
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.CRITICAL + 1)
        logger.addHandler(logging.NullHandler())
        # Monkey-patch all logging methods
        logger.debug = silent_log
        logger.info = silent_log
        logger.warning = silent_log
        logger.error = silent_log
        logger.critical = silent_log


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


def load_agent_from_file(agent_path: str) -> 'AgentBase':
    """
    Load an agent from a Python file
    
    Args:
        agent_path: Path to the Python file containing the agent
        
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
    
    # Strategy 1: Look for 'agent' variable (most common pattern)
    if hasattr(module, 'agent') and isinstance(module.agent, AgentBase):
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
    
    # Strategy 3: Look for AgentBase subclass and try to instantiate it
    if agent is None:
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
    
    # Check for --args separator and split arguments
    cli_args = sys.argv[1:]
    function_args_list = []
    
    if '--args' in sys.argv:
        args_index = sys.argv.index('--args')
        cli_args = sys.argv[1:args_index]
        function_args_list = sys.argv[args_index + 1:]
    
    # Temporarily modify sys.argv for argparse
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]] + cli_args
    
    parser = argparse.ArgumentParser(
        description="Test SWAIG functions from agent applications with comprehensive simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Function testing (existing functionality)
  %(prog)s examples/web_search_agent.py web_search '{"query":"test"}'
  %(prog)s examples/agent.py search --args --query "AI" --limit 5 --verbose
  
  # SWML testing (enhanced with fake post_data)
  %(prog)s examples/my_agent.py --dump-swml
  %(prog)s examples/my_agent.py --dump-swml --raw | jq '.'
  %(prog)s examples/my_agent.py --dump-swml --verbose
  
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
  
  # Combined testing scenarios
  %(prog)s examples/agent.py --dump-swml --call-type sip --user-vars '{"vip":"true"}' --header "X-Source=test" --verbose
  
  # Other commands
  %(prog)s examples/my_agent.py --list-tools
        """
    )
    
    parser.add_argument(
        "agent_path",
        help="Path to the Python file containing the agent"
    )
    
    parser.add_argument(
        "tool_name", 
        nargs="?",
        help="Name of the SWAIG function/tool to call"
    )
    
    parser.add_argument(
        "args_json",
        nargs="?",
        help="JSON string containing the arguments to pass to the function (or use --args for CLI syntax)"
    )
    
    parser.add_argument(
        "--custom-data",
        help="Optional JSON string containing custom post_data overrides",
        default="{}"
    )
    
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List all available tools in the agent and exit"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--fake-full-data",
        action="store_true", 
        help="Generate comprehensive fake post_data with all possible keys"
    )
    
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="Use minimal post_data (only essential keys)"
    )
    
    parser.add_argument(
        "--dump-swml",
        action="store_true",
        help="Dump the SWML document from the agent and exit"
    )
    
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Output raw SWML JSON only (no headers, useful for piping to jq/yq)"
    )
    
    # ===== NEW SWML TESTING ARGUMENTS =====
    
    parser.add_argument(
        "--call-type",
        choices=["sip", "webrtc"],
        default="webrtc",
        help="Type of call for SWML generation (default: webrtc)"
    )
    
    parser.add_argument(
        "--call-direction",
        choices=["inbound", "outbound"],
        default="inbound",
        help="Direction of call for SWML generation (default: inbound)"
    )
    
    parser.add_argument(
        "--call-state",
        default="created",
        help="State of call for SWML generation (default: created)"
    )
    
    parser.add_argument(
        "--call-id",
        help="Override call_id in fake SWML post_data"
    )
    
    parser.add_argument(
        "--project-id",
        help="Override project_id in fake SWML post_data"
    )
    
    parser.add_argument(
        "--space-id", 
        help="Override space_id in fake SWML post_data"
    )
    
    parser.add_argument(
        "--from-number",
        help="Override 'from' address in fake SWML post_data"
    )
    
    parser.add_argument(
        "--to-extension",
        help="Override 'to' address in fake SWML post_data"
    )
    
    parser.add_argument(
        "--user-vars",
        help="JSON string for vars.userVariables in fake SWML post_data"
    )
    
    parser.add_argument(
        "--query-params",
        help="JSON string for query parameters (merged into userVariables)"
    )
    
    parser.add_argument(
        "--override",
        action="append",
        default=[],
        help="Override specific values using dot notation (e.g., --override call.state=answered)"
    )
    
    parser.add_argument(
        "--override-json",
        action="append", 
        default=[],
        help="Override with JSON values using dot notation (e.g., --override-json vars.custom='{\"key\":\"value\"}')"
    )
    
    parser.add_argument(
        "--header",
        action="append",
        default=[],
        help="Add HTTP headers for mock request (e.g., --header Authorization=Bearer token)"
    )
    
    parser.add_argument(
        "--method",
        default="POST",
        help="HTTP method for mock request (default: POST)"
    )
    
    parser.add_argument(
        "--body",
        help="JSON string for mock request body"
    )
    
    args = parser.parse_args()
    
    # Restore original sys.argv
    sys.argv = original_argv
    
    # Validate arguments
    if not args.list_tools and not args.dump_swml:
        if not args.tool_name:
            parser.error("tool_name is required unless --list-tools or --dump-swml is used")
        
        # Either args_json OR function_args_list is required
        if not args.args_json and not function_args_list:
            parser.error("Either args_json or --args with parameters is required when calling a function")
    
    try:
        # Load the agent
        if args.verbose and not args.raw:
            print(f"Loading agent from: {args.agent_path}")
        
        agent = load_agent_from_file(args.agent_path)
        
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
                            
                        if args.verbose:
                            print(f"    Config: {json.dumps(func, indent=6)}")
                    else:
                        # Regular SWAIG function
                        print(f"  {name} - {func.description}")
                        
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
                            
                        if args.verbose:
                            print(f"    Function object: {func}")
            else:
                print("  No SWAIG functions registered")
            return 0
        
        # Dump SWML if requested
        if args.dump_swml:
            return handle_dump_swml(agent, args)
        
        # Parse function arguments
        if function_args_list:
            # Using --args syntax, need to get the function to parse arguments with schema
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
        else:
            # Using JSON syntax
            try:
                function_args = json.loads(args.args_json)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in args: {e}")
                return 1
        
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
        # DataMap functions are stored as dicts, webhook functions as SWAIGFunction objects
        is_datamap = isinstance(func, dict)
        
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
    
    return 0


def console_entry_point():
    """Console script entry point for pip installation"""
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main()) 