#!/usr/bin/env python3
"""
SWML Service Example

This example demonstrates creating a simple SWML service using the new architecture.
It shows:

1. Creating a basic SWML document with various verbs
2. Using the fluent SWML builder API
3. Setting up a web server to serve the SWML document
"""

import os
import sys

# Add the parent directory to the path so we can import the package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signalwire_agents.core.swml_service import SWMLService
from signalwire_agents.core.swml_builder import SWMLBuilder


def example_using_service():
    """Example using SWMLService directly"""
    print("=== Example using SWMLService directly ===")
    
    # Create a simple SWML service
    service = SWMLService(
        name="simple-swml-service",
        route="/simple",
        host="0.0.0.0",
        port=3001
    )
    
    # Reset the document to start fresh
    service.reset_document()
    
    # Add verbs to the document
    service.add_answer_verb()
    service.add_verb("play", {"url": "say:Hello, world!"})
    service.add_hangup_verb()
    
    # Print the rendered document
    print(service.render_document())
    print()
    
    return service


def example_using_builder():
    """Example using SWMLBuilder fluent API"""
    print("=== Example using SWMLBuilder fluent API ===")
    
    # Create a simple SWML service
    service = SWMLService(
        name="builder-swml-service",
        route="/builder",
        host="0.0.0.0",
        port=3002
    )
    
    # Create a builder for the service
    builder = SWMLBuilder(service)
    
    # Build the document using the fluent API
    builder.reset() \
           .answer() \
           .say("Hello from the SWML Builder API!") \
           .say("Isn't this easier than assembling JSON?", 
                voice="Polly.Matthew", 
                language="en-US") \
           .hangup()
    
    # Print the rendered document
    print(builder.render())
    print()
    
    return service


def example_using_ai():
    """Example using AI verb"""
    print("=== Example using AI verb ===")
    
    # Create a simple SWML service
    service = SWMLService(
        name="ai-swml-service",
        route="/ai",
        host="0.0.0.0",
        port=3003
    )
    
    # Create a builder for the service
    builder = SWMLBuilder(service)
    
    # Build the document using the fluent API
    builder.reset() \
           .answer() \
           .ai(
               prompt_text="You are a helpful assistant. Answer user questions concisely.",
               post_prompt="Summarize the conversation in 1-2 sentences."
           ) \
           .hangup()
    
    # Print the rendered document
    print(builder.render())
    print()
    
    return service


if __name__ == "__main__":
    # Run the examples
    service1 = example_using_service()
    service2 = example_using_builder()
    service3 = example_using_ai()
    
    # Ask which example to serve
    print("Choose a service to start:")
    print("1. Simple SWML service")
    print("2. Builder SWML service")
    print("3. AI SWML service")
    choice = input("Enter choice (1-3) or any other key to exit: ")
    
    if choice == "1":
        service1.serve()
    elif choice == "2":
        service2.serve()
    elif choice == "3":
        service3.serve()
    else:
        print("Exiting.") 