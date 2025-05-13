# SignalWire AI Agent Guide

## Table of Contents
- [Introduction](#introduction)
- [Architecture Overview](#architecture-overview)
- [Creating an Agent](#creating-an-agent)
- [Prompt Building](#prompt-building)
- [SWAIG Functions](#swaig-functions)
- [Multilingual Support](#multilingual-support)
- [Agent Configuration](#agent-configuration)
- [Advanced Features](#advanced-features)
- [API Reference](#api-reference)
- [Examples](#examples)

## Introduction

The `AgentBase` class provides the foundation for creating AI-powered agents using the SignalWire AI Agent SDK. It extends the `SWMLService` class, inheriting all its SWML document creation and serving capabilities, while adding AI-specific functionality.

Key features of `AgentBase` include:

- Structured prompt building with POM (Prompt Object Model)
- SWAIG function definitions for AI tool access
- Multilingual support
- Agent configuration (hint handling, pronunciation rules, etc.)
- State management for conversations

This guide explains how to create and customize your own AI agents, with examples based on the SDK's sample implementations.

## Architecture Overview

The Agent SDK architecture consists of several layers:

1. **SWMLService**: The base layer for SWML document creation and serving
2. **AgentBase**: Extends SWMLService with AI agent functionality
3. **Custom Agents**: Your specific agent implementations that extend AgentBase

Here's how these components relate to each other:

```
┌─────────────┐
│ Your Agent  │ (Extends AgentBase with your specific functionality)
└─────▲───────┘
      │
┌─────┴───────┐
│  AgentBase  │ (Adds AI functionality to SWMLService)
└─────▲───────┘
      │
┌─────┴───────┐
│ SWMLService │ (Provides SWML document creation and web service)
└─────────────┘
```

## Creating an Agent

To create an agent, extend the `AgentBase` class and define your agent's behavior:

```python
from signalwire_agents import AgentBase

class MyAgent(AgentBase):
    def __init__(self):
        super().__init__(
            name="my-agent",
            route="/agent",
            host="0.0.0.0",
            port=3000,
            use_pom=True  # Enable Prompt Object Model
        )
        
        # Define agent personality and behavior
        self.prompt_add_section("Personality", body="You are a helpful and friendly assistant.")
        self.prompt_add_section("Goal", body="Help users with their questions and tasks.")
        self.prompt_add_section("Instructions", bullets=[
            "Answer questions clearly and concisely",
            "If you don't know, say so",
            "Use the provided tools when appropriate"
        ])
        
        # Add a post-prompt for summary
        self.set_post_prompt("Please summarize the key points of this conversation.")
```

## Prompt Building

There are several ways to build prompts for your agent:

### 1. Using Prompt Sections (POM)

The Prompt Object Model (POM) provides a structured way to build prompts:

```python
# Add a section with just body text
self.prompt_add_section("Personality", body="You are a friendly assistant.")

# Add a section with bullet points
self.prompt_add_section("Instructions", bullets=[
    "Answer questions clearly",
    "Be helpful and polite",
    "Use functions when appropriate"
])

# Add a section with both body and bullets
self.prompt_add_section("Context", 
                       body="The user is calling about technical support.",
                       bullets=["They may need help with their account", 
                               "Check for existing tickets"])
```

### 2. Using Raw Text Prompts

For simpler agents, you can set the prompt directly as text:

```python
self.set_prompt("""
You are a helpful assistant. Your goal is to provide clear and concise information
to the user. Answer their questions to the best of your ability.
""")
```

### 3. Setting a Post-Prompt

The post-prompt is sent to the AI after the conversation for summary or analysis:

```python
self.set_post_prompt("""
Analyze the conversation and extract:
1. Main topics discussed
2. Action items or follow-ups needed
3. Whether the user's questions were answered satisfactorily
""")
```

## SWAIG Functions

SWAIG functions allow the AI agent to perform actions and access external systems. You define these functions using the `@AgentBase.tool` decorator:

```python
from signalwire_agents.core.function_result import SwaigFunctionResult

@AgentBase.tool(
    name="get_weather",
    description="Get the current weather for a location",
    parameters={
        "location": {
            "type": "string",
            "description": "The city or location to get weather for"
        }
    }
)
def get_weather(self, args, raw_data):
    # Extract the location parameter
    location = args.get("location", "Unknown location")
    
    # Here you would typically call a weather API
    # For this example, we'll return mock data
    weather_data = f"It's sunny and 72°F in {location}."
    
    # Return a SwaigFunctionResult
    return SwaigFunctionResult(weather_data)
```

### Function Parameters

The parameters for a SWAIG function are defined using JSON Schema:

```python
parameters={
    "parameter_name": {
        "type": "string", # Can be string, number, integer, boolean, array, object
        "description": "Description of the parameter",
        # Optional attributes:
        "enum": ["option1", "option2"],  # For enumerated values
        "minimum": 0,  # For numeric types
        "maximum": 100,  # For numeric types
        "pattern": "^[A-Z]+$"  # For string validation
    }
}
```

### Function Results

To return results from a SWAIG function, use the `SwaigFunctionResult` class:

```python
# Basic result with just text
return SwaigFunctionResult("Here's the result")

# Result with actions
return SwaigFunctionResult(
    "Here's the result", 
    actions=[
        # Action to say something
        {"say": "I found the information you requested."},
        
        # Action to play audio
        {"playback_bg": {"file": "https://example.com/music.mp3"}}
    ]
)
```

### Native Functions

The agent can use SignalWire's built-in functions:

```python
# Enable native functions
self.set_native_functions([
    "check_time",
    "wait_seconds"
])
```

### Function Includes

You can include functions from remote sources:

```python
# Include remote functions
self.add_function_include(
    url="https://api.example.com/functions",
    functions=["get_weather", "get_news"],
    meta_data={"api_key": "your-api-key"}
)
```

## Multilingual Support

Agents can support multiple languages:

```python
# Add English language
self.add_language(
    name="English",
    code="en-US",
    voice="en-US-Neural2-F",
    speech_fillers=["Let me think...", "One moment please..."],
    function_fillers=["I'm looking that up...", "Let me check that..."]
)

# Add Spanish language
self.add_language(
    name="Spanish",
    code="es",
    voice="elevenlabs.antonio:eleven_multilingual_v2",
    speech_fillers=["Un momento por favor...", "Estoy pensando..."]
)
```

### Voice Formats

There are different ways to specify voices:

```python
# Simple format
self.add_language(name="English", code="en-US", voice="en-US-Neural2-F")

# Explicit parameters with engine and model
self.add_language(
    name="British English",
    code="en-GB",
    voice="emma",
    engine="elevenlabs",
    model="eleven_turbo_v2"
)

# Combined string format
self.add_language(
    name="Spanish",
    code="es",
    voice="elevenlabs.antonio:eleven_multilingual_v2"
)
```

## Agent Configuration

### Adding Hints

Hints help the AI understand certain terms better:

```python
# Simple hints (list of words)
self.add_hints(["SignalWire", "SWML", "SWAIG"])

# Pattern hint with replacement
self.add_pattern_hint(
    hint="AI Agent", 
    pattern="AI\\s+Agent", 
    replace="A.I. Agent", 
    ignore_case=True
)
```

### Adding Pronunciation Rules

Pronunciation rules help the AI speak certain terms correctly:

```python
# Add pronunciation rule
self.add_pronunciation("API", "A P I", ignore_case=False)
self.add_pronunciation("SIP", "sip", ignore_case=True)
```

### Setting AI Parameters

Configure various AI behavior parameters:

```python
# Set AI parameters
self.set_params({
    "wait_for_user": False,
    "end_of_speech_timeout": 1000,
    "ai_volume": 5,
    "languages_enabled": True,
    "local_tz": "America/Los_Angeles"
})
```

### Setting Global Data

Provide global data for the AI to reference:

```python
# Set global data
self.set_global_data({
    "company_name": "SignalWire",
    "product": "AI Agent SDK",
    "supported_features": [
        "Voice AI",
        "Telephone integration",
        "SWAIG functions"
    ]
})
```

## Advanced Features

### State Management

Enable state tracking to persist information across interactions:

```python
# Enable state tracking in the constructor
super().__init__(
    name="stateful-agent",
    enable_state_tracking=True
)

# Access and update state
@AgentBase.tool(name="save_preference")
def save_preference(self, args, raw_data):
    # Get the call ID from the raw data
    call_id = raw_data.get("call_id")
    
    if call_id:
        # Get current state or empty dict if none exists
        state = self.get_state(call_id) or {}
        
        # Update the state
        preferences = state.get("preferences", {})
        preferences.update(args)
        state["preferences"] = preferences
        
        # Save the updated state
        self.update_state(call_id, state)
        
        return SwaigFunctionResult("Preferences saved")
    else:
        return SwaigFunctionResult("Could not save preferences: No call ID")
```

### Conversation Summary Handling

Process conversation summaries:

```python
def on_summary(self, summary, raw_data=None):
    """
    Handle the conversation summary
    
    Args:
        summary: The summary object or None if no summary was found
        raw_data: The complete raw POST data from the request
    """
    if summary:
        # Log the summary
        self.log.info("conversation_summary", summary=summary)
        
        # Save the summary to a database, send notifications, etc.
        # ...
```

## API Reference

### Constructor Parameters

- `name`: Agent name/identifier (required)
- `route`: HTTP route path (default: "/")
- `host`: Host to bind to (default: "0.0.0.0")
- `port`: Port to bind to (default: 3000)
- `basic_auth`: Optional (username, password) tuple
- `use_pom`: Whether to use POM for prompts (default: True)
- `enable_state_tracking`: Enable conversation state (default: False)
- `token_expiry_secs`: State token expiry time (default: 600)
- `auto_answer`: Auto-answer calls (default: True)
- `record_call`: Record calls (default: False)
- `state_manager`: Custom state manager (default: None)

### Prompt Methods

- `prompt_add_section(title, body=None, bullets=None)`
- `set_prompt(prompt_text)`
- `set_post_prompt(prompt_text)`

### SWAIG Methods

- `@AgentBase.tool(name, description, parameters={})`
- `set_native_functions(function_names)`
- `add_native_function(function_name)`
- `add_function_include(url, functions, meta_data=None)`

### Configuration Methods

- `add_hints(hints)`
- `add_pattern_hint(hint, pattern, replace, ignore_case=False)`
- `add_pronunciation(replace, with_text, ignore_case=False)`
- `add_language(name, code, voice, speech_fillers=None, function_fillers=None, engine=None, model=None)`
- `set_params(params_dict)`
- `set_global_data(data_dict)`

### State Methods

- `get_state(call_id)`
- `update_state(call_id, state)`
- `delete_state(call_id)`

## Examples

### Simple Question-Answering Agent

```python
from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult
from datetime import datetime

class SimpleAgent(AgentBase):
    def __init__(self):
        super().__init__(
            name="simple",
            route="/simple",
            use_pom=True
        )
        
        # Configure agent personality
        self.prompt_add_section("Personality", body="You are a friendly and helpful assistant.")
        self.prompt_add_section("Goal", body="Help users with basic tasks and answer questions.")
        self.prompt_add_section("Instructions", bullets=[
            "Be concise and direct in your responses.",
            "If you don't know something, say so clearly.",
            "Use the get_time function when asked about the current time."
        ])
        
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
```

### Multi-Language Customer Service Agent

```python
class CustomerServiceAgent(AgentBase):
    def __init__(self):
        super().__init__(
            name="customer-service",
            route="/support",
            use_pom=True
        )
        
        # Configure agent personality
        self.prompt_add_section("Personality", 
                               body="You are a helpful customer service representative for SignalWire.")
        self.prompt_add_section("Knowledge", 
                               body="You can answer questions about SignalWire products and services.")
        self.prompt_add_section("Instructions", bullets=[
            "Greet customers politely",
            "Answer questions about SignalWire products",
            "Use check_account_status when customer asks about their account",
            "Use create_support_ticket for unresolved issues"
        ])
        
        # Add language support
        self.add_language(
            name="English",
            code="en-US",
            voice="elevenlabs.josh",
            speech_fillers=["Let me check that for you...", "One moment please..."]
        )
        
        self.add_language(
            name="Spanish",
            code="es",
            voice="elevenlabs.antonio:eleven_multilingual_v2",
            speech_fillers=["Un momento por favor...", "Voy a verificar eso..."]
        )
        
        # Enable languages
        self.set_params({"languages_enabled": True})
        
        # Add company information
        self.set_global_data({
            "company_name": "SignalWire",
            "support_hours": "9am-5pm ET, Monday through Friday",
            "support_email": "support@signalwire.com"
        })
    
    @AgentBase.tool(
        name="check_account_status",
        description="Check the status of a customer's account",
        parameters={
            "account_id": {
                "type": "string",
                "description": "The customer's account ID"
            }
        }
    )
    def check_account_status(self, args, raw_data):
        account_id = args.get("account_id")
        # In a real implementation, this would query a database
        return SwaigFunctionResult(f"Account {account_id} is in good standing.")
    
    @AgentBase.tool(
        name="create_support_ticket",
        description="Create a support ticket for an unresolved issue",
        parameters={
            "issue": {
                "type": "string",
                "description": "Brief description of the issue"
            },
            "priority": {
                "type": "string",
                "description": "Ticket priority",
                "enum": ["low", "medium", "high", "critical"]
            }
        }
    )
    def create_support_ticket(self, args, raw_data):
        issue = args.get("issue", "")
        priority = args.get("priority", "medium")
        
        # Generate a ticket ID (in a real system, this would create a database entry)
        ticket_id = f"TICKET-{hash(issue) % 10000:04d}"
        
        return SwaigFunctionResult(
            f"Support ticket {ticket_id} has been created with {priority} priority. " +
            "A support representative will contact you shortly."
        )
```

For more examples, see the `examples` directory in the SignalWire AI Agent SDK repository. 