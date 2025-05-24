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
        
        # Create a weather API tool - output goes inside webhook
        weather_tool = (DataMap('get_weather')
            .description('Get current weather information')
            .parameter('location', 'string', 'City name', required=True)
            .webhook('GET', 'https://api.weather.com/v1/current?key=YOUR_API_KEY&q=${location}')
            .output(SwaigFunctionResult('Weather in ${location}: ${response.current.condition.text}, ${response.current.temp_f}°F'))
            .error_keys(['error'])
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

### Webhook Output Structure

**Important**: Outputs are attached to individual webhooks, not at the top level. This allows for:

- **Per-webhook responses**: Each API can have its own output template
- **Sequential fallback**: Try multiple APIs until one succeeds
- **Error handling**: Per-webhook error detection

```python
# Correct: Output inside webhook
tool = (DataMap('get_data')
    .webhook('GET', 'https://api.primary.com/data')
    .output(SwaigFunctionResult('Primary: ${response.value}'))
    .error_keys(['error'])
)

# Multiple webhooks with fallback
tool = (DataMap('search_with_fallback')
    .webhook('GET', 'https://api.fast.com/search?q=${args.query}')
    .output(SwaigFunctionResult('Fast result: ${response.title}'))
    .webhook('GET', 'https://api.comprehensive.com/search?q=${args.query}')
    .output(SwaigFunctionResult('Comprehensive result: ${response.title}'))
    .fallback_output(SwaigFunctionResult('Sorry, all search services are unavailable'))
)
```

### Execution Flow

1. **Try first webhook**: If successful, use its output
2. **Try subsequent webhooks**: If first fails, try next webhook
3. **Fallback output**: If all webhooks fail, use top-level fallback (if defined)
4. **Generic error**: If no fallback defined, return generic error message

## Variable Expansion

DataMap supports powerful variable substitution using `${variable}` syntax:

### Available Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `${args.param_name}` | Function arguments | `${args.location}` |
| `${array[0].field}` | API response data (array) | `${array[0].joke}` |
| `${response.field}` | API response data (object) | `${response.status}` |
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

### Variable Scoping Rules

Understanding when to use different variable types:

| Context | Variable Type | Example | When to Use |
|---------|---------------|---------|-------------|
| **Array APIs** | `${array[0].field}` | `${array[0].joke}` | API returns JSON array `[{...}]` |
| **Object APIs** | `${response.field}` | `${response.temperature}` | API returns JSON object `{...}` |
| **Foreach loops** | `${foreach.field}` | `${foreach.title}` | Inside array processing |
| **Function args** | `${args.field}` | `${args.location}` | User-provided parameters |
| **Agent data** | `${global_data.field}` | `${global_data.api_key}` | Agent configuration |

```python
# Example: Weather API returns object
{
  "current": {"temp_f": 72, "condition": {"text": "Sunny"}},
  "location": {"name": "New York"}
}
# Use: ${response.current.temp_f}

# Example: Jokes API returns array  
[
  {"joke": "Why did the chicken cross the road?", "category": "classic"}
]
# Use: ${array[0].joke}

# Example: Search API with foreach
{
  "results": [
    {"title": "Result 1", "snippet": "..."},
    {"title": "Result 2", "snippet": "..."}
  ]
}
# Use: .foreach('${response.results}') then ${foreach.title}
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
    .error_keys(['error'])
    .fallback_output(SwaigFunctionResult('Sorry, the joke service is currently unavailable. Please try again later.'))
)
```

### API with Array Response

```python
# For APIs that return arrays, use ${array[0].field} syntax
joke_ninja_tool = (DataMap('get_joke')
    .description('Get a random joke from API Ninjas')
    .parameter('type', 'string', 'Type of joke', enum=['jokes', 'dadjokes'])
    .webhook('GET', 'https://api.api-ninjas.com/v1/${args.type}',
             headers={'X-Api-Key': '${global_data.api_key}'})
    .output(SwaigFunctionResult('Here\'s a joke: ${array[0].joke}'))
    .error_keys(['error'])
    .fallback_output(SwaigFunctionResult('Sorry, there is a problem with the joke service right now. Please try again later.'))
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

## Troubleshooting

### Common Issues and Solutions

#### 1. "Output is undefined" or Empty Responses

**Problem**: Your DataMap tool returns empty or undefined results.

**Common Causes**:
- Wrong variable syntax (`${response.field}` vs `${array[0].field}`)
- Incorrect JSON path
- API returns different structure than expected

**Solutions**:
```python
# Test your API response structure first
# If API returns: {"data": [{"joke": "text"}]}
.output(SwaigFunctionResult('${response.data[0].joke}'))  # Correct

# If API returns: [{"joke": "text"}]  
.output(SwaigFunctionResult('${array[0].joke}'))  # Correct

# Debug by returning the raw response
.output(SwaigFunctionResult('Raw response: ${response}'))
```

#### 2. Authentication Failures

**Problem**: API returns 401/403 errors.

**Solutions**:
```python
# Ensure API key is in global_data
agent.set_global_data({'api_key': 'your-actual-key'})

# Check header format
.webhook('GET', 'https://api.service.com/data',
         headers={'X-API-Key': '${global_data.api_key}'})  # Correct
         
# Not in the URL if it should be in headers
.webhook('GET', 'https://api.service.com/data?key=${global_data.api_key}')  # Check API docs
```

#### 3. Parameter Validation Errors

**Problem**: "Missing required parameter" or validation failures.

**Solutions**:
```python
# Ensure required parameters are marked correctly
.parameter('location', 'string', 'City name', required=True)

# Use enums for limited options
.parameter('units', 'string', 'Temperature units', 
           required=True, enum=['celsius', 'fahrenheit'])
```

#### 4. Webhook Never Executes

**Problem**: Tool doesn't seem to call the API.

**Common Causes**:
- Expressions match first (expressions run before webhooks)
- Wrong parameter names in URL template

**Solutions**:
```python
# Check if expressions are matching unexpectedly
# Remove or modify expressions if they're catching all inputs

# Verify parameter names match
.parameter('query', 'string', 'Search query')  # Parameter name
.webhook('GET', 'https://api.search.com?q=${args.query}')  # Same name
```

#### 5. Error Keys Not Working

**Problem**: API errors aren't being caught.

**Solutions**:
```python
# Check actual error response structure
# If API returns: {"error": {"message": "Not found"}}
.error_keys(['error'])  # Correct

# If API returns: {"status": "error", "msg": "Not found"}  
.error_keys(['status', 'msg'])  # Check top-level keys
```

#### 6. Foreach Not Processing Arrays

**Problem**: Array items aren't being processed individually.

**Solutions**:
```python
# Ensure you're pointing to the actual array
# If response is: {"results": [{"title": "..."}, {"title": "..."}]}
.foreach('${response.results}')  # Correct

# Then use foreach variables
.output(SwaigFunctionResult('Title: ${foreach.title}'))
```

### Debugging Tips

1. **Start Simple**: Begin with a basic webhook that just returns `${response}` to see the raw API response

2. **Test API Directly**: Use curl or Postman to verify the API works and see the response structure

3. **Use Fallback Output**: Add fallback messages to catch when webhooks fail:
   ```python
   .fallback_output(SwaigFunctionResult('All webhooks failed - check API'))
   ```

4. **Check Agent Logs**: Look for error messages in the agent console output

5. **Validate JSON Paths**: Use online JSON path testers to verify your variable paths

### Testing Strategies

```python
# Create a test tool that echoes inputs
debug_tool = (DataMap('debug_echo')
    .description('Debug tool to test parameters')
    .parameter('test_param', 'string', 'Test parameter')
    .webhook('GET', 'https://httpbin.org/get?test=${args.test_param}')
    .output(SwaigFunctionResult('Sent: ${args.test_param}, Got: ${response.args.test}'))
)

# Test variable scoping with a mock API
test_variables = (DataMap('test_vars')
    .description('Test variable access')
    .parameter('user_input', 'string', 'User input to echo')
    .webhook('GET', 'https://httpbin.org/json')
    .output(SwaigFunctionResult('''
        Input: ${args.user_input}
        API Response: ${response.slideshow.title}
        Global Data: ${global_data.api_key}
    '''))
)
```

This comprehensive guide should help you understand and effectively use the DataMap system for creating REST API integrations in your SignalWire agents. 