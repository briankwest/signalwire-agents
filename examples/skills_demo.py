#!/usr/bin/env python3
"""
Skills System Demo

This example demonstrates the new modular skills system for SignalWire agents.
Skills are automatically discovered and can be added with simple one-liner calls.

To use the web_search skill, you'll need:
- GOOGLE_SEARCH_API_KEY environment variable
- GOOGLE_SEARCH_ENGINE_ID environment variable

The datetime and math skills work without any additional setup.
"""

import os
from signalwire_agents import AgentBase

def main():
    # Create an agent
    agent = AgentBase("Multi-Skill Assistant", route="/assistant")
    
    # Configure the agent with rime.spore voice
    agent.add_language("English", "en-US", "rime.spore")
    
    print("Creating agent with multiple skills...")
    
    # Add skills using the new system - these are one-liners!
    try:
        agent.add_skill("datetime")
        print("Added datetime skill")
    except Exception as e:
        print(f"Failed to add datetime skill: {e}")
    
    try:
        agent.add_skill("math")
        print("Added math skill")
    except Exception as e:
        print(f"Failed to add math skill: {e}")
    
    try:
        # Add web search with custom parameters
        # num_results=1 (default) for fast responses, delay=0 (default) for no latency
        agent.add_skill("web_search", {
            "num_results": 1,  # Just get one result for faster responses
            "delay": 0         # No delay between requests for minimal latency
        })
        print("Added web search skill with optimized parameters (num_results=1, delay=0)")
    except Exception as e:
        print(f"Failed to add web search skill: {e}")
        print("   Note: Web search requires GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID")
    
    # Show what skills are loaded
    loaded_skills = agent.list_skills()
    print(f"\nLoaded skills: {', '.join(loaded_skills)}")
    
    # Show available skills from registry
    try:
        from signalwire_agents.skills.registry import skill_registry
        available_skills = skill_registry.list_skills()
        print(f"\nAvailable skills in registry:")
        for skill in available_skills:
            print(f"  - {skill['name']}: {skill['description']}")
            if skill['required_env_vars']:
                print(f"    Requires env vars: {', '.join(skill['required_env_vars'])}")
            if skill['required_packages']:
                print(f"    Requires packages: {', '.join(skill['required_packages'])}")
    except Exception as e:
        print(f"Failed to list available skills: {e}")
    
    print(f"\nAgent available at: {agent.get_full_url()}")
    print("The agent now has enhanced capabilities:")
    print("   - Can tell current date/time")
    print("   - Can perform mathematical calculations")
    if "web_search" in loaded_skills:
        print("   - Can search the web for information (optimized for speed: 1 result, no delay)")
    
    print("\nSkill Parameter Examples:")
    print("   # Default web search (1 result, no delay)")
    print("   agent.add_skill('web_search')")
    print("   ")
    print("   # Custom web search (3 results, 0.5s delay)")
    print("   agent.add_skill('web_search', {'num_results': 3, 'delay': 0.5})")
    print("   ")
    print("   # Fast web search (1 result, no delay)")
    print("   agent.add_skill('web_search', {'num_results': 1, 'delay': 0})")
    
    print("\nStarting agent server...")
    agent.serve()

if __name__ == "__main__":
    main() 