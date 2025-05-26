#!/usr/bin/env python3
"""
Generic Lambda wrapper for ANY existing SignalWire AI Agent

This wrapper shows how to deploy any existing agent to AWS Lambda
without modifying the agent code at all.

Instructions:
1. Replace the import and agent creation below with your actual agent
2. Deploy this file to Lambda
3. All existing functionality will work unchanged

Example agents you can use:
- basic_agent_with_functions.py
- order_pizza_agent.py  
- datasphere_agent.py
- Any custom agent you've created

Features preserved in Lambda:
SUCCESS: All SWAIG functions work
SUCCESS: Basic authentication works
SUCCESS: Health endpoints work (/health, /ready)
SUCCESS: Debug endpoints work (/debug)
SUCCESS: All routing works (/swaig, /post_prompt, etc.)
SUCCESS: Session management works (stateless tokens)
SUCCESS: Structured logging works (CloudWatch compatible)
"""

import os
import sys

# Add the signalwire_agents module to the path if needed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import Mangum for Lambda integration
try:
    from mangum import Mangum
except ImportError:
    print("ERROR: Mangum not installed. Run: pip install mangum")
    sys.exit(1)

# ============================================================================
# STEP 1: Import your existing agent
# ============================================================================

# Option 1: Import an existing example agent
# from basic_agent_with_functions import BasicAgentWithFunctions as MyAgent

# Option 2: Import your custom agent (uncomment and modify)
# from my_custom_agent import MyCustomAgent as MyAgent

# Option 3: Import a skill-based agent (TESTING WEB SEARCH AGENT)
import os
from signalwire_agents import AgentBase

def create_web_search_agent():
    """Create web search agent for Lambda testing"""
    agent = AgentBase("Web Search Lambda Agent", route="/")
    agent.add_language("English", "en-US", "rime.spore")
    
    # Get API credentials
    google_api_key = os.getenv('GOOGLE_SEARCH_API_KEY', 'test_key')
    google_search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID', 'test_engine')
    
    # Add web search with the NEW max_content_length parameter
    agent.add_skill("web_search", {
        "api_key": google_api_key,
        "search_engine_id": google_search_engine_id,
        "num_results": 1,
        "delay": 0,
        "max_content_length": 3000,  # NEW configurable parameter!
        "no_results_message": "No results from Lambda for '{query}'.",
    })
    return agent

MyAgent = create_web_search_agent

# ============================================================================
# STEP 2: Create your agent instance (same as local development)
# ============================================================================

# Create the agent exactly as you would locally
agent = MyAgent()  # Web search agent function call

# ============================================================================ 
# STEP 3: Lambda setup (no changes needed)
# ============================================================================

# Get the FastAPI app from the agent
app = agent.get_app()

# Create the Lambda handler using Mangum
handler = Mangum(app)

def lambda_handler(event, context):
    """
    AWS Lambda entry point
    
    This is the function that AWS Lambda calls.
    Mangum translates between API Gateway events and FastAPI.
    """
    return handler(event, context)

# ============================================================================
# Optional: Local testing
# ============================================================================

if __name__ == "__main__":
    print("TESTING: Testing agent locally...")
    print(f"AGENT: Agent: {agent.get_name()}")
    print(f"FUNCTIONS: Functions: {len(agent._swaig_functions)}")
    print()
    print("NOTE: Note: This runs FastAPI directly, not via Lambda")
    print("   For true Lambda testing, use 'sam local start-api'")
    print()
    
    # List available functions
    if agent._swaig_functions:
        print("AVAILABLE: Available SWAIG functions:")
        for func_name in agent._swaig_functions.keys():
            print(f"   - {func_name}")
        print()
    
    # Run locally for testing
    agent.serve(host="0.0.0.0", port=8080) 