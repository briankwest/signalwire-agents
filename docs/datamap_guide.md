# DataMap Guide

The DataMap system allows you to create SWAIG tools that integrate directly with REST APIs without requiring custom webhook endpoints. DataMap tools execute on the SignalWire server, making them simpler to deploy and manage than traditional webhook-based tools.

## Table of Contents

- [Overview](#overview)
- [Basic Usage](#basic-usage)
- [Core Concepts](#core-concepts)
- [Variable Expansion](#variable-expansion)
- [Webhook Configuration](#webhook-configuration)
- [Expression-Based Tools](#expression-based-tools)
- [Array Processing](#array-processing)
- [Error Handling](#error-handling)
- [Helper Functions](#helper-functions)
- [Real-World Examples](#real-world-examples)
- [Best Practices](#best-practices)
- [API Reference](#api-reference)

## Overview

DataMap tools provide a declarative way to define API integrations that run on SignalWire's infrastructure. Instead of creating webhook endpoints, you describe the API call and response processing using a fluent builder interface.

### Benefits

- **Serverless execution**: No need to host webhook endpoints
- **Simplified deployment**: No infrastructure to manage
- **Built-in authentication**: Support for various auth methods
- **Response processing**: JSON path traversal and array iteration
- **Error handling**: Automatic error detection
- **Variable expansion**: Dynamic parameter substitution

### When to Use DataMap vs Skills vs Custom Tools

- **DataMap**: Simple REST API integrations, no complex processing needed
- **Skills**: Complex multi-step workflows, custom logic, state management
- **Custom Tools**: Full control over execution, database access, complex business logic

## Basic Usage

```python
from signalwire_agents import AgentBase
from signalwire_agents.core.data_map import DataMap
from signalwire_agents.core.function_result import SwaigFunctionResult

class WeatherAgent(AgentBase):
    def __init__(self):
        super().__init__(name="weather-agent", route="/weather")
        
        # Create a weather API tool
        weather_tool = (DataMap('get_weather')
            .description('Get current weather information')
            .parameter('location', 'string', 'City name', required=True)
            .webhook('GET', 'https://api.weather.com/v1/current?key=YOUR_API_KEY&q=${location}')
            .output(SwaigFunctionResult('Weather in ${location}: ${response.current.condition.text}, ${response.current.temp_f}°F'))
        )
        
        # Register the tool
        self.register_swaig_function(weather_tool.to_swaig_function())

agent = WeatherAgent()
agent.serve()
```

## Core Concepts

### DataMap Builder Pattern

DataMap uses a fluent interface where methods can be chained together:

```python
tool = (DataMap('function_name')
    .description('What this function does')
    .parameter('param1', 'string', 'Parameter description', required=True)
    .webhook('GET', 'https://api.example.com/endpoint')
    .output(SwaigFunctionResult('Response: ${response.field}'))
)
```

### Processing Pipeline

DataMap tools follow this execution order:

1. **Expressions**: Pattern matching against arguments (if defined)
2. **Webhooks**: API calls (if expressions don't match)
3. **Foreach**: Array processing (if webhook returns array)
4. **Output**: Final response generation

The pipeline stops at the first successful step.

## Variable Expansion

DataMap supports powerful variable substitution using `${variable}` syntax:

### Available Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `${args.param_name}` | Function arguments | `${args.location}` |
| `${response.field}` | API response data | `${response.current.temp_f}` |
| `${foreach.field}` | Current array item | `${foreach.title}` |
| `${global_data.key}` | Agent global data | `${global_data.user_id}` |
| `${meta_data.call_id}` | Call metadata | `${meta_data.call_id}` |

### JSON Path Traversal

Variables support nested object access and array indexing:

```python
# Nested objects
'${response.current.condition.text}'

# Array indexing  
'${response.results[0].title}'

# Complex paths
'${response.data.users[2].profile.name}'
```

### Examples

```python
# URL parameter substitution
.webhook('GET', 'https://api.weather.com/v1/current?key=${global_data.api_key}&q=${args.location}')

# Request body templating
.body({
    'query': '${args.search_term}',
    'user_id': '${global_data.user_id}',
    'limit': 10
})

# Response formatting
.output(SwaigFunctionResult('Found ${response.total_results} results for "${args.query}"'))
```

## Webhook Configuration

### HTTP Methods

```python
# GET request
.webhook('GET', 'https://api.example.com/data?param=${args.value}')

# POST request with JSON body
.webhook('POST', 'https://api.example.com/create')
.body({'name': '${args.name}', 'value': '${args.value}'})

# PUT request with authentication
.webhook('PUT', 'https://api.example.com/update/${args.id}', 
         headers={'Authorization': 'Bearer ${global_data.token}'})
.body({'status': '${args.status}'})
```

### Authentication

```python
# API key in URL
.webhook('GET', 'https://api.service.com/data?key=${global_data.api_key}&q=${args.query}')

# Bearer token
.webhook('POST', 'https://api.service.com/search',
         headers={'Authorization': 'Bearer ${global_data.token}'})

# Basic auth
.webhook('GET', 'https://api.service.com/data',
         headers={'Authorization': 'Basic ${global_data.credentials}'})

# Custom headers
.webhook('GET', 'https://api.service.com/data',
         headers={
             'X-API-Key': '${global_data.api_key}',
             'X-Client-ID': '${global_data.client_id}',
             'Content-Type': 'application/json'
         })
```

## Expression-Based Tools

For simple pattern matching without API calls, use expressions:

```python
file_control = (DataMap('file_control')
    .description('Control file playback')
    .parameter('command', 'string', 'Playback command')
    .parameter('filename', 'string', 'File to control', required=False)
    .expression(r'start.*', SwaigFunctionResult().add_action('start_playback', {'file': '${args.filename}'}))
    .expression(r'stop.*', SwaigFunctionResult().add_action('stop_playback', True))
    .expression(r'pause.*', SwaigFunctionResult().add_action('pause_playback', True))
)
```

### Expression Patterns

```python
# Exact match
.expression('hello', SwaigFunctionResult('Hello response'))

# Case-insensitive regex
.expression(r'(?i)weather.*', SwaigFunctionResult('Weather info'))

# Multiple patterns
.expression(r'start|begin|play', SwaigFunctionResult().add_action('start', True))
.expression(r'stop|end|pause', SwaigFunctionResult().add_action('stop', True))
```

## Array Processing

When an API returns an array, use `foreach` to process each item:

```python
search_tool = (DataMap('search_docs')
    .description('Search documentation')
    .parameter('query', 'string', 'Search query', required=True)
    .webhook('GET', 'https://api.docs.com/search?q=${args.query}')
    .foreach('${response.results}')  # Process each result
    .output(SwaigFunctionResult('Document: ${foreach.title} - ${foreach.summary}'))
)
```

### Array Response Example

If the API returns:
```json
{
  "results": [
    {"title": "Getting Started", "summary": "Basic setup"},
    {"title": "Advanced Features", "summary": "Complex workflows"}
  ]
}
```

The foreach will generate:
- "Document: Getting Started - Basic setup"
- "Document: Advanced Features - Complex workflows"

## Error Handling

Use `error_keys` to detect API errors:

```python
api_tool = (DataMap('check_status')
    .webhook('GET', 'https://api.service.com/status')
    .error_keys(['error', 'message', 'errors'])  # Check for these keys
    .output(SwaigFunctionResult('Status: ${response.status}'))
)
```

If the response contains any of the error keys, the tool will fail gracefully.

## Helper Functions

For common patterns, use convenience functions:

### Simple API Tool

```python
from signalwire_agents.core.data_map import create_simple_api_tool

weather = create_simple_api_tool(
    name='get_weather',
    url='https://api.weather.com/v1/current?key=API_KEY&q=${location}',
    response_template='Weather: ${response.current.condition.text}, ${response.current.temp_f}°F',
    parameters={
        'location': {
            'type': 'string', 
            'description': 'City name', 
            'required': True
        }
    },
    headers={'X-API-Key': 'your-api-key'},
    error_keys=['error']
)
```

### Expression Tool

```python
from signalwire_agents.core.data_map import create_expression_tool

control = create_expression_tool(
    name='media_control',
    patterns={
        r'start|play|begin': SwaigFunctionResult().add_action('start', True),
        r'stop|end|pause': SwaigFunctionResult().add_action('stop', True),
        r'next|skip': SwaigFunctionResult().add_action('next', True)
    },
    parameters={
        'command': {'type': 'string', 'description': 'Control command'}
    }
)
```

## Real-World Examples

### Weather Service

```python
weather_tool = (DataMap('get_weather')
    .description('Get current weather conditions')
    .parameter('location', 'string', 'City and state/country', required=True)
    .parameter('units', 'string', 'Temperature units', enum=['fahrenheit', 'celsius'])
    .webhook('GET', 'https://api.openweathermap.org/data/2.5/weather?q=${location}&appid=${global_data.api_key}&units=${"imperial" if args.units == "fahrenheit" else "metric"}')
    .error_keys(['cod', 'message'])
    .output(SwaigFunctionResult('Weather in ${location}: ${response.weather[0].description}, ${response.main.temp}°${"F" if args.units == "fahrenheit" else "C"}. Feels like ${response.main.feels_like}°.'))
)
```

### Knowledge Search

```python
knowledge_tool = (DataMap('search_knowledge')
    .description('Search company knowledge base')
    .parameter('query', 'string', 'Search query', required=True)
    .parameter('category', 'string', 'Knowledge category', enum=['support', 'sales', 'technical'])
    .webhook('POST', 'https://api.company.com/knowledge/search',
             headers={'Authorization': 'Bearer ${global_data.knowledge_token}'})
    .body({
        'query': '${args.query}',
        'category': '${args.category}',
        'max_results': 3
    })
    .foreach('${response.articles}')
    .output(SwaigFunctionResult('Article: ${foreach.title}\n${foreach.summary}\nRelevance: ${foreach.score}'))
)
```

### Joke Service

```python
joke_tool = (DataMap('get_joke')
    .description('Get a random joke')
    .parameter('category', 'string', 'Joke category', 
               enum=['programming', 'dad', 'pun', 'random'])
    .webhook('GET', 'https://api.jokes.com/v1/joke?category=${args.category}&format=json')
    .output(SwaigFunctionResult('Here\'s a ${args.category} joke: ${response.setup} ... ${response.punchline}'))
)
```

### Multi-Step Fallback

```python
# Try multiple APIs with fallback
search_tool = (DataMap('web_search')
    .description('Search the web')
    .parameter('query', 'string', 'Search query', required=True)
    # Primary API
    .webhook('GET', 'https://api.primary.com/search?q=${args.query}&key=${global_data.primary_key}')
    # Fallback API
    .webhook('GET', 'https://api.fallback.com/search?query=${args.query}&token=${global_data.fallback_token}')
    .output(SwaigFunctionResult('Search results for "${args.query}": ${response.results[0].title} - ${response.results[0].snippet}'))
)
```

## Best Practices

### 1. Keep It Simple

DataMap is best for straightforward API integrations. For complex logic, use Skills or custom tools:

```python
# Good: Simple API call
.webhook('GET', 'https://api.service.com/data?id=${args.id}')

# Consider alternatives: Complex multi-step processing
# (Better handled by Skills or custom tools)
```

### 2. Use Global Data for Secrets

Store API keys and tokens in global data, not hardcoded:

```python
# Good
.webhook('GET', 'https://api.service.com/data?key=${global_data.api_key}')

# Bad
.webhook('GET', 'https://api.service.com/data?key=hardcoded-key')
```

### 3. Provide Clear Parameter Descriptions

```python
# Good
.parameter('location', 'string', 'City name or ZIP code (e.g., "New York" or "10001")', required=True)

# Bad  
.parameter('location', 'string', 'location', required=True)
```

### 4. Handle Errors Gracefully

```python
# Add error detection
.error_keys(['error', 'message', 'code'])

# Provide fallback webhooks
.webhook('GET', 'https://primary-api.com/data')
.webhook('GET', 'https://backup-api.com/data')  # Fallback
```

### 5. Use Enums for Limited Options

```python
.parameter('units', 'string', 'Temperature units', enum=['celsius', 'fahrenheit'])
.parameter('category', 'string', 'News category', enum=['business', 'tech', 'sports'])
```

## API Reference

### DataMap Class

#### Constructor

```python
DataMap(function_name: str)
```

#### Methods

| Method | Parameters | Description |
|--------|------------|-------------|
| `description(desc)` | `desc: str` | Set function description |
| `purpose(desc)` | `desc: str` | Alias for description |
| `parameter(name, type, desc, required, enum)` | `name: str, type: str, desc: str, required: bool, enum: List[str]` | Add parameter |
| `webhook(method, url, headers)` | `method: str, url: str, headers: Dict[str, str]` | Add API call |
| `body(data)` | `data: Dict[str, Any]` | Set request body |
| `expression(pattern, output)` | `pattern: str/Pattern, output: SwaigFunctionResult` | Add pattern match |
| `foreach(array_path)` | `array_path: str` | Process array response |
| `output(result)` | `result: SwaigFunctionResult` | Set final output |
| `error_keys(keys)` | `keys: List[str]` | Set error indicators |
| `to_swaig_function()` | - | Generate SWAIG function |

### Helper Functions

#### create_simple_api_tool

```python
create_simple_api_tool(
    name: str,
    url: str, 
    response_template: str,
    parameters: Optional[Dict[str, Dict]] = None,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    error_keys: Optional[List[str]] = None
) -> DataMap
```

#### create_expression_tool

```python
create_expression_tool(
    name: str,
    patterns: Dict[Union[str, Pattern], SwaigFunctionResult],
    parameters: Optional[Dict[str, Dict]] = None
) -> DataMap
```

## Integration with AgentBase

### Registration

```python
class MyAgent(AgentBase):
    def __init__(self):
        super().__init__(name="my-agent", route="/agent")
        
        # Create DataMap tool
        tool = DataMap('my_tool').description('My tool').output(SwaigFunctionResult('Result'))
        
        # Register with agent
        self.register_swaig_function(tool.to_swaig_function())
```

### Setting Global Data

```python
agent.set_global_data({
    'api_key': 'your-api-key',
    'user_id': 'current-user',
    'preferences': {'theme': 'dark'}
})
```

### Dynamic Configuration

```python
def configure_per_request(self, query_params, body_params, headers, agent):
    # Set API keys based on tenant
    tenant_id = query_params.get('tenant')
    api_key = get_api_key_for_tenant(tenant_id)
    
    agent.set_global_data({'api_key': api_key, 'tenant': tenant_id})
```

This comprehensive guide should help you understand and effectively use the DataMap system for creating REST API integrations in your SignalWire agents. 