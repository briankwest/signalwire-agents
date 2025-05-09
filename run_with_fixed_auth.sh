#!/bin/bash
# Script to run an agent with fixed authentication credentials

# Set environment variables for authentication
export SWML_BASIC_AUTH_USER="admin"
export SWML_BASIC_AUTH_PASSWORD="signalwire123"

echo "Starting agent with fixed credentials:"
echo "Username: $SWML_BASIC_AUTH_USER"
echo "Password: $SWML_BASIC_AUTH_PASSWORD"
echo "----------------------------------------"

# Run the test agent
python env_auth_test.py

# Cleanup - unset the environment variables when done
unset SWML_BASIC_AUTH_USER
unset SWML_BASIC_AUTH_PASSWORD 