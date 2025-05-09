#!/usr/bin/env python3
"""
Simple test script to verify environment variables are accessible
"""

import os
import sys

print("Environment Variable Access Test")
print("-" * 40)

# Check for auth environment variables
user = os.environ.get('SWML_BASIC_AUTH_USER')
password = os.environ.get('SWML_BASIC_AUTH_PASSWORD')

print(f"SWML_BASIC_AUTH_USER: {user if user else 'NOT SET'}")
print(f"SWML_BASIC_AUTH_PASSWORD: {password if password else 'NOT SET'}")

if user and password:
    print("\n✅ Environment variables are set and accessible to Python.")
    print(f"User: {user}")
    print(f"Password: {password}")
else:
    print("\n❌ Environment variables are NOT set or accessible to Python.")
    print("Make sure you're setting them correctly before running the script.")
    print("Example:")
    print("  SWML_BASIC_AUTH_USER=admin SWML_BASIC_AUTH_PASSWORD=secret python examples/env_auth_simple.py") 