# SignalWire AI Agent SDK

A Python SDK for creating, hosting, and securing SignalWire AI agents as microservices with minimal boilerplate.

## Features

- **Self-Contained Agents**: Each agent is both a web app and an AI persona
- **Prompt Object Model**: Structured prompt composition using POM
- **SWAIG Integration**: Easily define and handle AI tools/functions
- **Dynamic Configuration**: Configure agents per-request for multi-tenant apps and personalization
- **Custom Routing**: Dynamic request handling for different paths and content
- **SIP Integration**: Route SIP calls to agents based on SIP usernames
- **Security Built-In**: Session management, function-specific security tokens, and basic auth
- **State Management**: Persistent conversation state with automatic tracking
- **Prefab Archetypes**: Ready-to-use agent types for common scenarios
- **Multi-Agent Support**: Host multiple agents on a single server
- **Modular Skills System**: Add capabilities to agents with simple one-liner calls

## Skills System

The SignalWire Agents SDK includes a powerful modular skills system that allows you to add complex capabilities to your agents with simple one-liner calls:

```python
from signalwire_agents import AgentBase

# Create an agent
agent = AgentBase("My Assistant", route="/assistant")

# Add skills with one-liners
agent.add_skill("web_search")   # Web search capability
agent.add_skill("datetime")     # Current date/time info  
agent.add_skill("math")         # Mathematical calculations

# Configure skills with parameters
agent.add_skill("web_search", {
    "num_results": 3,  # Get 3 search results
    "delay": 0.5       # Small delay between requests
})

# Advanced: Customize SWAIG function properties
agent.add_skill("math", {
    "swaig_fields": {
        "secure": False,  # Override security settings
        "fillers": {"en-US": ["Calculating..."]}  # Custom filler phrases
    }
})

agent.serve()
```

### Available Built-in Skills

- **web_search**: Google Custom Search API integration with web scraping
- **datetime**: Current date and time with timezone support
- **math**: Safe mathematical expression evaluation

### Benefits

- **One-liner integration**: `agent.add_skill("skill_name")`
- **Configurable parameters**: `agent.add_skill("skill_name", {"param": "value"})`
- **Automatic discovery**: Skills are automatically found from the skills directory
- **Dependency validation**: Clear error messages for missing requirements
- **Modular architecture**: Skills are self-contained and reusable

For detailed documentation, see [Skills System README](docs/SKILLS_SYSTEM_README.md).

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
        
        # When enable_state_tracking=True, startup_hook and hangup_hook
        # are automatically registered to track session lifecycle
    
    # Custom tool for accessing and updating state
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
- `ReceptionistAgent`: Greets callers and transfers them to appropriate departments

## Dynamic Agent Configuration

Configure agents dynamically based on request parameters for multi-tenant applications, A/B testing, and personalization.

### Static vs Dynamic Configuration

- **Static**: Agent configured once at startup (traditional approach)
- **Dynamic**: Agent configured fresh for each request based on parameters

### Basic Example

```python
from signalwire_agents import AgentBase

class DynamicAgent(AgentBase):
    def __init__(self):
        super().__init__(name="dynamic-agent", route="/dynamic")
        
        # Set up dynamic configuration callback
        self.set_dynamic_config_callback(self.configure_per_request)
    
    def configure_per_request(self, query_params, body_params, headers, agent):
        """Configure agent based on request parameters"""
        
        # Extract parameters from request
        tier = query_params.get('tier', 'standard')
        language = query_params.get('language', 'en')
        customer_id = query_params.get('customer_id')
        
        # Configure voice and language
        if language == 'es':
            agent.add_language("Spanish", "es-ES", "rime.spore:mistv2")
        else:
            agent.add_language("English", "en-US", "rime.spore:mistv2")
        
        # Configure based on service tier
        if tier == 'premium':
            agent.set_params({"end_of_speech_timeout": 300})  # Faster response
            agent.prompt_add_section("Service Level", "You provide premium support.")
        else:
            agent.set_params({"end_of_speech_timeout": 500})  # Standard response
            agent.prompt_add_section("Service Level", "You provide standard support.")
        
        # Personalize with customer data
        global_data = {"tier": tier, "language": language}
        if customer_id:
            global_data["customer_id"] = customer_id
        agent.set_global_data(global_data)

# Usage examples:
# curl "http://localhost:3000/dynamic?tier=premium&language=es&customer_id=123"
# curl "http://localhost:3000/dynamic?tier=standard&language=en"
```

### Use Cases

- **Multi-tenant SaaS**: Different configurations per customer/organization
- **A/B Testing**: Test different agent behaviors with different user groups
- **Personalization**: Customize voice, prompts, and behavior per user
- **Localization**: Language and cultural adaptation based on user location
- **Dynamic Pricing**: Adjust features and capabilities based on subscription tiers

The `EphemeralAgentConfig` object provides all the same familiar methods as `AgentBase` (like `add_language()`, `prompt_add_section()`, `set_global_data()`) but applies them per-request instead of at startup.

For detailed documentation and advanced examples, see the [Agent Guide](docs/agent_guide.md#dynamic-agent-configuration).

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
- `SWML_SCHEMA_PATH`: Optional path to override the location of the schema.json file

When the auth environment variables are set, they will be used for all agents instead of generating random credentials. The proxy URL base is useful when your service is behind a reverse proxy or when you need external services to access your webhooks.

To enable HTTPS directly (without a reverse proxy), set `SWML_SSL_ENABLED` to "true", provide valid paths to your certificate and key files, and specify your domain name.

## Documentation

The package includes comprehensive documentation in the `docs/` directory:

- [Agent Guide](docs/agent_guide.md) - Detailed guide to creating and customizing agents, including dynamic configuration
- [Architecture](docs/architecture.md) - Overview of the SDK architecture and core concepts
- [SWML Service Guide](docs/swml_service_guide.md) - Guide to the underlying SWML service

These documents provide in-depth explanations of the features, APIs, and usage patterns.

## License

MIT
