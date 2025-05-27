#!/usr/bin/env python3
"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

"""
Enhanced test script for SWAIG function calls
This script can:
1. Send HTTP requests to running agents (traditional mode)
2. Test agents directly in serverless mode (CGI, Lambda, etc.)
"""

import sys
import os
import requests
import json
import argparse
import importlib.util
from pathlib import Path

def test_swaig_http(base_url, username, password, function_name, args=None):
    """
    Test a SWAIG function by sending an HTTP request to a running agent
    
    Args:
        base_url: Base URL of the agent (e.g., http://localhost:3000/simple)
        username: Basic auth username
        password: Basic auth password
        function_name: Name of the function to call
        args: Optional dictionary of function arguments
    """
    # Ensure URL has trailing slash
    if not base_url.endswith('/'):
        base_url = base_url + '/'
    
    # Construct the SWAIG endpoint URL
    url = f"{base_url}swaig/"
    
    # Prepare the request body
    body = {
        "function": function_name
    }
    
    if args:
        # Format arguments as expected by the SWAIG handler
        body["argument"] = {
            "parsed": [args],
            "raw": json.dumps(args)
        }
    
    print(f"Sending HTTP request to {url}")
    print(f"Request body: {json.dumps(body, indent=2)}")
    
    # Send the request with basic auth
    response = requests.post(
        url,
        json=body,
        auth=(username, password)
    )
    
    print(f"Response status: {response.status_code}")
    try:
        print(f"Response body: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response text: {response.text}")
    
    return response

def test_swaig_serverless(agent_module, function_name, args=None, mode='server', call_id=None):
    """
    Test a SWAIG function by directly calling agent methods (serverless simulation)
    
    Args:
        agent_module: Python module containing the agent
        function_name: Name of the function to call
        args: Optional dictionary of function arguments
        mode: Serverless mode to simulate ('cgi', 'lambda', 'cloud_function', 'server')
        call_id: Optional call ID for testing
    """
    print(f"Testing agent directly in {mode} mode")
    
    try:
        # Look for a function that creates/returns an agent
        agent = None
        for attr_name in dir(agent_module):
            attr = getattr(agent_module, attr_name)
            if callable(attr) and not attr_name.startswith('_'):
                # Try calling it to see if it returns an agent-like object
                try:
                    potential_agent = attr()
                    if hasattr(potential_agent, '_execute_swaig_function'):
                        agent = potential_agent
                        print(f"Found agent using function: {attr_name}()")
                        break
                except:
                    continue
        
        if not agent:
            print("Error: Could not find an agent in the module")
            print("Available functions:", [name for name in dir(agent_module) if callable(getattr(agent_module, name)) and not name.startswith('_')])
            return None
        
        # Set up environment variables for the desired mode
        original_env = {}
        if mode == 'cgi':
            original_env = {k: os.environ.get(k) for k in ['GATEWAY_INTERFACE', 'PATH_INFO']}
            os.environ['GATEWAY_INTERFACE'] = 'CGI/1.1'
            os.environ['PATH_INFO'] = f'/{function_name}'
        elif mode == 'lambda':
            original_env = {k: os.environ.get(k) for k in ['AWS_LAMBDA_FUNCTION_NAME']}
            os.environ['AWS_LAMBDA_FUNCTION_NAME'] = 'test-function'
        elif mode == 'cloud_function':
            original_env = {k: os.environ.get(k) for k in ['GOOGLE_CLOUD_PROJECT']}
            os.environ['GOOGLE_CLOUD_PROJECT'] = 'test-project'
        
        try:
            if mode == 'lambda':
                # Simulate Lambda event
                event = {
                    'pathParameters': {'proxy': function_name},
                    'body': None
                }
                
                if args:
                    event['body'] = json.dumps({
                        "function": function_name,
                        "argument": {
                            "parsed": [args],
                            "raw": json.dumps(args)
                        },
                        "call_id": call_id
                    })
                
                print(f"Simulating Lambda event: {json.dumps(event, indent=2)}")
                result = agent.run(event=event, context={}, force_mode='lambda')
                print(f"Lambda response: {json.dumps(result, indent=2)}")
                
            elif mode == 'cgi':
                # For CGI, we call run() with force_mode and it will use environment variables
                print(f"Simulating CGI with PATH_INFO=/{function_name}")
                result = agent.run(force_mode='cgi')
                print(f"CGI response: {result}")
                
            else:
                # Direct function call for testing
                print(f"Calling _execute_swaig_function directly")
                result = agent._execute_swaig_function(function_name, args, call_id)
                print(f"Direct result: {json.dumps(result, indent=2)}")
                
        finally:
            # Restore original environment
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        
        return result
        
    except Exception as e:
        print(f"Error testing agent: {e}")
        import traceback
        traceback.print_exc()
        return None

def load_agent_module(module_path):
    """
    Load an agent module from file path
    
    Args:
        module_path: Path to the Python file containing the agent
        
    Returns:
        Loaded module object
    """
    module_path = Path(module_path)
    if not module_path.exists():
        raise FileNotFoundError(f"Agent module not found: {module_path}")
    
    # Load the module
    spec = importlib.util.spec_from_file_location("agent_module", module_path)
    module = importlib.util.module_from_spec(spec)
    
    # Add the module's directory to sys.path temporarily
    original_path = sys.path[:]
    sys.path.insert(0, str(module_path.parent))
    
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = original_path
    
    return module

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test SWAIG function calls (HTTP or direct)")
    
    # Mode selection
    parser.add_argument("--mode", choices=['http', 'direct'], default='http',
                       help="Test mode: 'http' for running server, 'direct' for serverless simulation")
    
    # HTTP mode arguments
    parser.add_argument("--url", help="Base URL of the agent (e.g., http://localhost:3000/simple)")
    parser.add_argument("--username", help="Basic auth username")
    parser.add_argument("--password", help="Basic auth password")
    
    # Direct mode arguments
    parser.add_argument("--agent", help="Path to agent Python file (for direct mode)")
    parser.add_argument("--serverless-mode", choices=['server', 'cgi', 'lambda', 'cloud_function'], 
                       default='server', help="Serverless mode to simulate (for direct mode)")
    
    # Common arguments
    parser.add_argument("--function", required=True, help="Function name to call")
    parser.add_argument("--args", help="JSON string of function arguments (e.g., '{\"location\":\"Orlando\"}')")
    parser.add_argument("--call-id", help="Call ID for testing (optional)")
    
    args = parser.parse_args()
    
    # Parse function arguments
    function_args = None
    if args.args:
        try:
            function_args = json.loads(args.args)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in args parameter: {args.args}")
            sys.exit(1)
    
    if args.mode == 'http':
        # HTTP mode - test against running server
        if not all([args.url, args.username, args.password]):
            print("Error: HTTP mode requires --url, --username, and --password")
            sys.exit(1)
            
        test_swaig_http(
            args.url,
            args.username,
            args.password,
            args.function,
            function_args
        )
        
    else:
        # Direct mode - load agent and test directly
        if not args.agent:
            print("Error: Direct mode requires --agent path")
            sys.exit(1)
            
        try:
            agent_module = load_agent_module(args.agent)
            test_swaig_serverless(
                agent_module,
                args.function,
                function_args,
                args.serverless_mode,
                args.call_id
            )
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1) 