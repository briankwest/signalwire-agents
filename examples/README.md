# SignalWire AI Agent SDK Examples

This directory contains examples of how to use the SignalWire AI Agent SDK to create and deploy AI agents.

## Setup

To run these examples, you'll need to:

1. Install the package from the parent directory:

```bash
# From the parent directory (signalwire-agents)
pip install -e .
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Make sure you have the `signalwire-pom` package installed:

```bash
pip install signalwire-pom
```

## Available Examples

### web_search_agent.py

An intelligent web search agent that can search the internet for real-time information using Google Custom Search API. This example demonstrates:
- Integration with external APIs (Google Custom Search)
- Web scraping capabilities with BeautifulSoup
- Environment variable configuration for API credentials
- SWAIG tools with parameters (query and number of results)
- Error handling and content formatting for AI responses

**Required Setup:**
1. Get a Google Custom Search API key from [Google Cloud Console](https://console.developers.google.com/)
2. Create a Custom Search Engine at [Google CSE](https://cse.google.com/cse/)
3. Set environment variables:

```bash
export GOOGLE_SEARCH_API_KEY="your_api_key_here"
export GOOGLE_SEARCH_ENGINE_ID="your_search_engine_id_here"
```

Or use the setup script:

```bash
./setup_web_search_agent.sh
```

To run:

```bash
python web_search_agent.py
```

The agent can respond to queries like:
- "Search for the latest AI news"
- "Find information about Python programming"
- "Look up reviews of electric cars"

### simple_agent.py

A simple agent that demonstrates the basic functionality of the SDK, including:
- Creating a custom agent by subclassing `AgentBase`
- Building a prompt using POM
- Defining SWAIG tools with the `@tool` decorator
- Handling conversation summaries

To run:

```bash
python simple_agent.py
```

### stateful_agent.py

Demonstrates how to use the state management capabilities of the SDK, including:
- Enabling state tracking with `enable_state_tracking=True`
- Using the built-in lifecycle hooks (`startup_hook` and `hangup_hook`)
- Storing and retrieving data in the conversation state
- Creating custom SWAIG tools that interact with the state

To run:

```bash
python stateful_agent.py
```

### declarative_agent.py

Demonstrates the declarative approach to building agents using the PROMPT_SECTIONS class attribute:
- Defining the entire prompt structure declaratively instead of using method calls
- Two approaches: dictionary-based sections and direct POM list format
- Viewing the rendered prompt at runtime

To run:

```bash
python declarative_agent.py
```

### external_webhook_weather_agent.py

Demonstrates how to create SWAIG functions that use external webhook URLs instead of local handlers:
- Defining external webhook functions with `webhook_url` parameter
- Mixing local and external webhook functions in the same agent
- How SignalWire calls external services directly for function execution
- Testing external webhook functions with the CLI tool

To run:

```bash
python external_webhook_weather_agent.py
```

**Key Features:**
- `getWeather` function uses an external webhook URL (never processed locally)
- `getHelp` function uses traditional local processing
- `testBrokenWebhook` function demonstrates error handling for unreachable external services

**Testing with CLI:**
```bash
# Test external webhook function
swaig-test examples/external_webhook_weather_agent.py --verbose --exec getWeather --location "New York"

# Test local function
swaig-test examples/external_webhook_weather_agent.py --exec getHelp

# List all functions with their types
swaig-test examples/external_webhook_weather_agent.py --list-tools
```

### multi_agent_server.py

Shows how to use the `AgentServer` to host multiple agents in a single server, including:
- Creating custom agents using the `InfoGathererAgent` prefab
- Customizing prefab agents with additional tools
- Registering multiple agents with a single server
- Using structured data formats for summaries

To run:

```bash
python multi_agent_server.py
```

## Running with Environment Variables

You can set basic auth credentials using environment variables:

```bash
# Set auth credentials
export SWML_BASIC_AUTH_USER=myuser
export SWML_BASIC_AUTH_PASSWORD=mypassword

# Run any example with predefined credentials
python simple_agent.py
```

This is useful for:
- Production deployments with fixed credentials
- CI/CD pipelines
- Testing with API tools that support basic auth

## Testing the Agents

Once an agent is running, you can:

1. Make a GET request to the agent's URL with basic auth to get the SWML:

```bash
curl -u "username:password" http://localhost:3000/simple
```

2. In a real SignalWire setup, configure a phone number to point to the agent's URL with the basic auth credentials.

3. For testing purposes, you can POST to the agent's tools directly:

```bash
curl -X POST -u "username:password" http://localhost:3000/simple/tools/get_time -H "Content-Type: application/json" -d '{}'
```

## SIP Routing

The examples demonstrate SIP routing capabilities:

### Individual Agent Routing (simple_agent.py)

```python
# Enable SIP routing for this agent with auto_map=True
agent.enable_sip_routing(auto_map=True)

# Register additional SIP usernames for this agent
agent.register_sip_username("simple_agent")
agent.register_sip_username("assistant")
```

### Multi-Agent Routing (multi_agent_server.py)

```python
# Set up SIP routing on the /sip endpoint
server.setup_sip_routing(route="/sip", auto_map=True)

# Register additional SIP username mappings
server.register_sip_username("register", "/register")  # register@domain → registration agent
server.register_sip_username("signup", "/register")    # signup@domain → registration agent
server.register_sip_username("help", "/support")       # help@domain → support agent
```

When using SIP routing, you can reach the agents via SIP addresses like:
- `simple@your-domain` (auto-mapped from agent name)
- `simple_agent@your-domain` (explicitly registered)
- `assistant@your-domain` (explicitly registered) 