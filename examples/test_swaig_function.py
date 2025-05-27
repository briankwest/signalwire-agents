#!/usr/bin/env python3
"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

"""
Enhanced test script for SWAIG function calls and serverless simulation
This script can:
1. Send HTTP requests to running agents (traditional mode)
2. Test agents directly in serverless mode with full environment simulation
3. Dump SWML documents for different platforms
4. Execute functions with platform-specific contexts
"""

import sys
import os
import requests
import json
import argparse
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional

class ServerlessSimulator:
    """Manages serverless environment simulation"""
    
    # Default environment presets for each platform
    PLATFORM_PRESETS = {
        'lambda': {
            'AWS_LAMBDA_FUNCTION_NAME': 'test-agent-function',
            'AWS_LAMBDA_FUNCTION_URL': 'https://abc123.lambda-url.us-east-1.on.aws/',
            'AWS_REGION': 'us-east-1',
            'AWS_API_GATEWAY_ID': 'abc123def',
            'AWS_API_GATEWAY_STAGE': 'prod'
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
            'FUNCTION_URL': 'https://us-central1-test-project.cloudfunctions.net/agent',
            'GOOGLE_CLOUD_REGION': 'us-central1',
            'K_SERVICE': 'agent'
        },
        'azure_function': {
            'AZURE_FUNCTIONS_ENVIRONMENT': 'Development',
            'FUNCTIONS_WORKER_RUNTIME': 'python'
        }
    }
    
    def __init__(self, platform: str, overrides: Optional[Dict[str, str]] = None):
        self.platform = platform
        self.original_env = dict(os.environ)
        self.preset_env = self.PLATFORM_PRESETS.get(platform, {}).copy()
        self.overrides = overrides or {}
        self.active = False
    
    def activate(self):
        """Apply serverless environment simulation"""
        if self.active:
            return
            
        # Clear conflicting environment variables
        self._clear_conflicting_env()
        
        # Apply preset environment
        os.environ.update(self.preset_env)
        
        # Apply user overrides
        os.environ.update(self.overrides)
        
        self.active = True
        print(f"✓ Activated {self.platform} environment simulation")
        
        # Debug: Show key environment variables
        if self.platform == 'lambda':
            print(f"  AWS_LAMBDA_FUNCTION_NAME: {os.environ.get('AWS_LAMBDA_FUNCTION_NAME')}")
            print(f"  AWS_LAMBDA_FUNCTION_URL: {os.environ.get('AWS_LAMBDA_FUNCTION_URL')}")
        elif self.platform == 'cgi':
            print(f"  GATEWAY_INTERFACE: {os.environ.get('GATEWAY_INTERFACE')}")
            print(f"  HTTP_HOST: {os.environ.get('HTTP_HOST')}")
        elif self.platform == 'cloud_function':
            print(f"  GOOGLE_CLOUD_PROJECT: {os.environ.get('GOOGLE_CLOUD_PROJECT')}")
            print(f"  FUNCTION_URL: {os.environ.get('FUNCTION_URL')}")
        
        # Debug: Confirm SWML_PROXY_URL_BASE is cleared
        proxy_url = os.environ.get('SWML_PROXY_URL_BASE')
        if proxy_url:
            print(f"  WARNING: SWML_PROXY_URL_BASE still set: {proxy_url}")
        else:
            print(f"  ✓ SWML_PROXY_URL_BASE cleared successfully")
    
    def deactivate(self):
        """Restore original environment"""
        if not self.active:
            return
            
        os.environ.clear()
        os.environ.update(self.original_env)
        self.active = False
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
        
        # Store original values for restoration
        if not hasattr(self, '_cleared_vars'):
            self._cleared_vars = {}
        
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

def dump_swml(agent, call_id=None):
    """
    Dump SWML document from an agent
    
    Args:
        agent: Agent instance
        call_id: Optional call ID for testing
        
    Returns:
        SWML document as string
    """
    try:
        swml = agent._render_swml(call_id)
        return swml
    except Exception as e:
        print(f"Error generating SWML: {e}")
        import traceback
        traceback.print_exc()
        return None

def execute_function_direct(agent, function_name, args=None, call_id=None):
    """
    Execute a function directly using the agent's _execute_swaig_function method
    
    Args:
        agent: Agent instance
        function_name: Name of the function to call
        args: Optional dictionary of function arguments
        call_id: Optional call ID for testing
        
    Returns:
        Function execution result
    """
    try:
        print(f"Executing function '{function_name}' directly")
        if args:
            print(f"Arguments: {json.dumps(args, indent=2)}")
        
        result = agent._execute_swaig_function(function_name, args, call_id)
        return result
    except Exception as e:
        print(f"Error executing function: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

def execute_function_serverless(agent, function_name, args=None, call_id=None, platform='lambda'):
    """
    Execute a function in full serverless context using agent.run()
    
    Args:
        agent: Agent instance
        function_name: Name of the function to call
        args: Optional dictionary of function arguments
        call_id: Optional call ID for testing
        platform: Serverless platform to simulate
        
    Returns:
        Serverless execution result
    """
    try:
        print(f"Executing function '{function_name}' in {platform} context")
        
        if platform == 'lambda':
            # Create Lambda event structure
            event = {
                'pathParameters': {'proxy': function_name} if function_name else None,
                'body': None
            }
            
            if function_name and args:
                event['body'] = json.dumps({
                    "function": function_name,
                    "argument": {
                        "parsed": [args],
                        "raw": json.dumps(args)
                    },
                    "call_id": call_id
                })
            
            print(f"Lambda event: {json.dumps(event, indent=2)}")
            result = agent.run(event=event, context={}, force_mode='lambda')
            
        elif platform == 'cgi':
            # For CGI, set PATH_INFO and call run
            if function_name:
                os.environ['PATH_INFO'] = f'/{function_name}'
            
            # For CGI function calls, we need to simulate stdin input
            if function_name and args:
                import io
                original_stdin = sys.stdin
                body_data = {
                    "function": function_name,
                    "argument": {
                        "parsed": [args],
                        "raw": json.dumps(args)
                    }
                }
                if call_id:
                    body_data["call_id"] = call_id
                
                body_json = json.dumps(body_data)
                os.environ['CONTENT_LENGTH'] = str(len(body_json))
                sys.stdin = io.StringIO(body_json)
                
                try:
                    result = agent.run(force_mode='cgi')
                finally:
                    sys.stdin = original_stdin
                    os.environ.pop('CONTENT_LENGTH', None)
            else:
                result = agent.run(force_mode='cgi')
            
        elif platform == 'cloud_function':
            # Placeholder for Cloud Function simulation
            result = agent.handle_serverless_request(event={}, context={}, mode='cloud_function')
            
        elif platform == 'azure_function':
            # Placeholder for Azure Function simulation  
            result = agent.handle_serverless_request(event={}, context={}, mode='azure_function')
            
        else:
            raise ValueError(f"Unsupported platform: {platform}")
        
        return result
        
    except Exception as e:
        print(f"Error executing function in {platform} context: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

def test_agent_direct(agent_module, args):
    """
    Test an agent directly with comprehensive serverless simulation
    
    Args:
        agent_module: Python module containing the agent
        args: Parsed command line arguments
    """
    print(f"Testing agent directly")
    
    # Set up serverless simulation BEFORE creating the agent
    simulator = None
    if args.simulate_serverless:
        # Collect environment overrides
        overrides = {}
        
        # Platform-specific overrides
        if args.simulate_serverless == 'lambda':
            if args.aws_function_name:
                overrides['AWS_LAMBDA_FUNCTION_NAME'] = args.aws_function_name
            if args.aws_function_url:
                overrides['AWS_LAMBDA_FUNCTION_URL'] = args.aws_function_url
            if args.aws_api_gateway_id:
                overrides['AWS_API_GATEWAY_ID'] = args.aws_api_gateway_id
            if args.aws_region:
                overrides['AWS_REGION'] = args.aws_region
            if args.aws_stage:
                overrides['AWS_API_GATEWAY_STAGE'] = args.aws_stage
                
        elif args.simulate_serverless == 'cgi':
            if args.cgi_host:
                overrides['HTTP_HOST'] = args.cgi_host
            if args.cgi_script_name:
                overrides['SCRIPT_NAME'] = args.cgi_script_name
            if args.cgi_https:
                overrides['HTTPS'] = 'on'
            if args.cgi_path_info:
                overrides['PATH_INFO'] = args.cgi_path_info
                
        elif args.simulate_serverless == 'cloud_function':
            if args.gcp_project:
                overrides['GOOGLE_CLOUD_PROJECT'] = args.gcp_project
            if args.gcp_function_url:
                overrides['FUNCTION_URL'] = args.gcp_function_url
            if args.gcp_region:
                overrides['GOOGLE_CLOUD_REGION'] = args.gcp_region
            if args.gcp_service:
                overrides['K_SERVICE'] = args.gcp_service
                
        elif args.simulate_serverless == 'azure_function':
            if args.azure_env:
                overrides['AZURE_FUNCTIONS_ENVIRONMENT'] = args.azure_env
            if args.azure_function_url:
                overrides['AZURE_FUNCTION_URL'] = args.azure_function_url
        
        # Generic environment overrides
        if args.env:
            for env_pair in args.env:
                if '=' in env_pair:
                    key, value = env_pair.split('=', 1)
                    overrides[key] = value
        
        # Environment file overrides
        if args.env_file:
            file_env = load_env_file(args.env_file)
            overrides.update(file_env)
        
        # Create and activate simulator BEFORE creating agent
        simulator = ServerlessSimulator(args.simulate_serverless, overrides)
        simulator.activate()
    
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
        
        try:
            # Handle different operation modes
            if args.dump_swml:
                # Dump SWML document
                print("\n" + "="*50)
                print("SWML DOCUMENT")
                print("="*50)
                
                swml = dump_swml(agent, args.call_id)
                if swml:
                    if args.format_json:
                        # Pretty print JSON
                        try:
                            parsed = json.loads(swml)
                            print(json.dumps(parsed, indent=2))
                        except:
                            print(swml)
                    else:
                        print(swml)
                
            elif args.exec:
                # Execute function
                print("\n" + "="*50)
                print(f"EXECUTING FUNCTION: {args.exec}")
                print("="*50)
                
                # Parse function arguments
                function_args = None
                if args.exec_args:
                    try:
                        function_args = json.loads(args.exec_args)
                    except json.JSONDecodeError:
                        print(f"Error: Invalid JSON in exec-args: {args.exec_args}")
                        return None
                
                if args.full_request and args.simulate_serverless:
                    # Full serverless request simulation
                    result = execute_function_serverless(
                        agent, args.exec, function_args, args.call_id, args.simulate_serverless
                    )
                else:
                    # Direct function execution
                    result = execute_function_direct(agent, args.exec, function_args, args.call_id)
                
                print("\nResult:")
                if isinstance(result, dict):
                    print(json.dumps(result, indent=2))
                else:
                    print(result)
                    
            else:
                # Default: show agent info and available functions
                print("\n" + "="*50)
                print("AGENT INFORMATION")
                print("="*50)
                
                print(f"Agent name: {getattr(agent, 'name', 'Unknown')}")
                print(f"Agent route: {getattr(agent, 'route', 'Unknown')}")
                
                # Show environment info if simulating
                if simulator:
                    print(f"Simulated platform: {args.simulate_serverless}")
                    print(f"Generated URL: {agent.get_full_url()}")
                
                # List available functions
                if hasattr(agent, '_swaig_functions'):
                    functions = list(agent._swaig_functions.keys())
                    if functions:
                        print(f"Available functions: {', '.join(functions)}")
                    else:
                        print("No SWAIG functions defined")
                
                # Dump SWML if not doing anything else
                print("\n" + "="*50)
                print("SWML DOCUMENT (preview)")
                print("="*50)
                swml = dump_swml(agent, args.call_id)
                if swml:
                    # Show first few lines
                    lines = swml.split('\n')
                    for i, line in enumerate(lines[:10]):
                        print(line)
                    if len(lines) > 10:
                        print(f"... ({len(lines) - 10} more lines)")
                        print("\nUse --dump-swml to see the complete document")
                
        finally:
            # Clean up simulator
            if simulator:
                simulator.deactivate()
        
        return True
        
    except Exception as e:
        print(f"Error testing agent: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Clean up simulator even if there was an error
        if simulator:
            simulator.deactivate()

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
    parser = argparse.ArgumentParser(
        description="Test SWAIG function calls and serverless simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # HTTP mode - test against running server
  python test_swaig_function.py --mode http --url http://localhost:3000/agent --username user --password pass --function get_weather --args '{"location":"Miami"}'
  
  # Direct mode - test agent file directly
  python test_swaig_function.py --mode direct --agent my_agent.py --dump-swml
  
  # Serverless simulation - test Lambda environment
  python test_swaig_function.py --agent my_agent.py --simulate-serverless lambda --dump-swml
  
  # Execute function in serverless context
  python test_swaig_function.py --agent my_agent.py --simulate-serverless lambda --exec get_weather --exec-args '{"location":"Miami"}' --full-request
  
  # Custom environment variables
  python test_swaig_function.py --agent my_agent.py --simulate-serverless lambda --aws-function-name my-func --env DEBUG=1 --dump-swml
        """
    )
    
    # Mode selection
    parser.add_argument("--mode", choices=['http', 'direct'], default='direct',
                       help="Test mode: 'http' for running server, 'direct' for local testing")
    
    # HTTP mode arguments
    parser.add_argument("--url", help="Base URL of the agent (e.g., http://localhost:3000/simple)")
    parser.add_argument("--username", help="Basic auth username")
    parser.add_argument("--password", help="Basic auth password")
    
    # Direct mode arguments
    parser.add_argument("--agent", help="Path to agent Python file (required for direct mode)")
    
    # Serverless simulation
    parser.add_argument("--simulate-serverless", choices=['lambda', 'cgi', 'cloud_function', 'azure_function'],
                       help="Simulate serverless environment")
    
    # AWS Lambda specific overrides
    parser.add_argument("--aws-function-name", help="Override AWS_LAMBDA_FUNCTION_NAME")
    parser.add_argument("--aws-function-url", help="Override AWS_LAMBDA_FUNCTION_URL")
    parser.add_argument("--aws-api-gateway-id", help="Override AWS_API_GATEWAY_ID")
    parser.add_argument("--aws-region", help="Override AWS_REGION")
    parser.add_argument("--aws-stage", help="Override AWS_API_GATEWAY_STAGE")
    
    # CGI specific overrides
    parser.add_argument("--cgi-host", help="Override HTTP_HOST")
    parser.add_argument("--cgi-script-name", help="Override SCRIPT_NAME")
    parser.add_argument("--cgi-https", action='store_true', help="Set HTTPS=on")
    parser.add_argument("--cgi-path-info", help="Override PATH_INFO")
    
    # Google Cloud Functions specific overrides
    parser.add_argument("--gcp-project", help="Override GOOGLE_CLOUD_PROJECT")
    parser.add_argument("--gcp-function-url", help="Override FUNCTION_URL")
    parser.add_argument("--gcp-region", help="Override GOOGLE_CLOUD_REGION")
    parser.add_argument("--gcp-service", help="Override K_SERVICE")
    
    # Azure Functions specific overrides
    parser.add_argument("--azure-env", help="Override AZURE_FUNCTIONS_ENVIRONMENT")
    parser.add_argument("--azure-function-url", help="Override Azure function URL")
    
    # Generic environment overrides
    parser.add_argument("--env", action='append', help="Set environment variable (KEY=VALUE)")
    parser.add_argument("--env-file", help="Load environment variables from file")
    
    # Operation modes
    parser.add_argument("--dump-swml", action='store_true', help="Dump SWML document")
    parser.add_argument("--format-json", action='store_true', help="Format JSON output nicely")
    parser.add_argument("--exec", help="Execute specific function")
    parser.add_argument("--exec-args", help="JSON string of function arguments")
    parser.add_argument("--full-request", action='store_true', help="Use full serverless request simulation for function execution")
    
    # Legacy function execution (for backward compatibility)
    parser.add_argument("--function", help="Function name to call (legacy, use --exec instead)")
    parser.add_argument("--args", help="JSON string of function arguments (legacy, use --exec-args instead)")
    
    # Common arguments
    parser.add_argument("--call-id", help="Call ID for testing (optional)")
    
    # Legacy serverless mode (for backward compatibility)
    parser.add_argument("--serverless-mode", choices=['server', 'cgi', 'lambda', 'cloud_function'], 
                       help="Legacy serverless mode (use --simulate-serverless instead)")
    
    args = parser.parse_args()
    
    # Handle legacy arguments
    if args.function and not args.exec:
        args.exec = args.function
    if args.args and not args.exec_args:
        args.exec_args = args.args
    if args.serverless_mode and not args.simulate_serverless:
        args.simulate_serverless = args.serverless_mode
    
    # Validate arguments
    if args.mode == 'http':
        # HTTP mode - test against running server
        if not all([args.url, args.username, args.password]):
            print("Error: HTTP mode requires --url, --username, and --password")
            sys.exit(1)
        
        if not args.exec:
            print("Error: HTTP mode requires --exec (function name)")
            sys.exit(1)
            
        # Parse function arguments
        function_args = None
        if args.exec_args:
            try:
                function_args = json.loads(args.exec_args)
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON in exec-args parameter: {args.exec_args}")
                sys.exit(1)
        
        test_swaig_http(
            args.url,
            args.username,
            args.password,
            args.exec,
            function_args
        )
        
    else:
        # Direct mode - load agent and test directly
        if not args.agent:
            print("Error: Direct mode requires --agent path")
            sys.exit(1)
            
        try:
            agent_module = load_agent_module(args.agent)
            result = test_agent_direct(agent_module, args)
            if result is None:
                sys.exit(1)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1) 