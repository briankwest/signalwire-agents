# Building Advanced AI Voice Agents with the SignalWire AI Agents SDK

## Table of Contents

1. **Introduction**
   - What is the SignalWire AI Agents SDK
   - Why Voice AI Matters in Customer Engagement
   - Key Features and Benefits

2. **Understanding the Architecture**
   - Core Components
   - Class Hierarchy
   - Request Flow
   - State Management

3. **Building Your First AI Agent**
   - Setting Up Your Environment
   - Creating a Simple Question-Answering Agent
   - Defining SWAIG Functions
   - Running and Testing Your Agent

4. **Advanced Agent Customization**
   - Prompt Building with POM
   - Adding Multilingual Support
   - Configuring Pronunciation and Hints
   - Setting AI Behavior Parameters
   - Handling State and Context

5. **SWAIG Functions: Extending Your Agent's Capabilities**
   - What Are SWAIG Functions
   - Parameter Definition
   - Function Implementation
   - Returning Results with Actions
   - Native Functions and External Integrations

6. **Prefab Agents: Ready-to-Use Solutions**
   - InfoGathererAgent for Structured Data Collection
   - FAQBotAgent for Knowledge Base Assistance
   - ConciergeAgent for Intelligent Routing
   - SurveyAgent for Feedback Collection
   - Creating Custom Prefabs

7. **Best Practices and Patterns**
   - Effective Prompt Design
   - Function Organization
   - Security Considerations
   - Performance Optimization
   - Deployment Strategies

8. **Real-World Examples**
   - Customer Service Automation
   - Appointment Scheduling
   - Technical Support
   - Lead Qualification
   - Surveys and Information Collection

9. **Conclusion**
   - Future Directions
   - Community and Support
   - Getting Started 

## 1. Introduction

### What is the SignalWire AI Agents SDK

The SignalWire AI Agents SDK is a Python framework that provides developers with powerful tools to create, deploy, and manage conversational AI agents with minimal effort. Unlike generic AI tools that require significant customization for voice applications, this SDK is purpose-built for creating voice-centric AI agents that can understand spoken language, respond naturally, and execute complex workflows.

At its core, the SDK enables you to create self-contained AI agents as microservices, each with its own personality, capabilities, and endpoints. These agents can handle telephone calls, respond to user queries, perform actions through custom functions, and maintain context throughout conversations. The SDK abstracts away the complexities of prompt engineering, state management, and web service configuration, allowing developers to focus on designing the agent's behavior and business logic.

### Why Voice AI Matters in Customer Engagement

Voice remains the most natural and efficient form of human communication. While text-based chatbots have become commonplace, they often fall short when handling complex interactions that require nuance, empathy, and real-time problem-solving. Voice AI agents bridge this gap by providing:

1. **Enhanced Accessibility**: Voice interfaces remove barriers for users who may struggle with typing or navigating visual interfaces.

2. **Increased Efficiency**: Speaking is typically 3-4 times faster than typing, allowing for quicker information exchange and problem resolution.

3. **Emotional Connection**: Voice conveys tone, emphasis, and emotion in ways that text simply cannot, creating more engaging and human-like interactions.

4. **Hands-Free Operation**: Voice agents enable interaction while users are engaged in other activities, expanding the contexts in which customers can engage with your services.

5. **Reduced Cognitive Load**: Natural conversation requires less mental effort than composing and reading text, making complex interactions feel simpler and more intuitive.

In customer engagement specifically, voice AI can transform key touchpoints throughout the customer journey. From initial inquiries and lead qualification to technical support and feedback collection, voice AI agents can provide personalized, efficient service at scale while reducing operational costs.

### Key Features and Benefits

The SignalWire AI Agents SDK offers several distinctive features that set it apart from general-purpose AI frameworks:

**Self-Contained Agents**: Each agent functions as both a web application and an AI persona, complete with its own HTTP endpoints, personality, and specialized capabilities. This modular approach allows for clear separation of concerns and simplified deployment.

**Prompt Object Model (POM)**: The SDK introduces a structured approach to prompt construction through the Prompt Object Model. POM enables clean organization of the agent's personality, goals, and instructions into discrete sections, making prompts more maintainable and effective.

**SWAIG Integration**: SignalWire AI Gateway (SWAIG) functions allow agents to perform actions beyond conversation, such as retrieving data, executing commands, or integrating with external systems. These functions are defined with clear parameter schemas and can be invoked by the AI when needed.

**Multilingual Support**: Agents can be configured to understand and respond in multiple languages with appropriate voice models and speech patterns for each language.

**State Management**: The SDK provides built-in conversation state tracking to maintain context across interactions, with options for different persistence mechanisms.

**Security Controls**: Basic authentication, function-specific security tokens, and session management are built into the framework, securing your agents against unauthorized access.

**Prefab Agents**: Ready-to-use agent implementations for common scenarios like information gathering, knowledge base questions, and customer routing accelerate development.

**Multi-Agent Orchestration**: Multiple specialized agents can be hosted on a single server, with routing mechanisms to direct users to the appropriate agent based on their needs.

The benefits of using the SignalWire AI Agents SDK include:

- **Reduced Development Time**: Eliminate boilerplate code and leverage built-in functionality for common tasks.
- **Improved Maintainability**: Structured organization of prompts and clear separation of business logic from AI infrastructure.
- **Enhanced Security**: Built-in authentication and authorization mechanisms protect sensitive functions.
- **Flexible Deployment**: Run as standalone services or integrate multiple agents into a cohesive system.
- **Accelerated Innovation**: Focus on unique business logic rather than infrastructure setup.

In the following sections, we'll explore the architecture of the SDK, walk through creating your first agent, and demonstrate advanced customization techniques to create powerful, production-ready AI voice agents. 

## 2. Understanding the Architecture

### Core Components

The SignalWire AI Agents SDK is built around several core components that work together to create a flexible, modular system for AI voice agents:

**SWML Service**: The foundation of the SDK is the SWML (SignalWire Markup Language) Service, which handles document creation, validation, and web service functionality. SWML is a JSON-based language that defines how phone calls and other media sessions should be controlled.

**AgentBase**: Built on top of SWML Service, the AgentBase class adds AI-specific capabilities, including prompt management, SWAIG function definition, and state tracking. This is the primary class that developers extend to create their own agents.

**Prompt Object Model (POM)**: A structured format for organizing AI prompts into sections like Personality, Goal, and Instructions. POM makes prompts more maintainable and effective by clearly separating different aspects of the agent's behavior.

**SWAIG Function Framework**: A system for defining, registering, and executing functions that the AI can call during conversations. This framework includes parameter validation, security controls, and result formatting.

**State Management**: Components for tracking and persisting conversation state across interactions, with different storage options for various deployment scenarios.

**Prefab Agents**: Pre-built agent implementations for common use cases, which can be used directly or customized to specific needs.

**HTTP Routing**: Built on FastAPI, the SDK includes a routing system for handling various endpoints, including SWML document serving, SWAIG function execution, and custom paths.

Each of these components is designed to handle a specific aspect of AI agent functionality, creating a clean separation of concerns while providing a cohesive experience for developers.

### Class Hierarchy

The SDK follows a clear class hierarchy that makes it easy to understand and extend:

```
┌─────────────┐
│ SWMLService │ Base class for SWML document creation and web services
└─────▲───────┘
      │
┌─────┴───────┐
│  AgentBase  │ Adds AI functionality to SWMLService
└─────▲───────┘
      │
┌─────┴───────┐         ┌────────────────┐
│ Custom Agent│◄────────┤ Prefab Agents  │
│(Your Code)  │         │(Ready-to-use)  │
└─────────────┘         └────────────────┘
```

**SWMLService**: The base class that handles SWML document creation, schema validation, and HTTP service functionality. It provides methods for adding SWML verbs to documents and serving them via HTTP endpoints.

**AgentBase**: Extends SWMLService with AI-specific functionality such as prompt building, SWAIG function definition, multilingual support, and state management. This is the class most developers will extend to create their agents.

**Custom Agents**: Your implementation that extends AgentBase with specific business logic, custom functions, and personalized prompts. This is where you define what makes your agent unique.

**Prefab Agents**: Pre-built agent implementations for common use cases, which extend AgentBase with specialized functionality. These can be used directly or as templates for custom agents.

This hierarchical design allows for clear extension points and makes it easy to understand where different functionalities are implemented.

### Request Flow

Understanding how requests flow through the system is crucial for developing and debugging agents. The SDK handles several types of requests:

**SWML Document Request (GET/POST /):**
1. Client sends a request to the agent's root endpoint
2. Authentication is validated using HTTP Basic Auth
3. The `on_swml_request()` method is called to allow customization of the document
4. The current SWML document is rendered and returned as JSON
5. SignalWire's platform processes this document to control the call behavior

**SWAIG Function Call (POST /swaig/):**
1. During a conversation, when the AI decides to call a function, a POST request is sent to the SWAIG endpoint
2. Authentication is validated
3. Function name and arguments are extracted from the request
4. For secure functions, token validation occurs
5. The appropriate function is executed with the provided arguments
6. The result is formatted and returned to be integrated into the conversation

**Post-Prompt Processing (POST /post_prompt/):**
1. After a conversation ends, if a post-prompt is configured, the summary is sent to this endpoint
2. Authentication is validated
3. The summary data is extracted from the request
4. The `on_summary()` method is called to process this data
5. Any custom logic for storing or acting on the summary is executed

**Custom Routing (Various paths):**
1. Requests to custom paths are received
2. Authentication is validated
3. The appropriate routing callback is invoked
4. The callback can redirect the request or allow it to proceed with custom handling

This request flow enables a flexible system where different parts of the conversation lifecycle can be customized while maintaining a consistent overall structure.

### State Management

The SDK includes a robust state management system that allows agents to maintain context across interactions. This is especially important for voice applications where understanding the conversation history is crucial for providing relevant responses.

**Session Manager**: Handles session creation, activation, and termination. A session typically corresponds to a single call or conversation.

**State Manager Interface**: Defines the standard operations for retrieving, updating, and storing state. This interface can be implemented by different storage backends.

**Storage Options**:
- **MemoryStateManager**: Stores state in memory, suitable for development or stateless deployments.
- **FileStateManager**: Persists state to disk, suitable for single-server deployments.
- **Custom State Managers**: Developers can implement their own state managers for database storage or distributed systems.

**State Lifecycle**:
1. When a new call starts, a session is created with a unique call ID
2. During the conversation, state can be retrieved and updated using this call ID
3. Functions can access and modify state to maintain context
4. When the call ends, the session can be cleaned up or archived

**State Structure**: State is stored as JSON-compatible data, allowing for flexible schemas and easy serialization. Common patterns include:
- Storing user information and preferences
- Tracking the progress of multi-step processes
- Recording answers to questions
- Maintaining conversation history for context

This state management system strikes a balance between simplicity and flexibility, making it easy to implement common patterns while allowing for customization when needed.

The architecture of the SignalWire AI Agents SDK is designed to provide a solid foundation for building sophisticated voice agents while abstracting away many of the complexities. By understanding these components and how they work together, developers can leverage the full power of the SDK to create engaging, intelligent voice experiences. 

## 3. Building Your First AI Agent

Let's dive into creating your first AI agent with the SignalWire AI Agents SDK. We'll build a simple question-answering agent that can respond to basic queries and provide real-time information through custom functions.

### Setting Up Your Environment

Before we start coding, you'll need to set up your development environment:

1. **Install the SDK**:
   ```bash
   pip install signalwire-agents
   ```

2. **Environment Variables** (Optional):
   For consistent authentication credentials across restarts, you can set these environment variables:
   ```bash
   export SWML_BASIC_AUTH_USER=your_username
   export SWML_BASIC_AUTH_PASSWORD=your_password
   ```
   If not specified, the SDK will generate random credentials on startup.

3. **Create a New Project Directory**:
   ```bash
   mkdir my-first-agent
   cd my-first-agent
   ```

With these prerequisites in place, let's create a simple agent that can answer questions and provide the current time when asked.

### Creating a Simple Question-Answering Agent

The core of your agent is a Python class that extends `AgentBase`. Here's how to create a basic question-answering agent:

```python
from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult
from datetime import datetime

class SimpleQAAgent(AgentBase):
    """
    A simple question-answering agent that can provide the current time
    and answer basic questions.
    """
    
    def __init__(self):
        # Initialize the agent with a name and route
        super().__init__(
            name="simple-qa",
            route="/qa",
            host="0.0.0.0",
            port=3000,
            use_pom=True  # Enable the Prompt Object Model for structured prompts
        )
        
        # Configure the agent's personality and behavior
        self.prompt_add_section("Personality", 
                               body="You are a friendly and helpful assistant designed to answer questions clearly and concisely.")
        
        self.prompt_add_section("Goal", 
                               body="Help users by answering their questions accurately and providing helpful information.")
        
        self.prompt_add_section("Instructions", bullets=[
            "Respond to questions in a friendly, conversational tone",
            "Keep answers brief but informative",
            "If you don't know something, acknowledge that clearly",
            "Use the get_time function when asked about the current time",
            "Be helpful and respectful at all times"
        ])
        
        # Add a post-prompt for generating conversation summaries
        self.set_post_prompt("""
        Summarize this conversation in JSON format:
        {
            "topic": "The main topic discussed",
            "questions_asked": ["List of questions asked"],
            "satisfaction_level": "high/medium/low based on how well questions were answered",
            "follow_up_needed": true/false
        }
        """)
```

This initial setup creates an agent with:
- A defined personality, goal, and instructions
- A clear route (/qa) and server configuration
- A post-prompt that will generate a summary after each conversation

### Defining SWAIG Functions

Now, let's add a SWAIG function to our agent that allows it to provide the current time when asked:

```python
@AgentBase.tool(
    name="get_time",
    description="Get the current time and date",
    parameters={}  # This function doesn't need any parameters
)
def get_time(self, args, raw_data):
    """
    Returns the current time and date.
    
    This function is called by the AI when users ask about the current time.
    """
    now = datetime.now()
    formatted_time = now.strftime("%H:%M:%S")
    formatted_date = now.strftime("%A, %B %d, %Y")
    
    return SwaigFunctionResult(
        f"The current time is {formatted_time}. Today is {formatted_date}."
    )
```

Let's add another function that provides weather information based on a location parameter:

```python
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
    """
    Returns weather information for a specified location.
    
    In a real implementation, this would call a weather API.
    For this example, we'll return mock data.
    """
    location = args.get("location", "Unknown location")
    
    # In a real implementation, you would call a weather API here
    # For example: weather_data = weather_api.get_current(location)
    
    # For this example, we'll return mock data
    weather_info = f"It's sunny and 72°F in {location} with a gentle breeze from the west."
    
    # Create a result with both text and actions
    result = SwaigFunctionResult(weather_info)
    
    # Add an action to log this request
    result.add_action("log", {"message": f"Weather requested for {location}"})
    
    return result
```

### Running and Testing Your Agent

Now that we've defined our agent class with personality and functions, let's create a script to run it:

```python
if __name__ == "__main__":
    # Create an instance of our agent
    agent = SimpleQAAgent()
    
    # Print access information
    username, password = agent.get_basic_auth_credentials()
    print(f"Agent is available at: http://localhost:3000/qa")
    print(f"Basic Auth: {username}:{password}")
    
    try:
        # Start the agent's web server
        agent.serve()
    except KeyboardInterrupt:
        print("\nStopping the agent.")
```

Save this complete code as `simple_qa_agent.py` and run it:

```bash
python simple_qa_agent.py
```

When you run this script, you'll see output similar to:

```
Agent is available at: http://localhost:3000/qa
Basic Auth: user_ab12: JdK8Ls9pQw3mFr7T
Starting the agent. Press Ctrl+C to stop.
```

Your agent is now running as a web service! To test it:

1. If you have SignalWire credentials, you can direct calls to this endpoint.
2. Alternatively, you can use tools like Postman or cURL to send requests to the endpoint.

For example, using cURL:

```bash
curl -u user_ab12:JdK8Ls9pQw3mFr7T http://localhost:3000/qa
```

This will return the SWML document that defines your agent's behavior.

### Next Steps

You've now created your first AI agent with the SignalWire AI Agents SDK! This simple agent can:
- Answer questions using its configured personality
- Provide the current time when asked
- Give weather information for specified locations
- Generate conversation summaries after each interaction

From here, you can:
- Add more functions to extend its capabilities
- Customize its personality and instructions
- Configure additional features like multilingual support
- Deploy it to a server for actual call handling

In the next section, we'll explore more advanced customization options to create even more powerful and flexible agents.

## 4. Advanced Agent Customization

Now that you've built a basic agent, let's explore advanced customization options that can make your agents more sophisticated, versatile, and effective in real-world scenarios.

### Prompt Building with POM

The Prompt Object Model (POM) is a key feature of the SignalWire AI Agents SDK that allows for structured, maintainable prompt construction. While we used some basic POM capabilities in our simple agent, the full power of POM offers much more flexibility:

#### Section Types and Organization

The POM supports various section types to organize your agent's instructions:

```python
# Main sections with body text
self.prompt_add_section("Personality", 
                       body="You are a customer service representative for SignalWire.")

# Sections with bullet points
self.prompt_add_section("Instructions", bullets=[
    "Always ask for account verification before sharing sensitive information",
    "Offer to escalate to a human if you cannot resolve the issue",
    "Maintain a professional but friendly tone"
])

# Sections with both body and bullets
self.prompt_add_section("Context", 
                       body="The user is calling about a technical issue.",
                       bullets=["They may be experiencing service disruption", 
                               "Have technical account details ready"])

# Numbered sections
self.prompt_add_section("Process", 
                       bullets=["Verify identity", "Diagnose problem", "Suggest solution"],
                       numbered=True)  # Creates a numbered list

# Add subsections for better organization
self.prompt_add_subsection("Instructions", "Technical Support", bullets=[
    "Ask for error messages",
    "Check service status before troubleshooting"
])
```

#### Dynamic Content

You can also make your prompts dynamic by adding content at runtime:

```python
# Add to an existing section 
self.prompt_add_to_section("Context", 
                          bullet="Current system status: All services operational")

# Add or update sections based on runtime conditions
if high_call_volume:
    self.prompt_add_section("Priority", 
                          body="Focus on quick resolution due to high call volume")
else:
    self.prompt_add_section("Priority", 
                          body="Take time to fully address customer needs")
```

#### Convenience Methods

The SDK also provides convenience methods for common prompt sections:

```python
# These are equivalent to prompt_add_section with appropriate titles
self.setPersonality("You are a technical support specialist.")
self.setGoal("Resolve customer technical issues efficiently.")
self.setInstructions([
    "Get specific error details",
    "Guide users through troubleshooting steps",
    "Document the resolution"
])
```

### Adding Multilingual Support

One of the powerful features of the SignalWire AI Agents SDK is built-in multilingual support. This allows your agent to communicate with users in their preferred language, providing a more inclusive and personalized experience.

#### Configuring Multiple Languages

Here's how to add support for multiple languages:

```python
# Add English as the primary language
self.add_language(
    name="English",
    code="en-US",
    voice="elevenlabs.josh",  # Using ElevenLabs voice
    speech_fillers=["Let me think about that...", "One moment please..."],
    function_fillers=["I'm looking that up for you...", "Let me check that..."]
)

# Add Spanish with appropriate fillers
self.add_language(
    name="Spanish",
    code="es",
    voice="elevenlabs.antonio:eleven_multilingual_v2",
    speech_fillers=["Un momento por favor...", "Estoy pensando..."],
    function_fillers=["Estoy buscando esa información...", "Déjame verificar..."]
)

# Add French with specific engine and model parameters
self.add_language(
    name="French",
    code="fr-FR",
    voice="claire",
    engine="rime",
    model="arcana",
    speech_fillers=["Un instant s'il vous plaît...", "Laissez-moi réfléchir..."]
)

# Enable language detection and switching
self.set_params({"languages_enabled": True})
```

#### Voice Specification Formats

There are several formats for specifying voices:

```python
# Simple format
voice="en-US-Neural2-F"

# Provider-prefixed format
voice="elevenlabs.josh"

# Provider with model
voice="elevenlabs.antonio:eleven_multilingual_v2"

# Explicit parameters
self.add_language(
    name="German",
    code="de-DE",
    voice="hans",
    engine="rime",
    model="arcana"
)
```

#### Language Detection and Switching

With multiple languages configured and `languages_enabled` set to `True`, the agent will automatically detect the user's language based on their speech and respond in the same language using the appropriate voice and fillers.

### Configuring Pronunciation and Hints

For voices to sound natural, especially with technical terms, acronyms, or brand names, you can configure pronunciation rules and hints.

#### Adding Pronunciation Rules

Pronunciation rules map specific terms to the way they should be pronounced:

```python
# Spell out acronyms
self.add_pronunciation("API", "A P I", ignore_case=False)
self.add_pronunciation("SDK", "S D K", ignore_case=True)

# Correct pronunciation of brand names
self.add_pronunciation("SignalWire", "Signal Wire", ignore_case=False)
self.add_pronunciation("PostgreSQL", "Postgres Q L", ignore_case=True)
```

#### Pattern Hints

For more complex pattern matching, use pattern hints with regular expressions:

```python
# Help with AI terms using regex patterns
self.add_pattern_hint(
    hint="AI Agent",
    pattern="AI\\s+Agent",
    replace="A.I. Agent",
    ignore_case=True
)

# Format version numbers appropriately
self.add_pattern_hint(
    hint="version numbers",
    pattern="v(\\d+)\\.(\\d+)",
    replace="version $1 point $2",
    ignore_case=True
)
```

#### Simple Hints

For general terminology that should be recognized but doesn't need special pronunciation:

```python
# Add product and technical terms as hints
self.add_hints([
    "SignalWire",
    "SWML",
    "SWAIG",
    "WebRTC",
    "SIP"
])
```

These pronunciation rules and hints help the AI understand and pronounce technical terms correctly, creating a more professional and natural-sounding experience for users.

### Setting AI Behavior Parameters

The SDK provides extensive parameters to control how the AI agent behaves during conversations. These allow fine-tuning of the interaction style, timing, and other aspects of the conversation.

```python
# Configure AI behavior parameters
self.set_params({
    # Conversation flow
    "wait_for_user": False,          # Start speaking immediately vs. waiting for user
    "end_of_speech_timeout": 1000,   # Milliseconds of silence to detect end of speech
    "energy_level": 50,              # Sensitivity for detecting speech (0-100)
    
    # Voice and audio settings
    "ai_volume": 5,                  # Voice volume level
    "background_file": "https://example.com/hold-music.mp3",  # Background audio
    "background_file_volume": -10,   # Volume for background audio
    
    # Interruption handling
    "transparent_barge": True,       # Allow users to interrupt the AI
    "barge_min_words": 3,            # Min words needed to trigger interruption
    
    # Timeout handling
    "attention_timeout": 30000,      # Milliseconds before prompting unresponsive user
    "inactivity_timeout": 300000,    # Milliseconds of inactivity before ending session
    
    # Language settings
    "languages_enabled": True,       # Enable multilingual support
    "local_tz": "America/New_York",  # Default timezone for time functions
    
    # Advanced features
    "enable_vision": False,          # Enable visual processing capabilities
    "verbose_logs": True             # Enable detailed logging
})
```

You can also update parameters individually:

```python
# Update a single parameter
self.set_param("ai_volume", 7)
```

These parameters allow you to create conversational experiences tailored to specific use cases, from quick information retrieval to in-depth consultations.

### Handling State and Context

For sophisticated agents, maintaining state across a conversation is essential. The SDK provides built-in state management capabilities for tracking context and user information.

#### Enabling State Tracking

To enable state management, configure it in the constructor:

```python
from signalwire_agents.core.state import FileStateManager

# Create the agent with state tracking enabled
super().__init__(
    name="stateful-agent",
    enable_state_tracking=True,  # Automatically registers startup and hangup hooks
    state_manager=FileStateManager(storage_dir="./state_data")  # Custom state manager
)
```

#### Accessing and Updating State

State can be accessed and modified from any function, especially SWAIG functions:

```python
@AgentBase.tool(
    name="record_preference",
    description="Record a user preference",
    parameters={
        "preference_name": {"type": "string", "description": "Preference name"},
        "preference_value": {"type": "string", "description": "Preference value"}
    }
)
def record_preference(self, args, raw_data):
    call_id = raw_data.get("call_id")
    
    if not call_id:
        return SwaigFunctionResult("Could not save preference: No call ID")
    
    # Get current state (or initialize empty if none exists)
    state = self.get_state(call_id) or {}
    
    # Make sure we have a preferences section
    preferences = state.get("preferences", {})
    
    # Update the preference
    preferences[args.get("preference_name")] = args.get("preference_value")
    
    # Update the state
    state["preferences"] = preferences
    self.update_state(call_id, state)
    
    return SwaigFunctionResult("Your preference has been saved.")
```

#### Using State to Track Conversation Flow

State is particularly useful for multi-turn interactions:

```python
@AgentBase.tool(
    name="start_order",
    description="Start a new food order",
    parameters={}
)
def start_order(self, args, raw_data):
    call_id = raw_data.get("call_id")
    
    if not call_id:
        return SwaigFunctionResult("Could not start order: No call ID")
    
    # Initialize order state
    order_state = {
        "status": "collecting_items",
        "items": [],
        "delivery_address": None,
        "payment_method": None
    }
    
    # Update the state
    self.update_state(call_id, {"order": order_state})
    
    return SwaigFunctionResult("I've started a new order for you. What would you like to order?")
```

#### Global Data vs. State

In addition to state, the SDK also supports global data, which is available to the AI directly in the prompt:

```python
# Set global data that will be available to the AI
self.set_global_data({
    "company_name": "SignalWire",
    "business_hours": "9am-5pm ET, Monday through Friday",
    "support_email": "support@example.com",
    "available_services": [
        "Voice API",
        "Video API",
        "Messaging API"
    ]
})

# Update global data during execution
@AgentBase.tool(name="update_service_status")
def update_service_status(self, args, raw_data):
    # Get the current global data
    global_data = self.get_global_data()
    
    # Update it
    global_data["service_status"] = "All systems operational"
    
    # Set the updated data
    self.set_global_data(global_data)
    
    return SwaigFunctionResult("Service status updated.")
```

The combination of state management and global data enables the creation of complex, context-aware agents that can handle multi-turn interactions and maintain information throughout a conversation, making for more natural and effective user experiences.

## 5. SWAIG Functions: Extending Your Agent's Capabilities

SWAIG (SignalWire AI Gateway) functions are one of the most powerful features of the SignalWire AI Agents SDK. They allow your AI agent to go beyond simple conversation by providing the ability to execute code, access external systems, and perform actions on behalf of the user. In this section, we'll dive deeper into how to define, implement, and leverage SWAIG functions effectively.

### What Are SWAIG Functions

SWAIG functions are callable methods that the AI can invoke during conversations to accomplish specific tasks. They serve as the bridge between the conversational interface and your business logic or external systems. Unlike traditional webhook systems, SWAIG functions are seamlessly integrated into the conversation flow, allowing the AI to:

1. **Determine When to Call**: The AI decides when to invoke functions based on user requests
2. **Extract Parameters**: The AI identifies and extracts relevant parameters from the conversation
3. **Use Results**: The AI incorporates function results back into the conversation naturally

This creates a fluid experience where users don't need to follow strict command formats - they can simply express their needs conversationally, and the AI will handle the details of function invocation.

Each SWAIG function consists of:
- A **name** that the AI uses to reference the function
- A **description** that helps the AI understand when to use the function
- A **parameters schema** that defines what information the function needs
- An **implementation** that executes when the function is called
- Optional **security settings** that control access to the function

### Parameter Definition

A key aspect of SWAIG functions is their well-defined parameter schema. This schema helps the AI understand what information to extract from the conversation and how to format it when calling the function. The schema uses a JSON Schema-inspired format:

```python
@AgentBase.tool(
    name="book_appointment",
    description="Book an appointment for a customer",
    parameters={
        "customer_name": {
            "type": "string",
            "description": "The full name of the customer"
        },
        "service_type": {
            "type": "string",
            "description": "The type of service requested",
            "enum": ["haircut", "coloring", "styling", "consultation"]
        },
        "preferred_date": {
            "type": "string",
            "description": "The preferred date for the appointment (YYYY-MM-DD)"
        },
        "preferred_time": {
            "type": "string",
            "description": "The preferred time for the appointment (HH:MM)",
            "pattern": "^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"
        },
        "special_requests": {
            "type": "string",
            "description": "Any special requests or notes",
            "nullable": True
        }
    }
)
```

This schema format supports:

- **Basic Types**: string, number, integer, boolean, array, object
- **Validation Rules**: enum (allowed values), pattern (regex), minimum/maximum (for numbers)
- **Optional Parameters**: Using the `nullable` property
- **Nested Objects**: Using the object type with properties
- **Arrays**: Using the array type with items

These schemas serve multiple purposes:
1. **AI Guidance**: Help the AI understand what information to collect
2. **Validation**: Ensure the parameters meet expected formats
3. **Documentation**: Self-document the function's requirements

When designing parameter schemas, aim for clarity and specific descriptions to help the AI correctly extract the right information from user conversations.

### Function Implementation

The implementation of a SWAIG function is a Python method that receives the parameters extracted by the AI and performs the necessary actions. Here's a comprehensive example:

```python
@AgentBase.tool(
    name="check_order_status",
    description="Check the status of a customer's order",
    parameters={
        "order_id": {
            "type": "string",
            "description": "The order ID to check"
        }
    }
)
def check_order_status(self, args, raw_data):
    """
    Check the status of an order in our system.
    
    Args:
        args: Dictionary containing the parsed parameters (order_id)
        raw_data: Complete request data including call_id and other metadata
    
    Returns:
        SwaigFunctionResult with the order status information
    """
    # Extract the order ID from args
    order_id = args.get("order_id")
    
    # Log the function call
    self.log.info("check_order_status_called", order_id=order_id)
    
    try:
        # In a real implementation, you would query your order system
        # For this example, we'll simulate different statuses
        
        # Simulate a database query
        # order_data = order_database.get_order(order_id)
        
        # For demonstration, generate a status based on the order ID
        status_options = ["processing", "shipped", "delivered", "pending"]
        simulated_status = status_options[hash(order_id) % len(status_options)]
        
        # Create estimated delivery date (for demonstration)
        from datetime import datetime, timedelta
        estimated_delivery = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        
        # Format response based on status
        if simulated_status == "processing":
            response = f"Order {order_id} is currently being processed. Estimated shipping in 1-2 business days."
        elif simulated_status == "shipped":
            response = f"Order {order_id} has been shipped and is on its way. Expected delivery by {estimated_delivery}."
        elif simulated_status == "delivered":
            response = f"Order {order_id} has been delivered. It was completed on {estimated_delivery}."
        else:  # pending
            response = f"Order {order_id} is pending payment confirmation. Please allow 24 hours for processing."
        
        # Create the result
        result = SwaigFunctionResult(response)
        
        # Add the order status to global data for future reference
        result.add_action("set_global_data", {
            "last_checked_order": {
                "id": order_id,
                "status": simulated_status,
                "estimated_delivery": estimated_delivery
            }
        })
        
        return result
        
    except Exception as e:
        # Handle errors gracefully
        self.log.error("order_status_error", error=str(e), order_id=order_id)
        return SwaigFunctionResult(
            f"I'm sorry, I couldn't retrieve information for order {order_id}. " +
            "Please verify the order number or try again later."
        )
```

This implementation demonstrates several best practices:

1. **Comprehensive Docstring**: Clearly documents what the function does
2. **Parameter Extraction**: Gets parameters from the `args` dictionary
3. **Logging**: Records function invocation and any errors
4. **Error Handling**: Gracefully handles exceptions with user-friendly messages
5. **Structured Response**: Returns a well-formatted response with relevant information
6. **Global Data Updates**: Stores information that might be needed later

### Returning Results with Actions

The `SwaigFunctionResult` class provides a flexible way to return information and trigger actions. Beyond simple text responses, you can include various actions that affect the conversation flow or system state:

```python
@AgentBase.tool(
    name="process_payment",
    description="Process a payment for an order",
    parameters={
        "amount": {
            "type": "number",
            "description": "Payment amount"
        },
        "payment_method": {
            "type": "string",
            "description": "Payment method (credit_card, bank_transfer)",
            "enum": ["credit_card", "bank_transfer"]
        }
    }
)
def process_payment(self, args, raw_data):
    amount = args.get("amount")
    payment_method = args.get("payment_method")
    
    # Simulate payment processing
    transaction_id = f"TXN-{hash(str(amount) + payment_method) % 10000:04d}"
    
    # Create the result with an initial response
    result = SwaigFunctionResult(
        f"I've processed your {payment_method} payment for ${amount:.2f}. " +
        f"Your transaction ID is {transaction_id}."
    )
    
    # Add a single action
    result.add_action("log", {
        "message": f"Payment processed: ${amount:.2f} via {payment_method}"
    })
    
    # Add multiple actions at once
    result.add_actions([
        # Update global data with payment info
        {"set_global_data": {
            "last_transaction": {
                "id": transaction_id,
                "amount": amount,
                "method": payment_method,
                "status": "completed"
            }
        }},
        # Play a success sound in the background
        {"playback_bg": {
            "file": "https://example.com/sounds/payment_success.mp3",
            "wait": False
        }}
    ])
    
    # Chain actions for readability (alternative to add_actions)
    result.add_action("say", "Your receipt will be emailed to you shortly.")
    
    return result
```

Common action types include:

- **set_global_data/unset_global_data**: Update information available to the AI
- **log**: Record information for debugging or auditing
- **say**: Have the AI speak additional text
- **playback_bg**: Play background sounds or music
- **context_switch**: Change the AI's contextual understanding
- **stop_playback_bg**: Stop background audio
- **user_input**: Inject text as if the user had said it

These actions allow for rich, interactive experiences that go beyond simple text responses.

### Best Practices for SWAIG Functions

When designing and implementing SWAIG functions, keep these best practices in mind:

1. **Single Responsibility**: Each function should do one thing well
2. **Clear Descriptions**: Write detailed descriptions that help the AI understand when to use the function
3. **Specific Parameters**: Define parameters with clear names and descriptions
4. **Error Handling**: Gracefully handle exceptions with user-friendly messages
5. **Meaningful Responses**: Return results that the AI can easily incorporate into the conversation
6. **Action Combinations**: Use multiple actions when appropriate to create rich experiences
7. **Logging**: Include logging for debugging and analytics
8. **Performance**: Keep functions fast when possible, or use fillers for longer operations

By following these practices, you can create SWAIG functions that seamlessly integrate with the conversation flow, allowing your agent to provide helpful, dynamic responses to user requests.

### Native Functions and External Integrations

In addition to custom functions that you implement, the SDK supports native functions (built into SignalWire's platform) and external function integrations:

#### Native Functions

Native functions are pre-built capabilities provided by the SignalWire platform:

```python
# Register native functions
self.set_native_functions([
    "check_time",       # Get the current time in various formats/timezones
    "wait_seconds"      # Pause the conversation for a specified duration
])
```

These functions are immediately available to the AI without requiring any implementation code.

#### External Function Includes

You can also include functions hosted at external URLs:

```python
# Include functions from an external API
self.add_function_include(
    url="https://api.example.com/ai-functions",
    functions=[
        "search_knowledge_base",
        "get_product_details",
        "calculate_shipping"
    ],
    meta_data={
        "api_key": "your-api-key",
        "organization_id": "org123"
    }
)

# Include another set of functions from a different API
self.add_function_include(
    url="https://analytics.example.org/functions",
    functions=["get_user_insights"]
)
```

This feature allows you to:
1. **Split Functionality**: Distribute functions across multiple services
2. **Reuse Functions**: Share functions between different agents
3. **Third-Party Integration**: Leverage external AI function marketplaces

External functions follow the same invocation pattern from the AI's perspective, but the execution happens at the remote endpoint rather than within your agent's code.

### Function Security and Controls

SWAIG functions often provide access to sensitive operations or data, so the SDK includes several security features:

#### Secure Functions

By default, all SWAIG functions are marked as secure, meaning they require proper authentication:

```python
@AgentBase.tool(
    name="get_account_details",
    description="Get customer account details",
    parameters={"account_id": {"type": "string"}},
    secure=True  # This is the default
)
```

Secure functions use token-based authentication for each call, with tokens that are:
- **Scoped to specific functions**: A token for one function can't be used for another
- **Tied to specific call IDs**: Prevents cross-session usage
- **Time-limited**: Expire after a configurable duration

#### Function Fillers

To improve the user experience during function execution, you can configure "fillers" - phrases that the AI will say while waiting for a function to complete:

```python
@AgentBase.tool(
    name="search_database",
    description="Search the customer database",
    parameters={"query": {"type": "string"}},
    fillers={
        "en-US": [
            "Let me search our records...",
            "I'm looking that up for you...",
            "Checking our database..."
        ],
        "es": [
            "Déjame buscar en nuestros registros...",
            "Estoy buscando esa información..."
        ]
    }
)
```

These fillers make the conversation feel more natural during delays, especially for operations that might take several seconds to complete.

## 6. Prefab Agents: Ready-to-Use Solutions

The SignalWire AI Agents SDK includes several pre-built "prefab" agents that provide ready-to-use implementations for common use cases. These prefabs can significantly accelerate your development process, allowing you to deploy fully functional agents with minimal code. In this section, we'll explore the available prefab agents, how to configure them, and strategies for extending them to meet your specific needs.

### InfoGathererAgent for Structured Data Collection

The InfoGathererAgent is designed to systematically collect information from users through a series of predefined questions. This makes it ideal for intake forms, registration processes, surveys, and any situation where you need to gather specific information in a structured format.

#### Configuration

Setting up an InfoGathererAgent is straightforward:

```python
from signalwire_agents.prefabs import InfoGathererAgent

# Create an agent that collects user registration information
registration_agent = InfoGathererAgent(
    name="registration-form",
    route="/register",
    questions=[
        {
            "key_name": "full_name",
            "question_text": "What is your full name?"
        },
        {
            "key_name": "email",
            "question_text": "What is your email address?",
            "confirm": True  # This will prompt the AI to confirm the answer
        },
        {
            "key_name": "birth_date",
            "question_text": "What is your date of birth? Please provide it in MM/DD/YYYY format."
        },
        {
            "key_name": "reason",
            "question_text": "What brings you to our service today?"
        }
    ]
)
```

The agent manages the question flow automatically, tracking which questions have been asked and storing the answers in its state. The `confirm` option for questions allows you to specify which questions require confirmation due to their importance or potential for misunderstanding.

#### How It Works

The InfoGathererAgent implements a state-based question flow with two main SWAIG functions:

1. **start_questions**: Begins the question sequence with the first question
2. **submit_answer**: Records an answer to the current question and advances to the next one

Here's a simplified view of the flow:

1. When the conversation begins, the agent introduces itself and asks if the user is ready to begin
2. Once the user confirms, the AI calls `start_questions` to begin the process
3. The AI asks the first question from the configured list
4. When the user responds, the AI extracts the answer and calls `submit_answer`
5. The answer is stored, and the agent provides the next question
6. This process continues until all questions have been answered
7. When complete, the agent confirms that all information has been collected

#### Extending InfoGathererAgent

While the base implementation is sufficient for many use cases, you can extend it to add custom validation, processing, or follow-up actions:

```python
class CustomInfoGatherer(InfoGathererAgent):
    def __init__(self):
        super().__init__(
            name="customer-intake",
            route="/intake",
            questions=[
                {"key_name": "name", "question_text": "What is your name?"},
                {"key_name": "issue", "question_text": "Please describe your issue briefly."}
            ]
        )
        # Add a custom prompt section for more personalized interactions
        self.prompt_add_section("Introduction", 
                               body="Greet the user warmly and explain that you'll need to collect some information to help them.")
    
    # Override to add custom processing after all questions are answered
    def on_all_questions_completed(self, call_id, answers):
        # Process the collected information
        print(f"All questions completed for call {call_id}")
        print(f"Answers: {answers}")
        
        # You could add automatic routing, ticket creation, etc. here
        
        # Return a custom message
        return "Thank you for providing that information. I've created a support ticket for you, and a specialist will contact you shortly."
    
    # Add a custom function for after information is collected
    @AgentBase.tool(
        name="schedule_follow_up",
        description="Schedule a follow-up call",
        parameters={
            "preferred_time": {"type": "string", "description": "Preferred time for follow-up"}
        }
    )
    def schedule_follow_up(self, args, raw_data):
        # Implementation details...
        return SwaigFunctionResult("Your follow-up has been scheduled.")
```

This extensibility allows you to maintain the core question flow functionality while adding your own business logic and custom features.

### FAQBotAgent for Knowledge Base Assistance

The FAQBotAgent is designed to answer questions using a provided knowledge base. It's ideal for creating support bots, information assistants, and any agent that needs to provide factual answers based on specific content.

#### Configuration

To set up a FAQBotAgent, you provide it with FAQ content in one of several formats:

```python
from signalwire_agents.prefabs import FAQBotAgent

# Create an agent with direct FAQ content
support_agent = FAQBotAgent(
    name="product-support",
    route="/support",
    faq_content=[
        {
            "question": "How do I reset my password?",
            "answer": "To reset your password, visit the login page and click on 'Forgot Password'. Follow the instructions sent to your email."
        },
        {
            "question": "What payment methods do you accept?",
            "answer": "We accept Visa, Mastercard, American Express, and PayPal."
        },
        {
            "question": "How long does shipping take?",
            "answer": "Standard shipping typically takes 3-5 business days within the continental US."
        }
    ]
)

# Alternatively, load from a file
documentation_agent = FAQBotAgent(
    name="api-docs",
    route="/docs",
    faq_file="documentation.json"  # JSON file with question/answer pairs
)

# Or load from a URL
knowledge_agent = FAQBotAgent(
    name="knowledge-base",
    route="/kb",
    faq_url="https://example.com/api/knowledge-base",
    refresh_interval=3600  # Refresh content every hour
)
```

The agent processes this content and makes it available to the AI as context for answering questions.

#### How It Works

The FAQBotAgent works by:

1. Loading and processing the provided FAQ content
2. Including this content in the AI's prompt as reference material
3. Configuring the agent with a personality and goal focused on providing helpful, accurate answers
4. Adding fallback mechanisms for questions outside the knowledge domain

The agent doesn't typically need custom SWAIG functions since its primary purpose is to answer questions directly using the AI's reasoning capabilities and the provided content. However, it can be extended with additional functions for more complex scenarios.

#### Advanced Configuration

For more control over the FAQBotAgent's behavior:

```python
# Create a more customized FAQ bot
advanced_faq_agent = FAQBotAgent(
    name="technical-support",
    route="/tech-support",
    faq_content=tech_support_faqs,
    
    # Customize how to handle out-of-scope questions
    unknown_question_response="I specialize in technical support for our product line. That question seems outside my area of expertise. Would you like me to connect you with general customer service?",
    
    # Configure escalation options
    escalation_prompt="I can connect you with a human specialist if you'd prefer. Would you like me to transfer you now?",
    
    # Add additional context
    system_information={
        "product_versions": ["v1.2.3", "v1.3.0", "v2.0.1"],
        "known_issues": ["Bluetooth connectivity on v1.2.3", "Sleep mode on v2.0.1"]
    }
)
```

These configuration options allow you to adjust how the agent responds to different scenarios while maintaining its core FAQ functionality.

### ConciergeAgent for Intelligent Routing

The ConciergeAgent acts as a front-line receptionist or dispatcher, helping to understand user needs and route them to the appropriate specialized agent or department. This is particularly useful for creating entry points to multi-agent systems.

#### Configuration

Setting up a basic ConciergeAgent involves defining the available routes:

```python
from signalwire_agents.prefabs import ConciergeAgent

# Create a concierge agent for a customer service system
concierge = ConciergeAgent(
    name="customer-service-concierge",
    route="/concierge",
    routing_options=[
        {
            "name": "Technical Support",
            "description": "Help with product functionality, error messages, and troubleshooting",
            "route": "/tech-support"
        },
        {
            "name": "Billing Department",
            "description": "Questions about invoices, payments, refunds, and account status",
            "route": "/billing"
        },
        {
            "name": "Sales Team",
            "description": "Information about products, pricing, and placing new orders",
            "route": "/sales"
        }
    ]
)
```

The agent uses these routing options to determine where to direct users based on their needs.

#### How It Works

The ConciergeAgent operates through a simple flow:

1. The agent greets the user and asks how it can help
2. Based on the user's response, the agent identifies which routing option best fits their needs
3. The agent confirms the routing choice with the user
4. Once confirmed, the agent transfers the call to the appropriate specialized agent

This is implemented through a key SWAIG function:

```python
@AgentBase.tool(
    name="route_call",
    description="Route the call to the appropriate department",
    parameters={
        "destination": {
            "type": "string",
            "description": "The department to route to",
            "enum": ["Technical Support", "Billing Department", "Sales Team"]
        },
        "reason": {
            "type": "string",
            "description": "Brief reason for the routing choice"
        }
    }
)
```

#### Advanced Routing

For more sophisticated routing needs, you can extend the ConciergeAgent with additional context and logic:

```python
class EnhancedConcierge(ConciergeAgent):
    def __init__(self):
        super().__init__(
            name="enhanced-concierge",
            route="/enhanced-concierge",
            routing_options=[...]
        )
        
        # Add business hours information
        self.set_global_data({
            "business_hours": {
                "Technical Support": "24/7",
                "Billing Department": "Monday-Friday, 9am-5pm EST",
                "Sales Team": "Monday-Saturday, 8am-8pm EST"
            },
            "current_wait_times": {
                "Technical Support": "Approximately 5 minutes",
                "Billing Department": "Approximately 3 minutes",
                "Sales Team": "No wait time"
            }
        })
        
        # Enhance the routing instructions
        self.prompt_add_section("Routing Guidelines", bullets=[
            "Consider the urgency of the customer's issue",
            "Check if the appropriate department is currently available",
            "Inform the customer of expected wait times before routing",
            "If multiple departments could help, ask the customer for their preference"
        ])
    
    # Customize the pre-routing confirmation
    def pre_route_confirmation(self, destination, reason):
        # This would be called before finalizing the routing
        department = destination
        wait_time = self.get_global_data().get("current_wait_times", {}).get(department, "Unknown")
        
        return (
            f"I'll connect you with our {department} team regarding your {reason}. "
            f"The current estimated wait time is {wait_time}. "
            f"Would you like to proceed?"
        )
```

This enhanced version provides more context to both the AI and the user, creating a more informative and helpful routing experience.

### SurveyAgent for Feedback Collection

The SurveyAgent specializes in collecting structured feedback through surveys. It's ideal for customer satisfaction measurement, post-interaction feedback, and other survey-based data collection.

#### Configuration

Setting up a SurveyAgent involves defining the survey questions and rating scales:

```python
from signalwire_agents.prefabs import SurveyAgent

# Create a customer satisfaction survey agent
csat_survey = SurveyAgent(
    name="satisfaction-survey",
    route="/survey",
    introduction="We'd like to get your feedback on your recent experience with our customer service team.",
    questions=[
        {
            "type": "rating",
            "question": "How would you rate your overall experience?",
            "scale": 1,  # 1-5 scale
            "key": "overall_satisfaction"
        },
        {
            "type": "rating",
            "question": "How likely are you to recommend our service to others?",
            "scale": 2,  # 1-10 scale (NPS style)
            "key": "recommendation_score"
        },
        {
            "type": "text",
            "question": "What could we have done better?",
            "key": "improvement_feedback"
        }
    ],
    conclusion="Thank you for your feedback! We appreciate your input and will use it to improve our services."
)
```

The agent guides users through each question, collecting and storing their responses.

#### Survey Types and Formats

The SurveyAgent supports various question types and formats:

- **Rating Questions**: Numerical ratings on different scales (1-5, 1-10, etc.)
- **Multiple Choice**: Selection from a predefined list of options
- **Yes/No Questions**: Simple binary responses
- **Text Feedback**: Open-ended questions for qualitative feedback
- **Conditional Questions**: Questions that appear based on previous answers

This flexibility allows for creating sophisticated surveys that can gather both quantitative and qualitative data.

#### Custom Processing

You can extend the SurveyAgent to add custom processing of survey results:

```python
class EnhancedSurveyAgent(SurveyAgent):
    def __init__(self):
        super().__init__(
            name="enhanced-survey",
            route="/enhanced-survey",
            questions=[...]
        )
    
    # Override to add custom processing when survey completes
    def on_survey_completed(self, call_id, results):
        # Process the survey results
        print(f"Survey completed for call {call_id}")
        print(f"Results: {results}")
        
        # Calculate satisfaction metrics
        nps_score = results.get("recommendation_score", 0)
        overall_score = results.get("overall_satisfaction", 0)
        
        # Store in database, send alerts, trigger workflows, etc.
        self.store_results_in_database(call_id, results)
        
        if overall_score <= 2:  # Low satisfaction
            self.trigger_follow_up(call_id, results)
        
        # Return a customized conclusion based on the results
        if overall_score >= 4:
            return "Thank you for your positive feedback! We're glad you had a great experience."
        else:
            return "Thank you for your candid feedback. We apologize for any shortcomings and will work to improve your experience in the future."
```

This allows the survey to not just collect data but also to take immediate action based on the responses.

### Creating Custom Prefabs

While the SDK provides several useful prefab agents, you may want to create your own reusable agent templates for specific use cases. Here's how to create your own prefab:

```python
from signalwire_agents import AgentBase

class AppointmentSchedulerAgent(AgentBase):
    """
    A prefab agent for scheduling appointments.
    """
    
    def __init__(
        self,
        name="appointment-scheduler",
        route="/appointments",
        available_services=None,
        available_times=None,
        confirmation_required=True,
        **kwargs
    ):
        """
        Initialize an appointment scheduler agent.
        
        Args:
            name: Agent name
            route: HTTP route
            available_services: List of services that can be scheduled
            available_times: Dict of available time slots by date
            confirmation_required: Whether to require confirmation before finalizing
            **kwargs: Additional arguments for AgentBase
        """
        # Initialize the base agent
        super().__init__(
            name=name,
            route=route,
            use_pom=True,
            **kwargs
        )
        
        # Store configuration
        self.available_services = available_services or ["Consultation", "Follow-up"]
        self.available_times = available_times or self._default_availability()
        self.confirmation_required = confirmation_required
        
        # Set up global data
        self.set_global_data({
            "available_services": self.available_services,
            "available_times": self.available_times
        })
        
        # Build prompts
        self._build_prompt()
        
        # Register functions
        self._register_functions()
    
    def _default_availability(self):
        """Generate default availability if none provided"""
        from datetime import datetime, timedelta
        
        availability = {}
        start_date = datetime.now().date()
        
        # Generate availability for the next 7 days
        for i in range(7):
            date = start_date + timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            # 9am-5pm, hourly slots
            times = []
            for hour in range(9, 17):
                times.append(f"{hour:02d}:00")
            
            availability[date_str] = times
        
        return availability
    
    def _build_prompt(self):
        """Build the agent's prompt"""
        self.prompt_add_section(
            "Personality",
            body="You are a helpful appointment scheduling assistant."
        )
        
        self.prompt_add_section(
            "Goal",
            body="Help users schedule appointments efficiently by gathering the necessary information and finding a suitable time slot."
        )
        
        self.prompt_add_section(
            "Instructions",
            bullets=[
                "Ask for the type of service they need",
                "Find out their preferred date and time",
                "Suggest alternative times if their preference is unavailable",
                "Collect contact information",
                "Confirm all details before finalizing"
            ]
        )
    
    def _register_functions(self):
        """Register SWAIG functions"""
        # Functions would be defined here
        pass
    
    # SWAIG functions would be defined here
    @AgentBase.tool(
        name="check_availability",
        description="Check availability for a specific date",
        parameters={
            "date": {"type": "string", "description": "Date to check (YYYY-MM-DD)"}
        }
    )
    def check_availability(self, args, raw_data):
        date = args.get("date")
        available_times = self.available_times.get(date, [])
        
        if not available_times:
            return SwaigFunctionResult(f"I'm sorry, there are no available times on {date}.")
        
        result = SwaigFunctionResult(
            f"The following times are available on {date}: {', '.join(available_times)}"
        )
        
        return result
    
    # Additional functions for booking, rescheduling, etc.
```

Once defined, this custom prefab can be used just like the built-in ones:

```python
# Create an instance with custom configuration
scheduler = AppointmentSchedulerAgent(
    name="medical-appointments",
    route="/medical-appointments",
    available_services=[
        "Initial Consultation",
        "Follow-up",
        "Annual Physical",
        "Vaccination"
    ],
    custom_availability=medical_office_hours  # Custom availability data
)

# Or with defaults
simple_scheduler = AppointmentSchedulerAgent()
```

Custom prefabs allow you to encapsulate complex behavior in reusable components, making it easier to create consistent agents across your organization.

By leveraging these prefab agents, you can quickly deploy sophisticated AI voice agents without having to build everything from scratch. Whether you use them as-is or extend them with custom functionality, prefabs provide a solid foundation for many common use cases.

## 7. Best Practices and Patterns

When building AI voice agents, consider these best practices and patterns:

### Effective Prompt Design

Design prompts that are clear, concise, and contextually relevant. Use the Prompt Object Model (POM) to structure prompts and ensure they are maintainable and effective.

### Function Organization

Organize functions logically and logically. Use clear names and descriptions to help the AI understand when to use each function.

### Security Considerations

Ensure that functions are secure and that sensitive operations are protected. Use token-based authentication and other security measures to safeguard your agents.

### Performance Optimization

Optimize functions for speed and efficiency. Use fillers for longer operations and ensure that functions are fast when possible.

### Deployment Strategies

Consider different deployment strategies for your agents. Run as standalone services or integrate multiple agents into a cohesive system.

## 8. Real-World Examples

Here are some real-world examples of how AI voice agents can be used:

### Customer Service Automation

AI voice agents can provide personalized, efficient service at scale. They can handle telephone calls, respond to user queries, and perform actions through custom functions.

### Appointment Scheduling

AI voice agents can help users schedule appointments and manage their schedules. They can handle complex workflows and provide relevant information.

### Technical Support

AI voice agents can provide technical support and help users resolve issues. They can handle complex interactions and provide relevant information.

### Lead Qualification

AI voice agents can help qualify leads and determine their suitability for your services. They can handle complex interactions and provide relevant information.

### Surveys and Information Collection

AI voice agents can help collect feedback and information from users. They can handle complex interactions and provide relevant information.

## 9. Conclusion

The SignalWire AI Agents SDK provides powerful tools to create, deploy, and manage conversational AI agents with minimal effort. By leveraging the full power of the SDK, you can create engaging, intelligent voice experiences that can transform key touchpoints throughout the customer journey.

### Future Directions

The future of AI voice agents is bright. With advancements in natural language processing and machine learning, AI agents will become more sophisticated and capable. Consider exploring new features and capabilities to further enhance your agents.

### Community and Support

Join the SignalWire community to connect with other developers, share ideas, and get support. Visit the SignalWire community forums or contact the SignalWire support team for assistance.

- Discord: https://signalwire.community
- Docs: https://developer.signalwire.com
- AI: https://signalwire.ai
- Main Site: https://signalwire.com

### Getting Started

Ready to get started with the SignalWire AI Agents SDK? Follow the steps in the documentation to set up your development environment and start building your first agent.

By following these steps, you'll be well on your way to creating powerful, production-ready AI voice agents that can transform your customer engagement strategy. 
