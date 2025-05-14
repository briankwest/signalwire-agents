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
        self.set_personality("You are a helpful assistant.")
        self.set_goal("Help users with basic questions.")
        self.add_instruction("Be concise and clear.")
    
    @AgentBase.tool(name="get_time", parameters={})
    def get_time(self):
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
    
    # These methods are automatically registered when enable_state_tracking=True
    def startup_hook(self, args, raw_data):
        """Called when a conversation starts"""
        call_id = raw_data.get("call_id")
        state = self.get_state(call_id) or {}
        state["started_at"] = "2023-01-01T12:00:00Z"
        self.update_state(call_id, state)
        return "Call initialized"
        
    def hangup_hook(self, args, raw_data):
        """Called when a conversation ends"""
        call_id = raw_data.get("call_id")
        state = self.get_state(call_id)
        return "Call completed"
```

## Using Prefab Agents

```python
from signalwire_agents.prefabs import InfoGathererAgent

agent = InfoGathererAgent(
    fields=[
        {"name": "full_name", "prompt": "What is your full name?"},
        {"name": "reason", "prompt": "How can I help you today?"}
    ],
    confirmation_template="Thanks {full_name}, I'll help you with {reason}."
)

agent.serve(host="0.0.0.0", port=8000, route="/support")
```

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

See the [full documentation](https://docs.signalwire.com/ai-agents) for details on:

- Creating custom agents
- Using prefab agents
- SWAIG function definitions
- State management and persistence
- Security model
- Deployment options
- Multi-agent hosting

## License

MIT
