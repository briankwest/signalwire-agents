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
  - [State Management](#state-management)
  - [SIP Routing](#sip-routing)
  - [Custom Routing](#custom-routing)
- [Prefab Agents](#prefab-agents)
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

For convenience, the SDK also provides wrapper methods that some users may prefer:

```python
# Convenience methods
self.setPersonality("You are a friendly assistant.") 
self.setGoal("Help users with their questions.")
self.setInstructions([
    "Answer questions clearly",
    "Be helpful and polite"
])
```

These convenience methods call `prompt_add_section()` internally with the appropriate section titles.

### 2. Using Raw Text Prompts

For simpler agents, you can set the prompt directly as text:

```python
self.set_prompt_text("""
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
    },
    secure=True  # Optional, defaults to True
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

# Result with a single action
return SwaigFunctionResult("Here's the result with an action")
       .add_action("say", "I found the information you requested.")

# Result with multiple actions using add_actions
return SwaigFunctionResult("Multiple actions example")
       .add_actions([
           {"playback_bg": {"file": "https://example.com/music.mp3"}},
           {"set_global_data": {"key": "value"}}
       ])

# Alternative way to add multiple actions sequentially
return (
    SwaigFunctionResult("Sequential actions example")
    .add_action("say", "I found the information you requested.")
    .add_action("playback_bg", {"file": "https://example.com/music.mp3"})
)
```

In the examples above:
- `add_action(name, data)` adds a single action with the given name and data
- `add_actions(actions)` adds multiple actions at once from a list of action objects

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

### SWAIG Function Security

The SDK implements an automated security mechanism for SWAIG functions to ensure that only authorized calls can be made to your functions. This is important because SWAIG functions often provide access to sensitive operations or data.

#### Token-Based Security

By default, all SWAIG functions are marked as `secure=True`, which enables token-based security:

```python
@agent.tool(
    name="get_account_details",
    description="Get customer account details",
    parameters={"account_id": {"type": "string"}},
    secure=True  # This is the default, can be omitted
)
def get_account_details(self, args, raw_data):
    # Implementation
```

When a function is marked as secure:

1. The SDK automatically generates a secure token for each function when rendering the SWML document
2. The token is added to the function's URL as a query parameter: `?token=X2FiY2RlZmcuZ2V0X3RpbWUuMTcxOTMxNDI1...`
3. When the function is called, the token is validated before executing the function

These security tokens have important properties:
- **Completely stateless**: The system doesn't need to store tokens or track sessions
- **Self-contained**: Each token contains all information needed for validation
- **Function-specific**: A token for one function can't be used for another
- **Session-bound**: Tokens are tied to a specific call/session ID
- **Time-limited**: Tokens expire after a configurable duration (default: 60 minutes)
- **Cryptographically signed**: Tokens can't be tampered with or forged

This stateless design provides several benefits:
- **Server resilience**: Tokens remain valid even if the server restarts
- **No memory consumption**: No need to track sessions or store tokens in memory
- **High scalability**: Multiple servers can validate tokens without shared state
- **Load balancing**: Requests can be distributed across multiple servers freely

The token system secures both SWAIG functions and post-prompt endpoints:
- SWAIG function calls for interactive AI capabilities
- Post-prompt requests for receiving conversation summaries

You can disable token security for specific functions when appropriate:

```python
@agent.tool(
    name="get_public_information",
    description="Get public information that doesn't require security",
    parameters={},
    secure=False  # Disable token security for this function
)
def get_public_information(self, args, raw_data):
    # Implementation
```

#### Token Expiration

The default token expiration is 60 minutes (3600 seconds), but you can configure this when initializing your agent:

```python
agent = MyAgent(
    name="my_agent",
    token_expiry_secs=1800  # Set token expiration to 30 minutes
)
```

The expiration timer resets each time a function is successfully called, so as long as there is activity at least once within the expiration period, the tokens will remain valid throughout the entire conversation.

#### Custom Token Validation

You can override the default token validation by implementing your own `validate_tool_token` method in your custom agent class.

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
    voice="rime.spore:multilingual",
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
    voice="spore",
    engine="rime",
    model="multilingual"
)

# Combined string format
self.add_language(
    name="Spanish",
    code="es",
    voice="rime.spore:multilingual"
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
    enable_state_tracking=True,  # Automatically registers startup_hook and hangup_hook
    state_manager=FileStateManager(storage_dir="./state")  # Optional custom state manager
)

# Access and update state
@AgentBase.tool(
    name="save_preference",
    description="Save a user preference",
    parameters={
        "key": {
            "type": "string",
            "description": "The preference key"
        },
        "value": {
            "type": "string",
            "description": "The preference value"
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
        preferences[args.get("key")] = args.get("value")
        state["preferences"] = preferences
        
        # Save the updated state
        self.update_state(call_id, state)
        
        return SwaigFunctionResult("Preference saved")
    else:
        return SwaigFunctionResult("Could not save preference: No call ID")
```

### SIP Routing

SIP routing allows your agents to receive voice calls via SIP addresses. The SDK supports both individual agent-level routing and centralized server-level routing.

#### Individual Agent SIP Routing

Enable SIP routing on a single agent:

```python
# Enable SIP routing with automatic username mapping based on agent name
agent.enable_sip_routing(auto_map=True)

# Register additional SIP usernames for this agent
agent.register_sip_username("support_agent")
agent.register_sip_username("help_desk")
```

When `auto_map=True`, the agent automatically registers SIP usernames based on:
- The agent's name (e.g., `support@domain`)
- The agent's route path (e.g., `/support` becomes `support@domain`)
- Common variations (e.g., removing vowels for shorter dialing)

#### Server-Level SIP Routing (Multi-Agent)

For multi-agent setups, centralized routing is more efficient:

```python
# Create an AgentServer
server = AgentServer(host="0.0.0.0", port=3000)

# Register multiple agents
server.register(registration_agent)  # Route: /register
server.register(support_agent)       # Route: /support

# Set up central SIP routing
server.setup_sip_routing(route="/sip", auto_map=True)

# Register additional SIP username mappings
server.register_sip_username("signup", "/register")    # signup@domain → registration agent
server.register_sip_username("help", "/support")       # help@domain → support agent
```

With server-level routing:
- Each agent is reachable via its name (when `auto_map=True`)
- Additional SIP usernames can be mapped to specific agent routes
- All SIP routing is handled at a single endpoint (`/sip` by default)

#### How SIP Routing Works

1. A SIP call comes in with a username (e.g., `support@yourdomain`)
2. The SDK extracts the username part (`support`)
3. The system checks if this username is registered:
   - In individual routing: The current agent checks its own username list
   - In server routing: The server checks its central mapping table
4. If a match is found, the call is routed to the appropriate agent

### Custom Routing

You can dynamically handle requests to different paths using routing callbacks:

```python
# Enable custom routing in the constructor or anytime after initialization
self.register_routing_callback(self.handle_customer_route, path="/customer")
self.register_routing_callback(self.handle_product_route, path="/product")

# Define the routing handlers
def handle_customer_route(self, request, body):
    """
    Process customer-related requests
    
    Args:
        request: FastAPI Request object
        body: Parsed JSON body as dictionary
        
    Returns:
        Optional[str]: A URL to redirect to, or None to process normally
    """
    # Extract any relevant data
    customer_id = body.get("customer_id")
    
    # You can redirect to another agent/service if needed
    if customer_id and customer_id.startswith("vip-"):
        return f"/vip-handler/{customer_id}"
        
    # Or return None to process the request with on_swml_request
    return None
    
# Customize SWML based on the route in on_swml_request
def on_swml_request(self, request_data=None, callback_path=None):
    """
    Customize SWML based on the request and path
    
    Args:
        request_data: The request body data
        callback_path: The path that triggered the routing callback
    """
    if callback_path == "/customer":
        # Serve customer-specific content
        return {
            "sections": {
                "main": [
                    {"answer": {}},
                    {"play": {"url": "say:Welcome to customer service!"}}
                ]
            }
        }
    # Other path handling...
    return None
```

### Customizing SWML Requests

You can modify the SWML document based on request data by overriding the `on_swml_request` method:

```python
def on_swml_request(self, request_data=None, callback_path=None):
    """
    Customize the SWML document based on request data
    
    Args:
        request_data: The request data (body for POST or query params for GET)
        callback_path: The path that triggered the routing callback
        
    Returns:
        Optional dict with modifications to apply to the document
    """
    if request_data and "caller_type" in request_data:
        # Example: Return modifications to change the AI behavior based on caller type
        if request_data["caller_type"] == "vip":
            return {
                "sections": {
                    "main": [
                        # Keep the first verb (answer)
                        # Modify the AI verb parameters
                        {
                            "ai": {
                                "params": {
                                    "wait_for_user": False,
                                    "end_of_speech_timeout": 500  # More responsive
                                }
                            }
                        }
                    ]
                }
            }
            
    # You can also use the callback_path to serve different content based on the route
    if callback_path == "/customer":
        return {
            "sections": {
                "main": [
                    {"answer": {}},
                    {"play": {"url": "say:Welcome to our customer service line."}}
                ]
            }
        }
    
    # Return None to use the default document
    return None
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

### Custom Webhook URLs

You can override the default webhook URLs for SWAIG functions and post-prompt delivery:

```python
# In your agent initialization or setup code:

# Override the webhook URL for all SWAIG functions
agent.set_web_hook_url("https://external-service.example.com/handle-swaig")

# Override the post-prompt delivery URL
agent.set_post_prompt_url("https://analytics.example.com/conversation-summaries")

# These methods allow you to:
# 1. Send function calls to external services instead of handling them locally
# 2. Send conversation summaries to analytics services or other systems
# 3. Use special URLs with pre-configured authentication
```

### External Input Checking

The SDK provides a check-for-input endpoint that allows agents to check for new input from external systems:

```python
# Example client code that checks for new input
import requests
import json

def check_for_new_input(agent_url, conversation_id, auth):
    """
    Check if there's any new input for a conversation
    
    Args:
        agent_url: Base URL for the agent
        conversation_id: ID of the conversation to check
        auth: (username, password) tuple for basic auth
    
    Returns:
        New messages if any, None otherwise
    """
    url = f"{agent_url}/check_for_input"
    response = requests.post(
        url,
        json={"conversation_id": conversation_id},
        auth=auth
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get("new_input", False):
            return data.get("messages", [])
    
    return None
```

By default, the check_for_input endpoint returns an empty response. To implement custom behavior, override the `_handle_check_for_input_request` method in your agent:

```python
async def _handle_check_for_input_request(self, request):
    # First do basic authentication check
    if not self._check_basic_auth(request):
        return Response(
            content=json.dumps({"error": "Unauthorized"}),
            status_code=401,
            headers={"WWW-Authenticate": "Basic"},
            media_type="application/json"
        )
    
    # Get conversation_id from request
    conversation_id = None
    if request.method == "POST":
        body = await request.json()
        conversation_id = body.get("conversation_id")
    else:
        conversation_id = request.query_params.get("conversation_id")
    
    if not conversation_id:
        return Response(
            content=json.dumps({"error": "Missing conversation_id"}),
            status_code=400,
            media_type="application/json"
        )
    
    # Custom logic to check for new input
    # For example, checking a database or external API
    messages = self._get_new_messages(conversation_id)
    
    return {
        "status": "success",
        "conversation_id": conversation_id,
        "new_input": len(messages) > 0,
        "messages": messages
    }
```

This endpoint is useful for implementing asynchronous conversations where users might send messages through different channels that need to be incorporated into the agent conversation.

## Prefab Agents

Prefab agents are pre-configured agent implementations designed for specific use cases. They provide ready-to-use functionality with customization options, saving development time and ensuring consistent patterns.

### Built-in Prefabs

The SDK includes several built-in prefab agents:

#### InfoGathererAgent

Collects structured information from users:

```python
from signalwire_agents.prefabs import InfoGathererAgent

agent = InfoGathererAgent(
    fields=[
        {"name": "full_name", "prompt": "What is your full name?"},
        {"name": "email", "prompt": "What is your email address?", 
         "validation": r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"},
        {"name": "reason", "prompt": "How can I help you today?"}
    ],
    confirmation_template="Thanks {full_name}, I'll help you with {reason}. I'll send a confirmation to {email}.",
    name="info-gatherer",
    route="/info-gatherer"
)

agent.serve(host="0.0.0.0", port=8000)
```

#### FAQBotAgent

Answers questions based on a knowledge base:

```python
from signalwire_agents.prefabs import FAQBotAgent

agent = FAQBotAgent(
    knowledge_base_path="./docs",
    personality="I'm a product documentation assistant.",
    citation_style="inline",
    name="knowledge-base",
    route="/knowledge-base"
)

agent.serve(host="0.0.0.0", port=8000)
```

#### ConciergeAgent

Routes users to specialized agents:

```python
from signalwire_agents.prefabs import ConciergeAgent

agent = ConciergeAgent(
    routing_map={
        "technical_support": {
            "url": "http://tech-support-agent:8001",
            "criteria": ["error", "broken", "not working"]
        },
        "sales": {
            "url": "http://sales-agent:8002",
            "criteria": ["pricing", "purchase", "subscribe"]
        }
    },
    greeting="Welcome to SignalWire. How can I help you today?",
    name="concierge",
    route="/concierge"
)

agent.serve(host="0.0.0.0", port=8000)
```

#### SurveyAgent

Conducts structured surveys with different question types:

```python
from signalwire_agents.prefabs import SurveyAgent

agent = SurveyAgent(
    survey_name="Customer Satisfaction",
    introduction="We'd like to know about your recent experience with our product.",
    questions=[
        {
            "id": "satisfaction",
            "text": "How satisfied are you with our product?",
            "type": "rating",
            "scale": 5,
            "labels": {
                "1": "Very dissatisfied",
                "5": "Very satisfied"
            }
        },
        {
            "id": "feedback",
            "text": "Do you have any specific feedback about how we can improve?",
            "type": "text"
        }
    ],
    name="satisfaction-survey",
    route="/survey"
)

agent.serve(host="0.0.0.0", port=8000)
```

### Creating Your Own Prefabs

You can create your own prefab agents by extending `AgentBase` or any existing prefab. Custom prefabs can be created directly within your project or packaged as reusable libraries.

#### Basic Prefab Structure

A well-designed prefab should:

1. Extend `AgentBase` or another prefab
2. Take configuration parameters in the constructor
3. Apply configuration to set up the agent
4. Provide appropriate default values
5. Include domain-specific tools

Example of a custom support agent prefab:

```python
from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult

class CustomerSupportAgent(AgentBase):
    def __init__(
        self,
        product_name,
        knowledge_base_path=None,
        support_email=None,
        escalation_path=None,
        **kwargs
    ):
        # Pass standard params to parent
        super().__init__(**kwargs)
        
        # Store custom configuration
        self._product_name = product_name
        self._knowledge_base_path = knowledge_base_path
        self._support_email = support_email
        self._escalation_path = escalation_path
        
        # Configure prompt
        self.prompt_add_section("Personality", 
                               body=f"I am a customer support agent for {product_name}.")
        self.prompt_add_section("Goal", 
                               body="Help customers solve their problems effectively.")
        
        # Add standard instructions
        self._configure_instructions()
        
        # Register default tools
        self._register_default_tools()
    
    def _configure_instructions(self):
        """Configure standard instructions based on settings"""
        instructions = [
            "Be professional but friendly.",
            "Verify the customer's identity before sharing account details."
        ]
        
        if self._escalation_path:
            instructions.append(
                f"For complex issues, offer to escalate to {self._escalation_path}."
            )
            
        self.prompt_add_section("Instructions", bullets=instructions)
    
    def _register_default_tools(self):
        """Register default tools if appropriate paths are configured"""
        if self._knowledge_base_path:
            self.register_knowledge_base_tool()
    
    def register_knowledge_base_tool(self):
        """Register the knowledge base search tool if configured"""
        # Implementation...
        pass
    
    @AgentBase.tool(
        name="escalate_issue",
        description="Escalate a customer issue to a human agent",
        parameters={
            "issue_summary": {"type": "string", "description": "Brief summary of the issue"},
            "customer_email": {"type": "string", "description": "Customer's email address"}
        }
    )
    def escalate_issue(self, args, raw_data):
        # Implementation...
        return SwaigFunctionResult("Issue escalated successfully.")
    
    @AgentBase.tool(
        name="send_support_email",
        description="Send a follow-up email to the customer",
        parameters={
            "customer_email": {"type": "string"},
            "issue_summary": {"type": "string"},
            "resolution_steps": {"type": "string"}
        }
    )
    def send_support_email(self, args, raw_data):
        # Implementation...
        return SwaigFunctionResult("Follow-up email sent successfully.")
```

#### Using the Custom Prefab

```python
# Create an instance of the custom prefab
support_agent = CustomerSupportAgent(
    product_name="SignalWire Voice API",
    knowledge_base_path="./product_docs",
    support_email="support@example.com",
    escalation_path="tier 2 support",
    name="voice-support",
    route="/voice-support"
)

# Start the agent
support_agent.serve(host="0.0.0.0", port=8000)
```

#### Customizing Existing Prefabs

You can also extend and customize the built-in prefabs:

```python
from signalwire_agents.prefabs import InfoGathererAgent

class EnhancedGatherer(InfoGathererAgent):
    def __init__(self, fields, **kwargs):
        super().__init__(fields=fields, **kwargs)
        
        # Add an additional instruction
        self.prompt_add_section("Instructions", bullets=[
            "Verify all information carefully."
        ])
        
        # Add an additional custom tool
        
    @AgentBase.tool(
        name="check_customer", 
        description="Check customer status in database",
        parameters={"email": {"type": "string"}}
    )
    def check_customer(self, args, raw_data):
        # Implementation...
        return SwaigFunctionResult("Customer status: Active")
```

### Best Practices for Prefab Design

1. **Clear Documentation**: Document the purpose, parameters, and extension points
2. **Sensible Defaults**: Provide working defaults that make sense for the use case
3. **Error Handling**: Implement robust error handling with helpful messages
4. **Modular Design**: Keep prefabs focused on a specific use case
5. **Consistent Interface**: Maintain consistent patterns across related prefabs
6. **Extension Points**: Provide clear ways for others to extend your prefab
7. **Configuration Options**: Make all key behaviors configurable

### Making Prefabs Distributable

To create distributable prefabs that can be used across multiple projects:

1. **Package Structure**: Create a proper Python package
2. **Documentation**: Include clear usage examples 
3. **Configuration**: Support both code and file-based configuration
4. **Testing**: Include tests for your prefab
5. **Publishing**: Publish to PyPI or share via GitHub

Example package structure:

```
my-prefab-agents/
├── README.md
├── setup.py
├── examples/
│   └── support_agent_example.py
└── my_prefab_agents/
    ├── __init__.py
    ├── support.py
    ├── retail.py
    └── utils/
        ├── __init__.py
        └── knowledge_base.py
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
- `schema_path`: Optional path to schema.json file
- `suppress_logs`: Whether to suppress structured logs (default: False)

### Prompt Methods

- `prompt_add_section(title, body=None, bullets=None, numbered=False, numbered_bullets=False)`
- `prompt_add_subsection(parent_title, title, body=None, bullets=None)`
- `prompt_add_to_section(title, body=None, bullet=None, bullets=None)`
- `set_prompt_text(prompt_text)` or `set_prompt(prompt_text)`
- `set_post_prompt(prompt_text)`
- `setPersonality(text)` - Convenience method that calls prompt_add_section
- `setGoal(text)` - Convenience method that calls prompt_add_section
- `setInstructions(bullets)` - Convenience method that calls prompt_add_section

### SWAIG Methods

- `@AgentBase.tool(name, description, parameters={}, secure=True, fillers=None)`
- `define_tool(name, description, parameters, handler, secure=True, fillers=None)`
- `set_native_functions(function_names)`
- `add_native_function(function_name)`
- `remove_native_function(function_name)`
- `add_function_include(url, functions, meta_data=None)`

### Configuration Methods

- `add_hint(hint)` and `add_hints(hints)`
- `add_pattern_hint(hint, pattern, replace, ignore_case=False)`
- `add_pronunciation(replace, with_text, ignore_case=False)`
- `add_language(name, code, voice, speech_fillers=None, function_fillers=None, engine=None, model=None)`
- `set_param(key, value)` and `set_params(params_dict)`
- `set_global_data(data_dict)` and `update_global_data(data_dict)`

### State Methods

- `get_state(call_id)`
- `set_state(call_id, data)` 
- `update_state(call_id, data)`
- `clear_state(call_id)`
- `cleanup_expired_state()`

### SIP Routing Methods

- `enable_sip_routing(auto_map=True, path="/sip")`: Enable SIP routing for an agent
- `register_sip_username(sip_username)`: Register a SIP username for an agent
- `auto_map_sip_usernames()`: Automatically register SIP usernames based on agent attributes

#### AgentServer SIP Methods

- `setup_sip_routing(route="/sip", auto_map=True)`: Set up central SIP routing for a server
- `register_sip_username(username, route)`: Map a SIP username to an agent route

### Service Methods

- `serve(host=None, port=None)`: Start the web server
- `as_router()`: Return a FastAPI router for this agent
- `on_swml_request(request_data=None, callback_path=None)`: Customize SWML based on request data and path
- `on_summary(summary, raw_data=None)`: Handle post-prompt summaries
- `on_function_call(name, args, raw_data=None)`: Process SWAIG function calls
- `register_routing_callback(callback_fn, path="/sip")`: Register a callback for custom path routing
- `set_web_hook_url(url)`: Override the default web_hook_url with a supplied URL string
- `set_post_prompt_url(url)`: Override the default post_prompt_url with a supplied URL string

### Endpoint Methods

The SDK provides several endpoints for different purposes:

- Root endpoint (`/`): Serves the main SWML document
- SWAIG endpoint (`/swaig`): Handles SWAIG function calls
- Post-prompt endpoint (`/post_prompt`): Processes conversation summaries
- Check-for-input endpoint (`/check_for_input`): Supports checking for new input from external systems
- Debug endpoint (`/debug`): Serves the SWML document with debug headers
- SIP routing endpoint (configurable, default `/sip`): Handles SIP routing requests

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
            voice="en-US-Neural2-F",
            speech_fillers=["Let me think...", "One moment please..."],
            function_fillers=["I'm looking that up...", "Let me check that..."]
        )
        
        self.add_language(
            name="Spanish",
            code="es",
            voice="rime.spore:multilingual",
            speech_fillers=["Un momento por favor...", "Estoy pensando..."]
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