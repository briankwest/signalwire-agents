#!/usr/bin/env python3
"""
Stateful Agent Example

This example demonstrates how to use the state management capabilities
of the AgentBase class to build an agent that maintains conversation state.
"""

import os
import sys
import json
from datetime import datetime

# Add the parent directory to the path so we can import the package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult
from signalwire_agents.core.state import FileStateManager


class StatefulAgent(AgentBase):
    """
    A demo agent that uses state management to remember previous interactions
    
    This agent demonstrates how to:
    
    1. Enable state tracking with enable_state_tracking=True
    2. Implement the startup_hook and hangup_hook methods that are automatically registered
    3. Store and retrieve data in the conversation state
    4. Create custom SWAIG functions that interact with the state
    
    State tracking uses two special methods:
    - startup_hook: Called when a conversation starts, initializes state
    - hangup_hook: Called when a conversation ends, records final state
    
    Both functions are automatically registered when enable_state_tracking=True
    and receive call_id in the raw_data parameter.
    """
    
    def __init__(self):
        # Initialize with custom state manager
        state_manager = FileStateManager(
            storage_dir="./state_data",
            expiry_days=1.0
        )
        
        # Initialize the agent
        super().__init__(
            name="stateful",
            route="/stateful",
            host="0.0.0.0",
            port=3000,
            state_manager=state_manager,
            enable_state_tracking=True
        )
        
        # Use AgentBase methods instead of direct POM API calls
        self.prompt_add_section("Personality", body="You are a helpful assistant that remembers previous interactions.")
        self.prompt_add_section("Goal", body="Help users with their questions and remember context from the conversation.")
        self.prompt_add_section("Instructions", bullets=[
            "Keep track of user's preferences and previous questions.",
            "Use the get_time function when asked about the current time.",
            "Use the store_preference function to remember user preferences.",
            "Use the get_preferences function to recall user preferences."
        ])
        
        # Set up post-prompt
        self.set_post_prompt("""
        Return a JSON summary of the conversation:
        {
            "topic": "MAIN_TOPIC",
            "preferences_mentioned": ["any", "preferences", "mentioned"],
            "questions_asked": ["list", "of", "questions"]
        }
        """)
    
    @AgentBase.tool(
        name="get_time",
        description="Get the current time",
        parameters={}
    )
    def get_time(self, args, raw_data):
        """Get the current time"""
        now = datetime.now()
        formatted_time = now.strftime("%H:%M:%S")
        return SwaigFunctionResult(f"The current time is {formatted_time}")
    
    @AgentBase.tool(
        name="store_preference",
        description="Store a user preference",
        parameters={
            "key": {"type": "string", "description": "Preference name"},
            "value": {"type": "string", "description": "Preference value"}
        }
    )
    def store_preference(self, args, raw_data):
        """Store a user preference in state"""
        key = args.get("key", "")
        value = args.get("value", "")
        call_id = raw_data.get("call_id")
        
        if not call_id:
            return SwaigFunctionResult("Cannot store preference - no call ID")
            
        # Get current state
        state = self.get_state(call_id) or {}
        
        # Create preferences dictionary if it doesn't exist
        if "preferences" not in state:
            state["preferences"] = {}
            
        # Store the preference
        state["preferences"][key] = value
        
        # Update state
        self.update_state(call_id, state)
        
        return SwaigFunctionResult(f"I've remembered that your {key} is {value}.")
    
    @AgentBase.tool(
        name="get_preferences",
        description="Retrieve user preferences",
        parameters={}
    )
    def get_preferences(self, args, raw_data):
        """Get all stored user preferences"""
        call_id = raw_data.get("call_id")
        
        if not call_id:
            return SwaigFunctionResult("No preferences found - no call ID")
            
        # Get current state
        state = self.get_state(call_id) or {}
        
        # Get preferences or empty dict
        preferences = state.get("preferences", {})
        
        if not preferences:
            return SwaigFunctionResult("You haven't shared any preferences with me yet.")
            
        # Format preferences as a list
        preference_list = [f"{k}: {v}" for k, v in preferences.items()]
        preferences_text = "\n".join(preference_list)
        
        return SwaigFunctionResult(f"Your preferences:\n{preferences_text}")
    
    # These methods are automatically registered by enable_state_tracking=True,
    # so we just provide the implementations without the @AgentBase.tool decorators
    def startup_hook(self, args, raw_data):
        """
        Initialize call state when a new conversation starts
        
        This is called automatically by the SignalWire AI when a conversation begins.
        It initializes the interaction counter in the state. The call_id is provided
        in raw_data.
        
        Args:
            args: Empty arguments dictionary
            raw_data: Raw request data containing call_id
            
        Returns:
            SwaigFunctionResult with success message
        """
        call_id = raw_data.get("call_id")
        if not call_id:
            return SwaigFunctionResult("No call ID provided")
        
        # Initialize state
        state = self.get_state(call_id) or {}
        state["interaction_count"] = 0
        self.update_state(call_id, state)
        
        print(f"Call {call_id} started at {datetime.now()}")
        return SwaigFunctionResult("Call initialized successfully")
    
    def hangup_hook(self, args, raw_data):
        """
        Cleanup and log when a call ends
        
        This is called automatically by the SignalWire AI when a conversation ends.
        It logs the total number of interactions that occurred. The call_id is
        provided in raw_data.
        
        Args:
            args: Empty arguments dictionary
            raw_data: Raw request data containing call_id
            
        Returns:
            SwaigFunctionResult with success message
        """
        call_id = raw_data.get("call_id")
        if not call_id:
            return SwaigFunctionResult("No call ID provided")
        
        # Log call end
        state = self.get_state(call_id) or {}
        interactions = state.get("interaction_count", 0)
        
        print(f"Call {call_id} ended at {datetime.now()}")
        print(f"Total interactions: {interactions}")
        
        return SwaigFunctionResult("Call ended successfully")
    
    def on_function_call(self, name, args, raw_data=None):
        """
        Override the function call handler to provide custom handling
        
        This is usually not necessary since the handlers now receive both
        args and raw_data directly, but shown here as an example.
        """
        # We can add custom logic before/after calling the function
        print(f"Function call: {name} with args: {args}")
        
        # Let the parent class handle the actual function execution
        result = super().on_function_call(name, args, raw_data)
        
        # We could modify the result here if needed
        
        return result
    
    def _process_request_data(self, call_id, data):
        """
        Process incoming request data from POST to main endpoint
        
        This method is called when data is received on the main endpoint for an
        active call. It updates the state with the new data and increments the
        interaction count.
        
        Args:
            call_id: Call ID from the request
            data: Request data dictionary
        """
        # Call parent implementation first
        super()._process_request_data(call_id, data)
        
        # Get the current state
        state = self.get_state(call_id) or {}
        
        # Only process further if the call is active
        if not state.get("active", False):
            print(f"Received data for inactive call {call_id}, saving but not processing")
            return
        
        # Increment interaction count for active calls
        state["interaction_count"] = state.get("interaction_count", 0) + 1
        
        # Extract any messages from the request
        if "message" in data:
            messages = state.setdefault("messages", [])
            messages.append({
                "timestamp": datetime.now().isoformat(),
                "content": data["message"]
            })
        
        # Update state
        self.update_state(call_id, state)


if __name__ == "__main__":
    # Create and start the agent
    agent = StatefulAgent()
    print("Starting the stateful agent. Press Ctrl+C to stop.")
    print(f"Agent is accessible at: http://localhost:3000/stateful")
    print("----------------------------------------------------------------")
    print("To test state management, use:")
    print("curl -X POST -H 'Content-Type: application/json' -d '{\"message\": \"Remember my name is John\", \"call_id\": \"test-call-123\"}' http://localhost:3000/stateful")
    print("----------------------------------------------------------------")
    
    # Run periodic cleanup
    import threading
    def cleanup_task():
        count = agent.cleanup_expired_state()
        if count > 0:
            print(f"Cleaned up {count} expired state records")
        # Schedule next run (every hour)
        threading.Timer(3600, cleanup_task).start()
    
    # Start cleanup task
    cleanup_task()
    
    try:
        agent.serve()
    except KeyboardInterrupt:
        print("\nStopping the agent.")
        agent.stop() 