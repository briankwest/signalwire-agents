#!/usr/bin/env python3
"""
Contexts and Steps Demo Agent

This agent demonstrates the new contexts and steps system as an alternative
to traditional POM-based prompts. It shows both POM-style step building
and direct text approaches.
"""

from signalwire_agents import AgentBase


class ContextsDemoAgent(AgentBase):
    """Computer Sales Agent demonstrating contexts and steps system"""
    
    def __init__(self):
        super().__init__(
            name="Computer Sales Agent",
            route="/contexts-demo"
        )
        
        # Set base prompt (required even when using contexts)
        self.prompt_add_section(
            "Role", 
            "You are a knowledgeable computer sales consultant helping customers find the perfect computer."
        )
        self.prompt_add_section(
            "Instructions",
            "Follow the structured sales workflow to guide customers through their computer purchase decision.",
            bullets=[
                "Complete each step's specific criteria before advancing",
                "Ask focused questions to gather the exact information needed",
                "Be helpful and consultative, not pushy"
            ]
        )
        
        # Define contexts and steps AFTER setting base prompt
        # Contexts add structured workflow on top of the base prompt
        contexts = self.define_contexts()
        
        # Create a single context named "default" (required for single context)
        context = contexts.add_context("default")
        
        # Step 1: Determine use case - Gaming, Work, or Balanced
        context.add_step("determine_use_case") \
            .add_section("Current Task", "Identify the customer's primary computer use case") \
            .add_bullets("Required Information to Collect", [
                "What will they primarily use the computer for?",
                "Do they play video games? If so, what types and how often?",
                "Do they need it for work? What kind of work applications?",
                "Do they do creative work like video editing, design, or programming?",
                "Help them categorize as: GAMING, WORK, or BALANCED"
            ]) \
            .set_step_criteria("Customer has clearly stated their use case as one of: GAMING (high-performance games), WORK (business/productivity), or BALANCED (mix of both)") \
            .set_functions("none")
        
        # Step 2: Laptop vs Desktop preference
        context.add_step("determine_form_factor") \
            .add_section("Current Task", "Determine if customer wants a laptop or desktop computer") \
            .add_bullets("Decision-Making Questions", [
                "Ask directly: 'Are you looking for a laptop or desktop computer or if they need help deciding?'",
                "If they're unsure, help them decide by asking:",
                "  - Do you need to take it with you places, or will it stay in one location?",
                "  - Do you already have a monitor, keyboard, and mouse at home?",
                "  - Is desk space limited?",
                "  - What's more important: portability or maximum performance for your budget?"
            ]) \
            .add_section("Important", "If customer explicitly says 'laptop' or 'desktop', immediately acknowledge their choice and move to the next step. Do NOT ask additional form factor questions.") \
            .set_step_criteria("Customer has explicitly stated they want either a LAPTOP or DESKTOP (exact words matter)") \
            .set_functions("none")
        
        # Step 3: Final recommendation
        context.add_step("make_recommendation") \
            .add_section("Current Task", "Provide specific computer recommendation based on gathered information") \
            .add_bullets("Recommendation Requirements", [
                "Recommend a specific computer type based on their use case and form factor",
                "Explain why this recommendation fits their needs",
                "Mention key specs that matter for their use case",
                "Provide a rough price range they should expect"
            ]) \
            .set_step_criteria("Customer has received a specific recommendation with explanation and pricing guidance, and acknowledges understanding the recommendation") \
            .set_valid_steps(["determine_use_case"])  # Can start over with new customer
        
        # Add language support
        self.add_language(
            name="English",
            code="en-US",
            voice="rime.spore"
        )
        
        # Add internal fillers for the next_step function (used by contexts system)
        self.add_internal_filler("next_step", "en-US", [
            "Great! Let's move to the next step...",
            "Perfect! Moving forward in our conversation...",
            "Excellent! Let's continue to the next part...",
            "Wonderful! Progressing to the next step..."
        ])
        
        # No additional skills needed for this sales workflow


def main():
    """Main function to run the computer sales agent"""
    print("=" * 60)
    print("COMPUTER SALES AGENT - CONTEXTS DEMO")
    print("=" * 60)
    print()
    print("This agent demonstrates structured sales workflow using contexts and steps!")
    print()
    print("Sales workflow:")
    print("  1. Determine use case (Gaming/Work/Balanced)")
    print("  2. Choose form factor (Laptop/Desktop)")
    print("  3. Receive personalized recommendation")
    print()
    print("Features demonstrated:")
    print("  • Specific, measurable step criteria")
    print("  • Focused question guidance")
    print("  • Sequential workflow progression")
    print("  • Structured sales process")
    print()
    print("Test the agent at: http://localhost:3000/contexts-demo")
    print()
    
    agent = ContextsDemoAgent()
    
    print("Agent configuration:")
    print(f"  Name: {agent.get_name()}")
    print(f"  Route: /contexts-demo")
    print(f"  Mode: Computer Sales with Contexts & Steps")
    print()
    
    try:
        agent.run()
    except KeyboardInterrupt:
        print("\nShutting down agent...")


if __name__ == "__main__":
    agent = ContextsDemoAgent()
    print("Note: Works in any deployment mode (server/CGI/Lambda)")
    agent.run() 