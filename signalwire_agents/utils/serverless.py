#!/usr/bin/env python3
"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

import os

def get_execution_mode() -> str:
    """
    Detect the current execution environment.
    
    Returns:
        str: One of 'cgi', 'lambda', 'cloud_function', 'azure_function', or 'server'
    """
    if os.getenv('GATEWAY_INTERFACE'):
        return 'cgi'
    elif os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
        return 'lambda'
    elif os.getenv('GOOGLE_CLOUD_PROJECT'):
        return 'cloud_function'
    elif os.getenv('AZURE_FUNCTIONS_ENVIRONMENT'):
        return 'azure_function'
    else:
        return 'server'

def is_serverless_mode() -> bool:
    """
    Check if running in any serverless environment.
    
    Returns:
        bool: True if in serverless mode, False if in server mode
    """
    return get_execution_mode() != 'server' 