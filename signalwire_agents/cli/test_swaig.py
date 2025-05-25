#!/usr/bin/env python3
"""
SWAIG Function CLI Testing Tool

This tool loads an agent application and calls a specified SWAIG function
with supplied JSON input for testing purposes. It's particularly useful
for testing webhook-style tools without running the full server.

Usage:
    python -m signalwire_agents.cli.test_swaig <agent_path> <tool_name> <args_json>
    
    # Or directly:
    python signalwire_agents/cli/test_swaig.py <agent_path> <tool_name> <args_json>
    
    # Or as installed command:
    swaig-test <agent_path> <tool_name> <args_json>
    
Examples:
    # Test DataSphere search
    swaig-test examples/datasphere_webhook_env_demo.py search_knowledge '{"query":"test search"}'
    
    # Test math skill
    swaig-test examples/simple_agent.py calculate '{"expression":"2+2"}'
    
    # Test with raw data
    swaig-test examples/my_agent.py my_tool '{"param":"value"}' --raw-data '{"call_id":"test-123"}'
"""

import sys
import os
import json
import importlib.util
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Add the parent directory to the path so we can import signalwire_agents
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult


def load_agent_from_file(agent_path: str) -> AgentBase:
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
        description="Test SWAIG functions from agent applications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s examples/datasphere_webhook_env_demo.py search_knowledge '{"query":"test"}'
  %(prog)s examples/simple_agent.py calculate '{"expression":"2+2"}'
  %(prog)s my_agent.py my_tool '{"param":"value"}' --raw-data '{"call_id":"test-123"}'
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
        help="JSON string containing the arguments to pass to the function"
    )
    
    parser.add_argument(
        "--raw-data",
        help="Optional JSON string containing raw data (e.g., call_id, etc.)",
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
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.list_tools and (not args.tool_name or not args.args_json):
        parser.error("tool_name and args_json are required unless --list-tools is used")
    
    try:
        # Load the agent
        if args.verbose:
            print(f"Loading agent from: {args.agent_path}")
        
        agent = load_agent_from_file(args.agent_path)
        
        if args.verbose:
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
                    else:
                        # Regular SWAIG function
                        print(f"  {name} - {func.description}")
            else:
                print("  No SWAIG functions registered")
            return 0
        
        # Parse arguments
        try:
            function_args = json.loads(args.args_json)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in args: {e}")
            return 1
        
        try:
            raw_data = json.loads(args.raw_data)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in raw-data: {e}")
            return 1
        
        # Check if the function exists
        if not hasattr(agent, '_swaig_functions') or args.tool_name not in agent._swaig_functions:
            print(f"Error: Function '{args.tool_name}' not found in agent")
            print(f"Available functions: {list(agent._swaig_functions.keys()) if hasattr(agent, '_swaig_functions') else 'None'}")
            return 1
        
        func = agent._swaig_functions[args.tool_name]
        
        # Check if it's a DataMap function (serverless)
        if isinstance(func, dict):
            print(f"Error: '{args.tool_name}' is a DataMap function (serverless execution)")
            print("DataMap functions execute on SignalWire's servers, not locally")
            print("This tool only supports webhook-style SWAIG functions")
            return 1
        
        if args.verbose:
            print(f"\nCalling function: {args.tool_name}")
            print(f"Arguments: {json.dumps(function_args, indent=2)}")
            print(f"Raw data: {json.dumps(raw_data, indent=2)}")
            print(f"Function description: {func.description}")
            print("-" * 60)
        
        # Call the function
        try:
            result = agent.on_function_call(args.tool_name, function_args, raw_data)
            
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