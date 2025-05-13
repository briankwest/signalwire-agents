#!/usr/bin/env python3
"""
Test script for SWAIG function calls
This script sends a direct request to the /swaig/ endpoint of an agent
with the correct authentication.
"""

import sys
import os
import requests
import json
import argparse

def test_swaig_function(base_url, username, password, function_name, args=None):
    """
    Test a SWAIG function by sending a direct request
    
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
    
    print(f"Sending request to {url}")
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test SWAIG function calls")
    parser.add_argument("--url", required=True, help="Base URL of the agent (e.g., http://localhost:3000/simple)")
    parser.add_argument("--username", required=True, help="Basic auth username")
    parser.add_argument("--password", required=True, help="Basic auth password")
    parser.add_argument("--function", required=True, help="Function name to call")
    parser.add_argument("--args", help="JSON string of function arguments (e.g., '{\"location\":\"Orlando\"}')")
    
    args = parser.parse_args()
    
    function_args = None
    if args.args:
        try:
            function_args = json.loads(args.args)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in args parameter: {args.args}")
            sys.exit(1)
    
    test_swaig_function(
        args.url,
        args.username,
        args.password,
        args.function,
        function_args
    ) 