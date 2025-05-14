# SignalWire AI Agent SDK

A Python SDK for creating, hosting, and securing SignalWire AI agents as microservices with minimal boilerplate.

## Features

- **Self-Contained Agents**: Each agent is both a web app and an AI persona
- **Prompt Object Model**: Structured prompt composition using POM
- **SWAIG Integration**: Easily define and handle AI tools/functions
- **Security Built-In**: Session management, per-call tokens, and basic auth
- **State Management**: Persistent conversation state with lifecycle hooks
- **Prefab Archetypes**: Ready-to-use agent types for common scenarios
- **Multi-Agent Support**: Host multiple agents on a single server

## Installation

```bash
pip install signalwire-agents
```

## Quick Start

```python
from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult

class SimpleAgent(AgentBase):
    def __init__(self):
        super().__init__(name="simple", route="/simple")
        
        # Configure the agent's personality
        self.prompt_add_section("Personality", body="You are a helpful assistant.")
        self.prompt_add_section("Goal", body="Help users with basic questions.")
        self.prompt_add_section("Instructions", bullets=["Be concise and clear."])
        
        # Alternative using convenience methods:
        # self.setPersonality("You are a helpful assistant.")
        # self.setGoal("Help users with basic questions.")
        # self.setInstructions(["Be concise and clear."])
    
    @AgentBase.tool(
        name="get_time", 
        description="Get the current time",
        parameters={}
    )
    def get_time(self, args, raw_data):
        from datetime import datetime
        now = datetime.now().strftime("%H:%M:%S")
        return SwaigFunctionResult(f"The current time is {now}")

# Run the agent
if __name__ == "__main__":
    agent = SimpleAgent()
    agent.serve(host="0.0.0.0", port=8000)
```

## Using State Management

```python
from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult
from signalwire_agents.core.state import FileStateManager

class StatefulAgent(AgentBase):
    def __init__(self):
        # Configure state management
        state_manager = FileStateManager(storage_dir="./state_data")
        
        super().__init__(
            name="stateful", 
            route="/stateful",
            enable_state_tracking=True,  # Enable state tracking
            state_manager=state_manager  # Use custom state manager
        )
    
    # SWAIG function for accessing and updating state
    @AgentBase.tool(
        name="save_preference",
        description="Save a user preference",
        parameters={
            "preference_name": {
                "type": "string",
                "description": "Name of the preference to save"
            },
            "preference_value": {
                "type": "string",
                "description": "Value of the preference"
            }
        }
    )
    def save_preference(self, args, raw_data):
        # Get the call ID from the raw data
        call_id = raw_data.get("call_id")
        
        if call_id:
            # Get current state or empty dict if none exists
            state = self.get_state(call_id) or {}
            
            # Update the state
            preferences = state.get("preferences", {})
            preferences[args.get("preference_name")] = args.get("preference_value")
            state["preferences"] = preferences
            
            # Save the updated state
            self.update_state(call_id, state)
            
            return SwaigFunctionResult("Preference saved successfully")
        else:
            return SwaigFunctionResult("Could not save preference: No call ID")
```

## Using Prefab Agents

```python
from signalwire_agents.prefabs import InfoGathererAgent

agent = InfoGathererAgent(
    fields=[
        {"name": "full_name", "prompt": "What is your full name?"},
        {"name": "reason", "prompt": "How can I help you today?"}
    ],
    confirmation_template="Thanks {full_name}, I'll help you with {reason}.",
    name="info-gatherer",
    route="/info-gatherer"
)

agent.serve(host="0.0.0.0", port=8000)
```

Available prefabs include:
- `InfoGathererAgent`: Collects structured information from users
- `FAQBotAgent`: Answers questions based on a knowledge base
- `ConciergeAgent`: Routes users to specialized agents
- `SurveyAgent`: Conducts structured surveys with questions and rating scales

## Configuration

### Environment Variables

The SDK supports the following environment variables:

- `SWML_BASIC_AUTH_USER`: Username for basic auth (default: auto-generated)
- `SWML_BASIC_AUTH_PASSWORD`: Password for basic auth (default: auto-generated)
- `SWML_PROXY_URL_BASE`: Base URL to use when behind a reverse proxy, used for constructing webhook URLs
- `SWML_SSL_ENABLED`: Enable HTTPS/SSL support (values: "true", "1", "yes")
- `SWML_SSL_CERT_PATH`: Path to SSL certificate file
- `SWML_SSL_KEY_PATH`: Path to SSL private key file
- `SWML_DOMAIN`: Domain name for SSL certificate and external URLs

When the auth environment variables are set, they will be used for all agents instead of generating random credentials. The proxy URL base is useful when your service is behind a reverse proxy or when you need external services to access your webhooks.

To enable HTTPS directly (without a reverse proxy), set `SWML_SSL_ENABLED` to "true", provide valid paths to your certificate and key files, and specify your domain name.

## Documentation

For more detailed documentation, see:

- [Agent Guide](docs/agent_guide.md) - Comprehensive guide on creating and customizing agents
- [Architecture](docs/architecture.md) - Architecture overview and core concepts
- [SWML Service Guide](docs/swml_service_guide.md) - Guide to the underlying SWML service

## License

MIT
