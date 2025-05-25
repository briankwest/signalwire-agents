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
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

# Check for --raw flag early to suppress logging before any signalwire imports
if "--raw" in sys.argv:
    # More aggressive logging suppression for raw mode
    logging.getLogger().setLevel(logging.CRITICAL + 1)  # Suppress everything
    logging.getLogger().addHandler(logging.NullHandler())
    
    # Monkey-patch specific loggers to completely silence them
    def silent_log(*args, **kwargs):
        pass
    
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

# Add the parent directory to the path so we can import signalwire_agents
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult


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


def main():
    """Main entry point for the CLI tool"""
    parser = argparse.ArgumentParser(
        description="Test SWAIG functions from agent applications with comprehensive simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s examples/datasphere_webhook_env_demo.py search_knowledge '{"query":"test"}'
  %(prog)s examples/simple_agent.py calculate '{"expression":"2+2"}' --fake-full-data
  %(prog)s examples/my_agent.py my_datamap_func '{"input":"value"}' --datamap
  %(prog)s examples/my_agent.py --list-tools
  %(prog)s examples/my_agent.py --dump-swml
  %(prog)s examples/my_agent.py --dump-swml --verbose
  %(prog)s examples/my_agent.py --dump-swml --raw
  %(prog)s examples/my_agent.py --dump-swml --raw | jq '.'
  %(prog)s examples/my_agent.py --dump-swml --raw | jq '.sections.main[1].ai.SWAIG.functions'
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
        help="JSON string containing the arguments to pass to the function"
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
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.list_tools and not args.dump_swml and (not args.tool_name or not args.args_json):
        parser.error("tool_name and args_json are required unless --list-tools or --dump-swml is used")
    
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
                        print(f"  {name} - DataMap function (serverless)")
                        if args.verbose:
                            print(f"    Config: {json.dumps(func, indent=6)}")
                    else:
                        # Regular SWAIG function
                        print(f"  {name} - {func.description}")
                        if args.verbose:
                            print(f"    Function: {func}")
            else:
                print("  No SWAIG functions registered")
            return 0
        
        # Dump SWML if requested
        if args.dump_swml:
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
                # Generate the SWML document
                swml_doc = agent._render_swml()
                
                if args.raw:
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
                    import sys
                    print(f"Error generating SWML: {e}", file=sys.stderr)
                    if args.verbose:
                        import traceback
                        traceback.print_exc(file=sys.stderr)
                else:
                    print(f"Error generating SWML: {e}")
                    if args.verbose:
                        import traceback
                        traceback.print_exc()
                return 1
        
        # Parse arguments
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
        
        # Check if the function exists
        if not hasattr(agent, '_swaig_functions') or args.tool_name not in agent._swaig_functions:
            print(f"Error: Function '{args.tool_name}' not found in agent")
            print(f"Available functions: {list(agent._swaig_functions.keys()) if hasattr(agent, '_swaig_functions') else 'None'}")
            return 1
        
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