# SignalWire AI Agent SDK

A Python SDK for creating, hosting, and securing SignalWire AI agents as microservices with minimal boilerplate.

## Features

- **Self-Contained Agents**: Each agent is both a web app and an AI persona
- **Prompt Object Model**: Structured prompt composition using POM
- **SWAIG Integration**: Easily define and handle AI tools/functions
- **Security Built-In**: Session management, per-call tokens, and basic auth
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

When these variables are set, they will be used for all agents instead of generating random credentials.

## Documentation

See the [full documentation](https://docs.signalwire.com/ai-agents) for details on:

- Creating custom agents
- Using prefab agents
- SWAIG function definitions
- Security model
- Deployment options
- Multi-agent hosting

## License

MIT
