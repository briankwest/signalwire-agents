#!/usr/bin/env python3
"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

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
        #------------------------------------------------------------------------
        # STATE MANAGER CONFIGURATION
        # Set up custom state persistence using FileStateManager
        #------------------------------------------------------------------------
        
        # Initialize with custom state manager
        # FileStateManager stores state data as JSON files in the specified directory
        # expiry_days parameter sets how long state files are kept before automatic cleanup
        state_manager = FileStateManager(
            storage_dir="./state_data",  # Directory where state files will be stored
            expiry_days=1.0              # State files older than 1 day will be deleted during cleanup
        )
        
        # Initialize the agent
        # When enable_state_tracking=True, the system will automatically:
        # 1. Register startup_hook and hangup_hook as SWAIG functions
        # 2. Add call_id to all function calls
        # 3. Track conversation lifecycle
        super().__init__(
            name="stateful",              # Agent identifier 
            route="/stateful",            # HTTP endpoint path
            host="0.0.0.0",               # Bind to all interfaces
            port=3000,                    # Listen on port 3000
            state_manager=state_manager,  # Use our custom state manager
            enable_state_tracking=True    # Enable automatic state lifecycle management
        )
        
        #------------------------------------------------------------------------
        # PROMPT CONFIGURATION
        # Configure the AI to understand stateful capabilities
        #------------------------------------------------------------------------
        
        # Configure AI prompt structure using AgentBase methods
        # This configures the AI to be aware of its ability to remember context
        self.prompt_add_section("Personality", body="You are a helpful assistant that remembers previous interactions.")
        self.prompt_add_section("Goal", body="Help users with their questions and remember context from the conversation.")
        self.prompt_add_section("Instructions", bullets=[
            "Keep track of user's preferences and previous questions.",
            "Use the get_time function when asked about the current time.",
            "Use the store_preference function to remember user preferences.",
            "Use the get_preferences function to recall user preferences."
        ])
        
        # Set up post-prompt for conversation summarization
        # This defines what kind of summary the AI should generate after the conversation
        self.set_post_prompt("""
        Return a JSON summary of the conversation:
        {
            "topic": "MAIN_TOPIC",
            "preferences_mentioned": ["any", "preferences", "mentioned"],
            "questions_asked": ["list", "of", "questions"]
        }
        """)
    
    #------------------------------------------------------------------------
    # SWAIG FUNCTION DEFINITIONS
    # Tools that the AI can use during conversations
    #------------------------------------------------------------------------
    
    @AgentBase.tool(
        name="get_time",
        description="Get the current time",
        parameters={}  # No parameters needed for this function
    )
    def get_time(self, args, raw_data):
        """
        Get the current time
        
        A simple utility function that doesn't use state but shows how
        to provide real-time information to the AI.
        
        Args:
            args: Empty dictionary (no parameters needed)
            raw_data: Raw request data including call_id
            
        Returns:
            SwaigFunctionResult with the current time
        """
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
        """
        Store a user preference in state
        
        This function demonstrates how to update conversation state by storing
        user preferences in a structured format. The state is persisted between
        interactions using the configured state manager.
        
        Args:
            args: Dictionary containing "key" and "value" parameters
            raw_data: Raw request data including call_id
            
        Returns:
            SwaigFunctionResult with confirmation message
        """
        # Extract parameters from args
        key = args.get("key", "")
        value = args.get("value", "")
        
        # Get call_id from raw_data (automatically added by enable_state_tracking=True)
        call_id = raw_data.get("call_id")
        
        # Safety check - we can't update state without a call_id
        if not call_id:
            return SwaigFunctionResult("Cannot store preference - no call ID")
            
        # Get current state (or empty dict if this is first interaction)
        state = self.get_state(call_id) or {}
        
        # Create preferences dictionary if it doesn't exist in state
        # This uses dict.setdefault() as an alternative to the if-check approach
        preferences = state.setdefault("preferences", {})
            
        # Store the preference in the state
        preferences[key] = value
        
        # Update state in the persistence layer
        # This writes to the state file using the state manager
        self.update_state(call_id, state)
        
        # Return a human-friendly confirmation
        return SwaigFunctionResult(f"I've remembered that your {key} is {value}.")
    
    @AgentBase.tool(
        name="get_preferences",
        description="Retrieve user preferences",
        parameters={}  # No parameters needed
    )
    def get_preferences(self, args, raw_data):
        """
        Get all stored user preferences
        
        This function demonstrates how to retrieve data from conversation state.
        It reads all preferences previously stored with store_preference and
        formats them for the user.
        
        Args:
            args: Empty dictionary (no parameters needed)
            raw_data: Raw request data including call_id
            
        Returns:
            SwaigFunctionResult with formatted list of preferences
        """
        # Get call_id from raw_data
        call_id = raw_data.get("call_id")
        
        # Safety check - we can't retrieve state without a call_id
        if not call_id:
            return SwaigFunctionResult("No preferences found - no call ID")
            
        # Get current state
        state = self.get_state(call_id) or {}
        
        # Get preferences or empty dict if none exist
        preferences = state.get("preferences", {})
        
        # Handle the case where no preferences have been stored
        if not preferences:
            return SwaigFunctionResult("You haven't shared any preferences with me yet.")
            
        # Format preferences as a list for readability
        # Creates a string like "color: blue\nfood: pizza"
        preference_list = [f"{k}: {v}" for k, v in preferences.items()]
        preferences_text = "\n".join(preference_list)
        
        # Return the formatted preferences
        return SwaigFunctionResult(f"Your preferences:\n{preferences_text}")
    
    #------------------------------------------------------------------------
    # STATE LIFECYCLE HOOKS
    # These are automatically registered when enable_state_tracking=True
    #------------------------------------------------------------------------
    
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
        # Get call_id from raw_data
        call_id = raw_data.get("call_id")
        if not call_id:
            return SwaigFunctionResult("No call ID provided")
        
        # Initialize state with basic tracking information
        # We set interaction_count to 0 and will increment it with each message
        state = self.get_state(call_id) or {}
        state["interaction_count"] = 0
        state["active"] = True  # Mark the call as active
        state["start_time"] = datetime.now().isoformat()  # Record start time
        self.update_state(call_id, state)
        
        print(f"Call {call_id} started at {datetime.now()}")
        return SwaigFunctionResult("Call initialized successfully")
    
    def hangup_hook(self, args, raw_data):
        """
        Cleanup and log when a call ends
        
        This is called automatically by the SignalWire AI when a conversation ends.
        It logs the total number of interactions that occurred and marks the
        call as inactive in the state. The call_id is provided in raw_data.
        
        Args:
            args: Empty arguments dictionary
            raw_data: Raw request data containing call_id
            
        Returns:
            SwaigFunctionResult with success message
        """
        # Get call_id from raw_data
        call_id = raw_data.get("call_id")
        if not call_id:
            return SwaigFunctionResult("No call ID provided")
        
        # Get the current state
        state = self.get_state(call_id) or {}
        
        # Mark the call as inactive
        state["active"] = False
        state["end_time"] = datetime.now().isoformat()  # Record end time
        
        # Calculate session duration if we have a start time
        if "start_time" in state:
            try:
                start = datetime.fromisoformat(state["start_time"])
                end = datetime.fromisoformat(state["end_time"])
                duration = (end - start).total_seconds()
                state["duration_seconds"] = duration
            except Exception as e:
                print(f"Error calculating duration: {e}")
        
        # Update state with final information
        self.update_state(call_id, state)
        
        # Log call end with statistics
        interactions = state.get("interaction_count", 0)
        print(f"Call {call_id} ended at {datetime.now()}")
        print(f"Total interactions: {interactions}")
        
        return SwaigFunctionResult("Call ended successfully")
    
    #------------------------------------------------------------------------
    # ADVANCED CUSTOMIZATION
    # Override default methods to add custom behavior
    #------------------------------------------------------------------------
    
    def on_function_call(self, name, args, raw_data=None):
        """
        Override the function call handler to provide custom handling
        
        This demonstrates how to intercept and customize function execution.
        You can add logging, validation, or other processing before or after
        the actual function is executed.
        
        Args:
            name: The function name being called
            args: Arguments for the function
            raw_data: Raw request data including call_id
            
        Returns:
            The result from the function execution
        """
        # We can add custom logic before calling the function
        # This is useful for logging, validation, or preprocessing
        print(f"Function call: {name} with args: {args}")
        
        # Let the parent class handle the actual function execution
        # This ensures all the normal processing happens
        result = super().on_function_call(name, args, raw_data)
        
        # We could modify the result here if needed
        # For example, adding additional context or formatting
        
        return result
    
    def _process_request_data(self, call_id, data):
        """
        Process incoming request data from POST to main endpoint
        
        This method is called when data is received on the main endpoint for an
        active call. It updates the state with the new data and increments the
        interaction count.
        
        This is an internal method that's called automatically by the request
        handling system. We override it to add custom state-related processing.
        
        Args:
            call_id: Call ID from the request
            data: Request data dictionary
        """
        # Call parent implementation first to ensure standard processing
        # This handles the basic request processing logic
        super()._process_request_data(call_id, data)
        
        # Get the current state for this call
        state = self.get_state(call_id) or {}
        
        # Only process further if the call is active
        # This prevents processing data for completed calls
        if not state.get("active", False):
            print(f"Received data for inactive call {call_id}, saving but not processing")
            return
        
        # Increment interaction count for active calls
        # This tracks how many times the user has sent messages
        state["interaction_count"] = state.get("interaction_count", 0) + 1
        
        # Extract any messages from the request and add to history
        # This creates a transcript of the conversation
        if "message" in data:
            # Create or get the messages array in state
            messages = state.setdefault("messages", [])
            # Add the new message with timestamp
            messages.append({
                "timestamp": datetime.now().isoformat(),
                "content": data["message"]
            })
        
        # Update state with the new data
        self.update_state(call_id, state)


if __name__ == "__main__":
    #------------------------------------------------------------------------
    # AGENT INITIALIZATION AND STARTUP
    #------------------------------------------------------------------------
    
    # Create and start the agent
    agent = StatefulAgent()
    
    # Print startup information and usage instructions
    print("Starting the stateful agent. Press Ctrl+C to stop.")
    print(f"Agent is accessible at: http://localhost:3000/stateful")
    print("----------------------------------------------------------------")
    print("To test state management, use:")
    print("curl -X POST -H 'Content-Type: application/json' -d '{\"message\": \"Remember my name is John\", \"call_id\": \"test-call-123\"}' http://localhost:3000/stateful")
    print("----------------------------------------------------------------")
    
    #------------------------------------------------------------------------
    # STATE CLEANUP TASK
    # Periodically remove expired state files
    #------------------------------------------------------------------------
    
    # Run periodic cleanup using a background thread
    import threading
    
    def cleanup_task():
        """
        Periodic task to clean up expired state files
        
        This function runs every hour in a background thread and calls
        cleanup_expired_state() to remove state files older than the
        expiry_days setting in the FileStateManager.
        """
        # Run the cleanup and get number of files removed
        count = agent.cleanup_expired_state()
        if count > 0:
            print(f"Cleaned up {count} expired state records")
            
        # Schedule next run (every hour = 3600 seconds)
        threading.Timer(3600, cleanup_task).start()
    
    # Start cleanup task immediately
    cleanup_task()
    
    # Start the agent's HTTP server
    try:
        print("Note: Works in any deployment mode (server/CGI/Lambda)")
        agent.run()
    except KeyboardInterrupt:
        print("\nStopping the agent.")
        agent.stop() 