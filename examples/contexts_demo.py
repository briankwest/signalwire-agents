#!/usr/bin/env python3
"""
Contexts and Steps Demo Agent

This agent demonstrates the new contexts and steps system as an alternative
to traditional POM-based prompts. It shows both POM-style step building
and direct text approaches.
"""

from signalwire_agents import AgentBase


class ContextsDemoAgent(AgentBase):
    """Agent demonstrating contexts and steps system"""
    
    def __init__(self):
        super().__init__(
            name="Contexts Demo Agent",
            route="/contexts-demo"
        )
        
        # Define contexts and steps BEFORE adding skills
        # Skills might add prompt sections which would trigger validation error
        contexts = self.define_contexts()
        
        # Create a single context named "default" (required for single context)
        context = contexts.add_context("default")
        
        # Step 1: Greeting with direct text
        context.add_step("greeting") \
            .set_text("Greet the customer warmly and ask how you can help them today. Be friendly and professional.") \
            .set_step_criteria("Customer has been greeted and has stated their need or question") \
            .set_functions("none")  # No functions needed for greeting
        
        # Step 2: Information gathering with POM-style sections
        context.add_step("gather_info") \
            .add_section("Current Task", "Gather detailed information about the customer's request") \
            .add_bullets("Instructions", [
                "Ask clarifying questions to understand their needs",
                "Be patient and thorough in collecting information", 
                "Confirm your understanding before proceeding"
            ]) \
            .add_section("Available Tools", "You have access to helpful functions") \
            .add_bullets("Functions Available", [
                "datetime - for current date/time information",
                "math - for mathematical calculations"
            ]) \
            .set_step_criteria("You have all the information needed to help the customer") \
            .set_functions(["datetime", "math"])  # Only specific functions for this step
        
        # Step 3: Problem resolution with navigation control
        context.add_step("resolve") \
            .set_text("Now resolve the customer's issue using the information gathered. Provide a clear, helpful solution.") \
            .set_step_criteria("Customer's issue has been fully resolved to their satisfaction") \
            .set_valid_steps(["follow_up", "greeting"])  # Can go to follow-up or start over
        
        # Step 4: Follow-up
        context.add_step("follow_up") \
            .add_section("Current Task", "Follow up to ensure customer satisfaction") \
            .add_bullets("Follow-up Actions", [
                "Ask if they need any additional help",
                "Confirm they are satisfied with the solution",
                "Offer to assist with related questions"
            ]) \
            .set_step_criteria("Customer confirms they are satisfied and has no additional questions") \
            .set_valid_steps(["greeting"])  # Can start over with new customer
        
        # Now add skills after contexts are defined
        self.add_skill("datetime")
        self.add_skill("math")


def main():
    """Main function to run the contexts demo agent"""
    print("=" * 60)
    print("CONTEXTS AND STEPS DEMO AGENT")
    print("=" * 60)
    print()
    print("This agent demonstrates the new contexts and steps system!")
    print()
    print("Features demonstrated:")
    print("  • Single 'default' context")
    print("  • Mix of direct text and POM-style steps")
    print("  • Step-specific function restrictions")
    print("  • Custom step navigation")
    print("  • Step completion criteria")
    print()
    print("Test the agent at: http://localhost:3000/contexts-demo")
    print()
    
    agent = ContextsDemoAgent()
    
    print("Agent configuration:")
    print(f"  Name: {agent.get_name()}")
    print(f"  Route: /contexts-demo")
    print(f"  Skills: datetime, math")
    print(f"  Mode: Contexts & Steps")
    print()
    
    try:
        agent.serve()
    except KeyboardInterrupt:
        print("\nShutting down agent...")


if __name__ == "__main__":
    main() 