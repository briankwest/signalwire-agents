# SignalWire AI Agents SDK Architecture

## Overview

The SignalWire AI Agents SDK provides a Python framework for building, deploying, and managing AI agents as microservices. These agents are self-contained web applications that expose HTTP endpoints to interact with the SignalWire platform. The SDK simplifies the creation of custom AI agents by handling common functionality like HTTP routing, prompt management, and tool execution.

## Core Components

### Class Hierarchy

The SDK is built around a clear class hierarchy:

- **SWMLService**: The foundation class providing SWML document creation and HTTP service capabilities
  - **AgentBase**: Extends SWMLService with AI agent-specific functionality
    - **Custom Agent Classes**: User implementations like SimpleAgent
    - **Prefab Agents**: Ready-to-use agent types for common scenarios

### Key Components

1. **SWML Document Management**
   - Schema validation for SWML documents
   - Dynamic SWML verb creation and validation
   - Document rendering and serving

2. **Prompt Object Model (POM)**
   - Structured format for defining AI prompts
   - Section-based organization (Personality, Goal, Instructions, etc.)
   - Programmatic prompt construction and manipulation

3. **SWAIG Function Framework**
   - Tool definition and registration system
   - Parameter validation using JSON schema
   - Security tokens for function execution
   - Handler registry for function execution

4. **HTTP Routing**
   - FastAPI-based web service
   - Endpoint routing for SWML, SWAIG, and other services
   - Custom routing callbacks for dynamic endpoint handling
   - SIP request routing for voice applications
   - Basic authentication

5. **State Management**
   - Session-based state tracking
   - Persistence options (file system, memory)
   - State lifecycle hooks (startup, hangup)

6. **Prefab Agents**
   - Ready-to-use agent implementations
   - Customizable configurations
   - Extensible designs for common use cases

7. **Skills System**
   - Modular skill architecture for extending agent capabilities
   - Automatic skill discovery from directory structure
   - Parameter-configurable skills for customization
   - Dependency validation (packages and environment variables)
   - Built-in skills (web_search, datetime, math)

## Request Flow

### SWML Document Request (GET/POST /)

1. Client requests the root endpoint
2. Authentication is validated 
3. `on_swml_request()` is called to allow customization
4. Current SWML document is rendered and returned

### SWAIG Function Call (POST /swaig/)

1. Client sends a POST request to the SWAIG endpoint
2. Authentication is validated
3. Function name and arguments are extracted
4. Token validation occurs for secure functions
5. Function is executed and result returned

### Post-Prompt Processing (POST /post_prompt/)

1. Client sends conversation summary data
2. Authentication is validated
3. Summary is extracted from request
4. `on_summary()` is called to process the data

## State Management

The SDK provides a flexible state management system:

```
┌───────────────┐     ┌─────────────────┐     ┌───────────────┐
│ Session       │     │ State           │     │ Persistence   │
│ Management    │━━━━▶│ Manager         │━━━━▶│ Layer         │
└───────────────┘     └─────────────────┘     └───────────────┘
```

Components:
- **SessionManager**: Handles session creation, activation, and termination
- **StateManager**: Interface for state operations
- **Implementation Options**: FileStateManager, MemoryStateManager, etc.

State is indexed by call ID and can store arbitrary JSON data. When `enable_state_tracking=True` is set, the system automatically registers lifecycle hooks:
- **startup_hook**: Called when a new call/session starts
- **hangup_hook**: Called when a call/session ends

Common state management methods:
- `get_state(call_id)`: Retrieve state for a call
- `update_state(call_id, data)`: Update state for a call
- `set_state(call_id, data)`: Set state for a call (overriding existing)
- `clear_state(call_id)`: Remove state for a call

## Skills System

The Skills System provides a modular architecture for extending agent capabilities through self-contained, reusable components. Skills are automatically discovered, validated, and can be configured with parameters.

### Architecture Overview

The skills system follows a three-layer architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Agent Layer     │    │ Management      │    │ Skills Layer    │
│                 │    │ Layer           │    │                 │
│ AgentBase       │━━━▶│ SkillManager    │━━━▶│ SkillBase       │
│ .add_skill()    │    │ .load_skill()   │    │ .setup()        │
│                 │    │ .unload_skill() │    │ .register_tools()│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
    ┌────▼────┐             ┌────▼────┐             ┌────▼────┐
    │Request  │             │Registry │             │Skill    │
    │Routing  │             │Discovery│             │Instance │
    │         │             │         │             │         │
    └─────────┘             └─────────┘             └─────────┘
```

### Core Components

1. **SkillBase**: Abstract base class defining the skill interface
   - Dependency validation (packages and environment variables)
   - Tool registration with the agent
   - Parameter support for configuration
   - Lifecycle management (setup, cleanup)

2. **SkillManager**: Manages skill loading and lifecycle
   - Skill discovery and registration
   - Dependency validation and error reporting
   - Parameter passing to skills
   - Integration with agent prompt and tool systems

3. **SkillRegistry**: Automatic skill discovery system
   - Directory-based skill discovery
   - Class introspection and registration
   - Metadata extraction for skill information

### Skill Lifecycle

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Discovery       │    │ Loading         │    │ Registration    │
│                 │    │                 │    │                 │
│ 1. Scan dirs    │━━━▶│ 1. Validate     │━━━▶│ 1. Add tools    │
│ 2. Import mods  │    │    deps         │    │ 2. Add prompts  │
│ 3. Find classes │    │ 2. Create       │    │ 3. Add hints    │
│ 4. Register     │    │    instance     │    │ 4. Store ref    │
│                 │    │ 3. Call setup() │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Parameter System

Skills support configurable parameters for customization:

```python
# Default behavior
agent.add_skill("web_search")

# Custom configuration
agent.add_skill("web_search", {
    "num_results": 3,
    "delay": 0.5
})
```

Parameters are passed to the skill constructor and accessible via `self.params`:

```python
class WebSearchSkill(SkillBase):
    def setup(self) -> bool:
        self.num_results = self.params.get('num_results', 1)
        self.delay = self.params.get('delay', 0)
        # Configure behavior based on parameters
```

### Error Handling

The system provides detailed error reporting for common issues:

- **Missing Dependencies**: Lists specific missing packages or environment variables
- **Discovery Failures**: Reports issues during skill discovery or import
- **Setup Failures**: Provides details when skill setup fails
- **Parameter Validation**: Validates parameter types and values

Error messages are actionable and specific:
```
Failed to load skill 'web_search': Missing required environment variables: ['GOOGLE_SEARCH_API_KEY', 'GOOGLE_SEARCH_ENGINE_ID']
```

### Integration Points

Skills integrate seamlessly with existing agent systems:

1. **SWAIG Tools**: Skills register tools that become available to the AI
2. **Prompt System**: Skills can add prompt sections and hints
3. **Global Data**: Skills can contribute to agent context
4. **State Management**: Skills can access agent state if needed

This architecture enables powerful one-liner integration while maintaining flexibility and extensibility.

## Security Model

The SDK implements a multi-layer security model:

1. **Transport Security**
   - HTTPS support for encrypted communications
   - SSL certificate configuration

2. **Authentication**
   - HTTP Basic Authentication for all endpoints
   - Configurable via environment variables or programmatically

3. **Authorization**
   - Function-specific security tokens
   - Token validation for secure function calls
   - SessionManager-based security scope
   - `secure=True` option on tool definitions (default)

4. **State Isolation**
   - Per-call state separation
   - Call ID validation

## Extension Points

The SDK is designed to be highly extensible:

1. **Custom Agents**: Extend AgentBase to create specialized agents
   ```python
   class CustomAgent(AgentBase):
       def __init__(self):
           super().__init__(name="custom", route="/custom")
   ```

2. **Tool Registration**: Add new tools using the decorator pattern
   ```python
   @AgentBase.tool(
       name="tool_name", 
       description="Tool description",
       parameters={...},
       secure=True
   )
   def my_tool(self, args, raw_data):
       # Tool implementation
   ```

3. **Prompt Customization**: Add sections, hints, languages
   ```python
   agent.add_language(name="English", code="en-US", voice="elevenlabs.josh")
   agent.add_hints(["SignalWire", "SWML", "SWAIG"])
   ```

4. **State Management**: Implement custom state persistence
   ```python
   class CustomStateManager(StateManager):
       def get_state(self, call_id):
           # Implementation
   ```

5. **Request Handling**: Override request handling methods
   ```python
   def on_swml_request(self, request_data):
       # Custom request handling
   ```

6. **Custom Prefabs**: Create reusable agent patterns
   ```python
   class MyCustomPrefab(AgentBase):
       def __init__(self, config_param1, config_param2, **kwargs):
           super().__init__(**kwargs)
           # Configure the agent based on parameters
           self.prompt_add_section("Personality", body=f"Customized based on: {config_param1}")
   ```

7. **Dynamic Configuration**: Per-request agent configuration for flexible behavior
   ```python
   def configure_agent_dynamically(self, query_params, body_params, headers, agent):
       # Configure agent differently based on request data
       tier = query_params.get('tier', 'standard')
       agent.set_params({"end_of_speech_timeout": 300 if tier == 'premium' else 500})
   
   self.set_dynamic_config_callback(self.configure_agent_dynamically)
   ```

8. **Skills Integration**: Add capabilities with one-liner calls
   ```python
   # Add built-in skills
   agent.add_skill("web_search")
   agent.add_skill("datetime")
   agent.add_skill("math")
   
   # Configure skills with parameters
   agent.add_skill("web_search", {
       "num_results": 3,
       "delay": 0.5
   })
   ```

9. **Custom Skills**: Create reusable skill modules
   ```python
   from signalwire_agents.core.skill_base import SkillBase
   
   class MyCustomSkill(SkillBase):
       SKILL_NAME = "my_skill"
       SKILL_DESCRIPTION = "A custom skill"
       REQUIRED_PACKAGES = ["requests"]
       REQUIRED_ENV_VARS = ["API_KEY"]
       
       def setup(self) -> bool:
           # Initialize the skill
           return True
           
       def register_tools(self) -> None:
           # Register tools with the agent
           self.agent.define_tool(...)
   ```

### Dynamic Configuration

The dynamic configuration system enables agents to adapt their behavior on a per-request basis by examining incoming HTTP request data. This architectural pattern supports complex use cases like multi-tenant applications, A/B testing, and personalization while maintaining a single agent deployment.

#### Architecture Overview

Dynamic configuration intercepts the SWML document generation process to apply request-specific configuration:

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────────┐    ┌──────────────┐
│ HTTP        │    │ Dynamic Config   │    │ EphemeralAgent      │    │ SWML         │
│ Request     │━━━▶│ Callback         │━━━▶│ Config              │━━━▶│ Document     │
└─────────────┘    └──────────────────┘    └─────────────────────┘    └──────────────┘
       │                     │                        │                      │
       │                     │                        │                      │
   ┌───▼────┐           ┌────▼─────┐            ┌─────▼──────┐          ┌────▼────┐
   │Query   │           │Request   │            │Agent       │          │Rendered │
   │Params  │           │Data      │            │Builder     │          │Response │
   │Body    │           │Analysis  │            │Methods     │          │         │
   │Headers │           │Logic     │            │Execution   │          │         │
   └────────┘           └──────────┘            └────────────┘          └─────────┘
```

#### Component Interaction

1. **Request Processing**: The framework extracts query parameters, body data, and headers from incoming requests
2. **Callback Invocation**: If a dynamic configuration callback is registered, it's called with the request data
3. **Ephemeral Configuration**: The callback configures an `EphemeralAgentConfig` object using familiar AgentBase methods
4. **SWML Generation**: The configuration is applied during SWML document rendering
5. **Response Delivery**: The customized SWML document is returned to the client

#### Request Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Dynamic Configuration Request Flow                                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ 1. HTTP Request arrives (GET/POST /)                                          │
│                         │                                                       │
│ 2. Extract request data │                                                       │
│    ┌────────────────────▼────────────────────┐                                 │
│    │ • Query Parameters (URL params)        │                                 │
│    │ • Body Parameters (POST JSON)          │                                 │
│    │ • Headers (HTTP headers)               │                                 │
│    └────────────────────┬────────────────────┘                                 │
│                         │                                                       │
│ 3. Check for callback   │                                                       │
│    ┌────────────────────▼────────────────────┐                                 │
│    │ if dynamic_config_callback is set:     │                                 │
│    │   - Create EphemeralAgentConfig        │                                 │
│    │   - Call callback with request data    │                                 │
│    │   - Apply ephemeral configuration      │                                 │
│    │ else:                                   │                                 │
│    │   - Use static agent configuration     │                                 │
│    └────────────────────┬────────────────────┘                                 │
│                         │                                                       │
│ 4. Generate SWML        │                                                       │
│    ┌────────────────────▼────────────────────┐                                 │
│    │ • Render AI verb with configuration    │                                 │
│    │ • Include languages, params, prompts   │                                 │
│    │ • Apply hints and global data          │                                 │
│    │ • Generate function URLs with tokens   │                                 │
│    └────────────────────┬────────────────────┘                                 │
│                         │                                                       │
│ 5. Return SWML Document │                                                       │
│    ┌────────────────────▼────────────────────┐                                 │
│    │ • Complete SWML with customizations    │                                 │
│    │ • Ready for SignalWire platform        │                                 │
│    └─────────────────────────────────────────┘                                 │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### EphemeralAgentConfig Architecture

The `EphemeralAgentConfig` object provides the same familiar methods as `AgentBase` but applies them temporarily for a single request:

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ EphemeralAgentConfig Structure                                                │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│ ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐              │
│ │ Prompt Sections │   │ Language Config │   │ AI Parameters   │              │
│ │ ─────────────── │   │ ─────────────── │   │ ─────────────── │              │
│ │ • add_section() │   │ • add_language()│   │ • set_params()  │              │
│ │ • set_prompt()  │   │ • voice config  │   │ • timeouts      │              │
│ │ • post_prompt   │   │ • fillers       │   │ • volumes       │              │
│ └─────────────────┘   └─────────────────┘   └─────────────────┘              │
│                                                                               │
│ ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐              │
│ │ Global Data     │   │ Hints & Speech  │   │ Functions       │              │
│ │ ─────────────── │   │ ─────────────── │   │ ─────────────── │              │
│ │ • set_global()  │   │ • add_hints()   │   │ • native_funcs()│              │
│ │ • update_data() │   │ • pronunciation │   │ • recognition   │              │
│ │ • session data  │   │ • recognition   │   │ • external URLs │              │
│ └─────────────────┘   └─────────────────┘   └─────────────────┘              │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

#### Performance Considerations

The dynamic configuration system is designed with performance in mind:

1. **Lightweight Callbacks**: Configuration callbacks should be fast and avoid heavy computations
2. **Stateless Operation**: Each request is processed independently without shared state
3. **Ephemeral Scope**: Configuration objects are created per-request and garbage collected afterward
4. **Caching Opportunities**: External configuration data can be cached at the application level

#### Memory Management

```
Request 1 ┌─────────────┐    Request 2 ┌─────────────┐    Request 3 ┌─────────────┐
Lifecycle │ CREATE      │    Lifecycle │ CREATE      │    Lifecycle │ CREATE      │
          │ EphemeralCfg│              │ EphemeralCfg│              │ EphemeralCfg│
          │ ↓           │              │ ↓           │              │ ↓           │
          │ CONFIGURE   │              │ CONFIGURE   │              │ CONFIGURE   │
          │ ↓           │              │ ↓           │              │ ↓           │
          │ RENDER SWML │              │ RENDER SWML │              │ RENDER SWML │
          │ ↓           │              │ ↓           │              │ ↓           │
          │ DESTROY     │              │ DESTROY     │              │ DESTROY     │
          └─────────────┘              └─────────────┘              └─────────────┘
               │                             │                             │
               ▼                             ▼                             ▼
          Garbage                       Garbage                       Garbage
          Collection                    Collection                    Collection
```

#### Use Case Patterns

The dynamic configuration architecture supports several key patterns:

1. **Multi-Tenant Applications**
   ```
   ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
   │ Tenant A    │    │ Same Agent   │    │ Config A    │
   │ Request     │━━━▶│ Instance     │━━━▶│ Applied     │
   └─────────────┘    └──────────────┘    └─────────────┘
   
   ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
   │ Tenant B    │    │ Same Agent   │    │ Config B    │
   │ Request     │━━━▶│ Instance     │━━━▶│ Applied     │
   └─────────────┘    └──────────────┘    └─────────────┘
   ```

2. **A/B Testing and Experimentation**
   ```
   ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
   │ Control     │    │ Decision     │    │ Version A   │
   │ Group       │━━━▶│ Logic        │━━━▶│ Config      │
   └─────────────┘    └──────────────┘    └─────────────┘
   
   ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
   │ Test        │    │ Decision     │    │ Version B   │
   │ Group       │━━━▶│ Logic        │━━━▶│ Config      │
   └─────────────┘    └──────────────┘    └─────────────┘
   ```

3. **Geographic and Cultural Localization**
   ```
   ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
   │ US Request  │    │ Locale       │    │ English     │
   │ (en-US)     │━━━▶│ Detection    │━━━▶│ Voice + USD │
   └─────────────┘    └──────────────┘    └─────────────┘
   
   ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
   │ MX Request  │    │ Locale       │    │ Spanish     │
   │ (es-MX)     │━━━▶│ Detection    │━━━▶│ Voice + MXN │
   └─────────────┘    └──────────────┘    └─────────────┘
   ```

#### Integration Points

Dynamic configuration integrates with other SDK components:

- **State Management**: Can access and configure state based on request data
- **SWAIG Functions**: Functions are generated with proper URLs and security tokens
- **SIP Routing**: Can be combined with SIP username routing for voice applications
- **Authentication**: Respects existing authentication mechanisms
- **Logging**: Configuration decisions can be logged for debugging and analytics

#### Error Handling and Fallbacks

The system includes robust error handling:

```python
def configure_agent_dynamically(self, query_params, body_params, headers, agent):
    try:
        # Primary configuration logic
        self.apply_custom_config(query_params, agent)
    except ConfigurationError as e:
        # Log error and apply safe defaults
        self.log.error("dynamic_config_error", error=str(e))
        self.apply_default_config(agent)
    except Exception as e:
        # Catch-all with minimal safe configuration
        self.log.error("dynamic_config_critical", error=str(e))
        agent.add_language("English", "en-US", "rime.spore:mistv2")
```

#### Migration Strategy

The architecture supports gradual migration from static to dynamic configuration:

1. **Phase 1**: Deploy dynamic agent with static configuration callback
2. **Phase 2**: Add request parameter detection and basic customization
3. **Phase 3**: Implement full dynamic behavior based on use case requirements
4. **Phase 4**: Remove static configuration and rely entirely on dynamic system

This approach ensures zero downtime and allows for testing and validation at each phase.

## Prefab Agents

The SDK includes a collection of prefab agents that provide ready-to-use implementations for common use cases. These prefabs can be used directly or serve as templates for custom implementations.

### Built-in Prefab Types

1. **InfoGathererAgent**
   - Purpose: Collect specific information from users in a structured conversation
   - Configuration: Define fields to collect, validation rules, and confirmation templates
   - Use cases: Form filling, survey collection, intake processes

2. **FAQBotAgent**
   - Purpose: Answer questions based on a provided knowledge base
   - Configuration: Data sources, retrieval methods, citation options
   - Use cases: FAQ bots, documentation assistants, support agents

3. **ConciergeAgent**
   - Purpose: Handle routing and delegation between multiple specialized agents
   - Configuration: Connected agents, routing logic, handoff protocols
   - Use cases: Front-desk services, triage systems, switchboard operators

4. **SurveyAgent**
   - Purpose: Conduct structured surveys with rating scales and open-ended questions
   - Configuration: Survey questions, rating scales, branching logic
   - Use cases: Customer satisfaction surveys, feedback collection, market research

5. **ReceptionistAgent**
   - Purpose: Greet callers and transfer them to appropriate departments
   - Configuration: Department list with names, descriptions, and transfer numbers
   - Use cases: Call routing, front desk services, automated phone systems

### Creating Custom Prefabs

Users can create their own prefab agents by extending `AgentBase` or any existing prefab. Custom prefabs can be created within your project or packaged as reusable libraries.

Key steps for creating custom prefabs:

1. **Extend the base class**:
   ```python
   class MyCustomPrefab(AgentBase):
       def __init__(self, custom_param, **kwargs):
           super().__init__(**kwargs)
           self._custom_param = custom_param
   ```

2. **Configure defaults**:
   ```python
   # Set standard prompt sections
   self.prompt_add_section("Personality", body="I am a specialized agent for...")
   self.prompt_add_section("Goal", body="Help users with...")
   
   # Add default tools
   self.register_default_tools()
   ```

3. **Add specialized tools**:
   ```python
   @AgentBase.tool(
       name="specialized_function", 
       description="Do something specialized",
       parameters={...}
   )
   def specialized_function(self, args, raw_data):
       # Implementation
       return SwaigFunctionResult("Function result")
   ```

4. **Create a factory method** (optional):
   ```python
   @classmethod
   def create(cls, config_dict, **kwargs):
       """Create an instance from a configuration dictionary"""
       return cls(
           custom_param=config_dict.get("custom_param", "default"),
           name=config_dict.get("name", "custom_prefab"),
           **kwargs
       )
   ```

### Prefab Customization Points

When designing prefabs, consider exposing these customization points:

1. **Constructor parameters**: Allow users to configure key behavior
2. **Override methods**: Document which methods can be safely overridden
3. **Extension hooks**: Provide callback methods for custom logic
4. **Configuration files**: Support loading settings from external sources
5. **Runtime customization**: Allow changing behavior after initialization

### Prefab Best Practices

1. **Clear Documentation**: Document the purpose, parameters, and extension points
2. **Sensible Defaults**: Provide working defaults that make sense for the use case
3. **Error Handling**: Implement robust error handling with helpful messages
4. **Modular Design**: Keep prefabs focused on a specific use case
5. **Consistent Interface**: Maintain consistent patterns across related prefabs

## Implementation Details

### POM Structure

The POM (Prompt Object Model) represents a structured approach to prompt construction:

```
┌───────────────────────────────────────────────┐
│ Prompt                                        │
├───────────────────────────────────────────────┤
│ ┌─────────────────┐  ┌─────────────────────┐  │
│ │ Personality     │  │ Goal                │  │
│ └─────────────────┘  └─────────────────────┘  │
│ ┌─────────────────┐  ┌─────────────────────┐  │
│ │ Instructions    │  │ Hints               │  │
│ └─────────────────┘  └─────────────────────┘  │
│ ┌─────────────────┐  ┌─────────────────────┐  │
│ │ Languages       │  │ Custom Sections     │  │
│ └─────────────────┘  └─────────────────────┘  │
└───────────────────────────────────────────────┘
```

### SWAIG Function Definition

Functions are defined with:
- Name
- Description
- Parameters schema
- Implementation
- Security settings

Example:
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
    location = args.get("location", "Unknown location")
    return SwaigFunctionResult(f"It's sunny and 72°F in {location}.")
```

### HTTP Routing

The SDK uses FastAPI for routing with these key endpoints:

- **/** (GET/POST): Main endpoint that returns the SWML document
- **/swaig/** (POST): Endpoint for executing SWAIG functions
- **/post_prompt/** (POST): Endpoint for receiving conversation summaries
- **/sip/** (GET/POST): Optional endpoint for SIP routing

The SDK also supports dynamic creation of custom routing endpoints:

- **Custom routing callbacks**: Register callbacks for specific paths (e.g., `/customer`, `/product`)
- **Dynamic content serving**: Serve different SWML documents based on the request path
- **Request inspection**: Examine request data to make routing decisions
- **Redirection**: Optionally redirect requests to other endpoints

## Deployment Options

The SDK supports multiple deployment models:

1. **Standalone Mode**
   - Single agent on dedicated port
   - Direct invocation via `agent.serve()`

2. **Multi-Agent Mode**
   - Multiple agents on same server with different routes
   - `app.include_router(agent.as_router(), prefix=agent.route)`

3. **Reverse Proxy Integration**
   - Set `SWML_PROXY_URL_BASE` for proper webhook URL generation
   - Enable SSL termination at proxy level

4. **Direct HTTPS Mode**
   - Configure with SSL certificates
   - `agent.serve(ssl_cert="cert.pem", ssl_key="key.pem")`

## Best Practices

1. **Prompt Structure**
   - Use POM for clear, structured prompts
   - Keep personality and goal sections concise
   - Use specific instructions for behavior guidance

2. **SWAIG Functions**
   - Define clear parameter schemas
   - Provide comprehensive descriptions for AI context
   - Implement proper error handling
   - Return structured responses

3. **State Management**
   - Store essential conversation context in state
   - Enable automatic state tracking with `enable_state_tracking=True`
   - Use secure state storage for sensitive data

4. **Security**
   - Use HTTPS in production
   - Set strong authentication credentials
   - Enable security for sensitive operations with `secure=True`

5. **Deployment**
   - Use environment variables for configuration
   - Implement proper logging
   - Monitor agent performance and usage

6. **Prefab Usage**
   - Use existing prefabs for common patterns
   - Extend prefabs rather than starting from scratch
   - Create your own prefabs for reusable patterns
   - Share prefabs across projects for consistency

## Schema Validation

The SDK uses JSON Schema validation for:
- SWML document structure
- POM section validation
- SWAIG function parameter validation

Schema definitions are loaded from the `schema.json` file, which provides the complete specification for all supported SWML verbs and structures.

## Logging

The SDK uses structlog for structured logging with JSON output format. Key events logged include:
- Service initialization
- Request handling
- Function execution
- Authentication events
- Error conditions

## Configuration

Configuration options are available through:
1. **Constructor Parameters**: Direct configuration in code
2. **Environment Variables**: System-level configuration
3. **Method Calls**: Runtime configuration updates

Key environment variables:
- `SWML_BASIC_AUTH_USER`: Username for basic auth
- `SWML_BASIC_AUTH_PASSWORD`: Password for basic auth
- `SWML_PROXY_URL_BASE`: Base URL when behind reverse proxy
- `SWML_SSL_ENABLED`: Enable HTTPS
- `SWML_SSL_CERT_PATH`: Path to SSL certificate
- `SWML_SSL_KEY_PATH`: Path to SSL key
- `SWML_DOMAIN`: Domain name for the service
- `SWML_SCHEMA_PATH`: Optional path to override the schema.json location