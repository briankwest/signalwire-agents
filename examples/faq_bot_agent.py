#!/usr/bin/env python3
"""
FAQ Bot Agent Example

This example demonstrates how to create a specialized agent 
for answering frequently asked questions from a knowledge base.
"""

import os
import sys
from typing import Dict, List, Optional

# Add the parent directory to the path so we can import the package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult


class FAQBotAgent(AgentBase):
    """
    A specialized agent for answering frequently asked questions (FAQs)
    from a predefined knowledge base.
    """
    
    # Define the prompt sections declaratively with placeholders
    PROMPT_SECTIONS = {
        "Personality": "You are a helpful FAQ assistant for {company_name}.",
        "Goal": "Answer customer questions using only the provided FAQ knowledge base.",
        "Instructions": [
            "Only answer questions if the information is in the FAQ knowledge base.",
            "If you don't know the answer, politely say so and offer to help with something else.",
            "Be concise and direct in your responses.",
            "If the answer is in the knowledge base, cite the relevant FAQ item."
        ],
        "Knowledge Base": ""  # Will be populated during initialization
    }
    
    def __init__(
        self, 
        name: str = "faq_bot",
        route: str = "/faq",
        host: str = "0.0.0.0", 
        port: int = 3000,
        company_name: str = "Our Company",
        faqs: Optional[Dict[str, str]] = None
    ):
        # Initialize the base agent
        super().__init__(
            name=name,
            route=route,
            host=host,
            port=port
        )
        
        # Store the company name
        self.company_name = company_name
        
        # Default FAQs if none provided
        if faqs is None:
            faqs = {
                "What are your hours?": "We are open Monday through Friday, 9am to 5pm.",
                "How do I reset my password?": "You can reset your password by clicking on the 'Forgot Password' link on the login page.",
                "Do you offer refunds?": "Yes, we offer refunds within 30 days of purchase if you're not satisfied with your product."
            }
        
        # Store FAQs
        self.faqs = faqs
        
        # Generate Knowledge Base content
        kb_content = "Frequently Asked Questions:\n\n"
        for question, answer in faqs.items():
            kb_content += f"Q: {question}\n"
            kb_content += f"A: {answer}\n\n"
        
        # Update the Knowledge Base prompt section using direct POM API
        self.pom.add_section("Knowledge Base", body=kb_content)
        
        # Update the Personality section with company name
        personality_text = self.PROMPT_SECTIONS["Personality"].format(company_name=company_name)
        self.pom.add_section("Personality", body=personality_text)
        
        # Set up a post-prompt for summary
        self.set_post_prompt("""
        Provide a JSON summary of the interaction:
        {
            "question_type": "CATEGORY_OF_QUESTION",
            "answered_from_kb": true/false,
            "follow_up_needed": true/false
        }
        """)
        
    def on_summary(self, summary: Dict):
        """Handle the conversation summary"""
        print(f"FAQ Bot conversation summary: {summary}")
        # In a real implementation, you might log this to a database,
        # trigger follow-up actions, etc.


if __name__ == "__main__":
    # Create a custom FAQ bot with specific FAQs
    custom_faqs = {
        "What is SignalWire?": "SignalWire is a communications platform that provides APIs for voice, video, and messaging.",
        "How do I create an AI Agent?": "You can create an AI Agent using the SignalWire AI Agent SDK, which provides a simple way to build and deploy conversational AI agents.",
        "What is SWML?": "SWML (SignalWire Markup Language) is a markup language for defining communications workflows, including AI interactions."
    }
    
    agent = FAQBotAgent(
        name="signalwire_faq",
        company_name="SignalWire",
        faqs=custom_faqs
    )
    
    print("Starting the FAQ Bot. Press Ctrl+C to stop.")
    
    try:
        agent.serve()
    except KeyboardInterrupt:
        print("\nStopping the FAQ Bot.")
        agent.stop() 