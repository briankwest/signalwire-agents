#!/usr/bin/env python3
"""
DataSphere Webhook Environment Demo

This example demonstrates loading the traditional DataSphere skill (webhook-based) with configuration
from environment variables, showing the difference between webhook and serverless approaches.

Required Environment Variables:
- SIGNALWIRE_SPACE_NAME: Your SignalWire space name
- SIGNALWIRE_PROJECT_ID: Your SignalWire project ID  
- SIGNALWIRE_TOKEN: Your SignalWire authentication token
- DATASPHERE_DOCUMENT_ID: The DataSphere document ID to search

Optional Environment Variables:
- DATASPHERE_COUNT: Number of search results (default: 3)
- DATASPHERE_DISTANCE: Search distance threshold (default: 4.0)
- DATASPHERE_TAGS: Comma-separated list of tags to filter by
- DATASPHERE_LANGUAGE: Language code for search (e.g., "en")

Usage:
    export SIGNALWIRE_SPACE_NAME="your-space"
    export SIGNALWIRE_PROJECT_ID="your-project-id"
    export SIGNALWIRE_TOKEN="your-token"
    export DATASPHERE_DOCUMENT_ID="your-document-id"
    python examples/datasphere_webhook_env_demo.py
"""

import os
import sys
from signalwire_agents import AgentBase

def get_required_env_var(name: str) -> str:
    """Get a required environment variable or exit with error"""
    value = os.getenv(name)
    if not value:
        print(f"Error: Required environment variable {name} is not set")
        print("\nRequired environment variables:")
        print("- SIGNALWIRE_SPACE_NAME: Your SignalWire space name")
        print("- SIGNALWIRE_PROJECT_ID: Your SignalWire project ID")
        print("- SIGNALWIRE_TOKEN: Your SignalWire authentication token")
        print("- DATASPHERE_DOCUMENT_ID: The DataSphere document ID to search")
        print("\nOptional environment variables:")
        print("- DATASPHERE_COUNT: Number of search results (default: 3)")
        print("- DATASPHERE_DISTANCE: Search distance threshold (default: 4.0)")
        print("- DATASPHERE_TAGS: Comma-separated list of tags to filter by")
        print("- DATASPHERE_LANGUAGE: Language code for search (e.g., 'en')")
        sys.exit(1)
    return value

def parse_tags(tags_str: str) -> list:
    """Parse comma-separated tags string into list"""
    if not tags_str:
        return None
    return [tag.strip() for tag in tags_str.split(',') if tag.strip()]

def main():
    print("DataSphere Webhook Environment Demo")
    print("=" * 50)
    
    # Get required environment variables
    print("Loading configuration from environment variables...")
    space_name = get_required_env_var('SIGNALWIRE_SPACE_NAME')
    project_id = get_required_env_var('SIGNALWIRE_PROJECT_ID')
    token = get_required_env_var('SIGNALWIRE_TOKEN')
    document_id = get_required_env_var('DATASPHERE_DOCUMENT_ID')
    
    # Get optional environment variables with defaults
    count = int(os.getenv('DATASPHERE_COUNT', '3'))
    distance = float(os.getenv('DATASPHERE_DISTANCE', '4.0'))
    language = os.getenv('DATASPHERE_LANGUAGE')
    tags_str = os.getenv('DATASPHERE_TAGS', '')
    tags = parse_tags(tags_str)
    
    print(f"✓ Space: {space_name}")
    print(f"✓ Project ID: {project_id[:8]}...")  # Only show first 8 chars for security
    print(f"✓ Token: {'*' * len(token)}")  # Hide token completely
    print(f"✓ Document ID: {document_id}")
    print(f"✓ Search count: {count}")
    print(f"✓ Search distance: {distance}")
    if language:
        print(f"✓ Language: {language}")
    if tags:
        print(f"✓ Tags: {', '.join(tags)}")
    
    # Create agent
    agent = AgentBase("DataSphere Knowledge Assistant", route="/datasphere-webhook-demo")
    
    # Configure voice
    agent.add_language("English", "en-US", "rime.spore")
    
    # Add basic skills
    print("\nAdding basic skills...")
    try:
        agent.add_skill("datetime")
        print("✓ Added datetime skill")
    except Exception as e:
        print(f"✗ Failed to add datetime skill: {e}")
    
    try:
        agent.add_skill("math")
        print("✓ Added math skill")
    except Exception as e:
        print(f"✗ Failed to add math skill: {e}")
    
    # Build DataSphere configuration
    datasphere_config = {
        'space_name': space_name,
        'project_id': project_id,
        'token': token,
        'document_id': document_id,
        'count': count,
        'distance': distance,
        'tool_name': 'search_knowledge',
        'no_results_message': "I couldn't find any information about '{query}' in the knowledge base. Try rephrasing your question or asking about a different topic.",
        'swaig_fields': {
            'fillers': {
                'en-US': [
                    "Searching the knowledge base...",
                    "Looking up information for you...",
                    "Checking our database..."
                ]
            }
        }
    }
    
    # Add optional parameters if they were provided
    if language:
        datasphere_config['language'] = language
    if tags:
        datasphere_config['tags'] = tags
    
    # Add traditional DataSphere skill (webhook-based)
    print("\nAdding DataSphere skill (webhook-based)...")
    try:
        agent.add_skill("datasphere", datasphere_config)
        print("✓ Added DataSphere skill successfully")
        print(f"  - Tool name: search_knowledge")
        print(f"  - Execution: Webhook-based (traditional)")
        print(f"  - Document: {document_id}")
        print(f"  - Max results: {count}")
        print(f"  - Distance threshold: {distance}")
        if language:
            print(f"  - Language filter: {language}")
        if tags:
            print(f"  - Tag filters: {', '.join(tags)}")
    except Exception as e:
        print(f"✗ Failed to add DataSphere skill: {e}")
        print("  Check that your credentials and document ID are correct")
        return
    
    # Show agent capabilities
    print(f"\n🚀 Agent ready at: {agent.get_full_url()}")
    print("\nAgent Capabilities:")
    print("📅 Date and time information")
    print("🧮 Mathematical calculations")
    print("🔍 Knowledge base search (webhook execution)")
    
    print("\nDataSphere Webhook Features:")
    print("• Executes via traditional webhook endpoints")
    print("• Full Python logic for response processing")
    print("• Custom error handling and formatting")
    print("• Requests library for HTTP calls")
    print("• Uses environment variables for secure configuration")
    
    print("\nExample queries you can try:")
    print('• "What time is it?"')
    print('• "Calculate 25 * 47"')
    print('• "Search for information about [topic]"')
    print('• "Look up [specific question about your knowledge base]"')
    
    # Show environment configuration
    print(f"\nEnvironment Configuration:")
    print(f"• Space: {space_name}")
    print(f"• Document: {document_id}")
    print(f"• Results per search: {count}")
    print(f"• Distance threshold: {distance}")
    if language:
        print(f"• Language: {language}")
    if tags:
        print(f"• Tags: {', '.join(tags)}")
    
    print("\nTo modify configuration, update these environment variables:")
    print("export DATASPHERE_COUNT=5          # More results")
    print("export DATASPHERE_DISTANCE=2.0     # Stricter matching") 
    print("export DATASPHERE_TAGS='FAQ,Help'  # Filter by tags")
    print("export DATASPHERE_LANGUAGE='en'    # Language filter")
    
    print("\n" + "="*60)
    print("WEBHOOK vs SERVERLESS COMPARISON")
    print("="*60)
    print("This demo uses the WEBHOOK-based DataSphere skill:")
    print("✓ Full Python control over request/response")
    print("✓ Custom error handling and logging")
    print("✓ Flexible response formatting")
    print("✗ Requires webhook infrastructure")
    print("✗ Additional network latency")
    print("✗ More complex deployment")
    print()
    print("Compare with datasphere_serverless_env_demo.py:")
    print("✓ No webhook infrastructure needed")
    print("✓ Executes on SignalWire servers")
    print("✓ Lower latency and higher reliability")
    print("✗ Template-based response formatting only")
    print("✗ Limited custom logic")
    
    print("\nStarting agent server...")
    print("Press Ctrl+C to stop")
    
    try:
        agent.serve()
    except KeyboardInterrupt:
        print("\n\nShutting down agent...")
        print("Goodbye! 👋")

if __name__ == "__main__":
    main() 