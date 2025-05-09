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

### declarative_agent.py

Demonstrates the declarative approach to building agents using the PROMPT_SECTIONS class attribute:
- Defining the entire prompt structure declaratively instead of using method calls
- Two approaches: dictionary-based sections and direct POM list format
- Viewing the rendered prompt at runtime

To run:

```bash
python declarative_agent.py
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