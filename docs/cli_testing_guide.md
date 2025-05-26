# SWAIG CLI Testing Tool Guide

A comprehensive command-line tool for testing SignalWire AI Agents SWAIG functions locally with complete environment simulation and real API execution.

## Overview

The `swaig-test` CLI tool provides a complete testing environment for both webhook and DataMap SWAIG functions, automatically detecting function types and providing appropriate execution environments. It simulates the SignalWire platform locally while making real HTTP requests for DataMap functions.

## Key Features

- **Auto-Detection**: Automatically detects webhook vs DataMap functions - no manual flags needed
- **Real HTTP Execution**: DataMap functions make actual HTTP requests to real APIs
- **Complete DataMap Pipeline**: Full processing including expressions, webhooks, foreach, and output handling
- **Comprehensive Simulation**: Generate realistic post_data with all SignalWire metadata
- **Advanced Template Engine**: Supports all DataMap variable syntax (`${args.param}`, `${response.field}`, `${this.property}`)
- **Verbose Debugging**: Detailed execution tracing for both function types
- **Flexible Data Modes**: Choose between minimal, comprehensive, or custom post_data

## Installation

Install as part of the signalwire_agents package:

```bash
pip install -e .
swaig-test --help
```

## Quick Start

### List Available Functions

```bash
# Basic function listing
swaig-test examples/datasphere_serverless_env_demo.py --list-tools

# Detailed listing with function types
swaig-test examples/datasphere_serverless_env_demo.py --list-tools --verbose
```

**Example Output:**
```
Available SWAIG functions:
  search_knowledge - DataMap function (serverless)
  get_datetime - Get current date and time information
  calculate - Perform mathematical calculations and return the result
```

### Test Functions (Auto-Detection)

The tool automatically detects whether a function is a webhook or DataMap function:

```bash
# Test webhook function - auto-detected
swaig-test examples/datasphere_webhook_env_demo.py search_knowledge '{"query":"SignalWire"}'

# Test DataMap function - auto-detected  
swaig-test examples/datasphere_serverless_env_demo.py search_knowledge '{"query":"SignalWire"}'

# Test math skill function - auto-detected
swaig-test examples/datasphere_serverless_env_demo.py calculate '{"expression":"25 * 47"}'
```

## DataMap Function Execution

### Complete Processing Pipeline

DataMap functions follow the SignalWire server-side processing pipeline:

1. **Expression Processing**: Pattern matching against function arguments
2. **Webhook Execution**: Sequential HTTP requests until one succeeds  
3. **Foreach Processing**: Array iteration with template expansion
4. **Output Generation**: Final result formatting using templates
5. **Fallback Handling**: Error recovery with fallback outputs

### Real API Execution Example

```bash
# Test DataSphere serverless search with verbose output
swaig-test examples/datasphere_serverless_env_demo.py search_knowledge '{"query":"SignalWire"}' --verbose
```

**Example Execution Flow:**
```
=== DataMap Function Execution ===
Config: { ... complete datamap configuration ... }

--- Processing Webhooks ---
=== Webhook 1/1 ===
Making POST request to: https://tony.signalwire.com/api/datasphere/documents/search
Headers: {
  "Content-Type": "application/json",
  "Authorization": "Basic ODQ2NTlmMjE..."
}
Request data: {
  "document_id": "b888a1cc-1707-4902-9573-aa201a0c1086", 
  "query_string": "SignalWire",
  "distance": "4.0",
  "count": "1"
}
Response status: 200
Webhook 1 succeeded!

--- Processing Webhook Foreach ---
Found array data in response.chunks: 1 items
Processed 1 items
Foreach result (formatted_results): === RESULT ===
SignalWire's competitive advantage comes from...

--- Processing Webhook Output ---
Set response = I found results for "SignalWire":

=== RESULT ===
SignalWire's competitive advantage comes from...

RESULT:
Response: I found results for "SignalWire": ...
```

### Template Expansion Support

The tool supports all DataMap template syntax with both `${}` and `%{}` variations:

| Syntax | Description | Example |
|--------|-------------|---------|
| `${args.param}` / `%{args.param}` | Function arguments | `${args.query}`, `%{args.type}` |
| `${response.field}` / `%{response.field}` | API response object | `${response.temperature}` |
| `${array[0].field}` / `%{array[0].field}` | API response array | `${array[0].joke}`, `%{array[0].text}` |
| `${this.property}` / `%{this.property}` | Current foreach item | `${this.title}`, `%{this.content}` |
| `${global_data.key}` / `%{global_data.key}` | Agent global data | `${global_data.api_key}` |

**Array Response Handling**: When a webhook returns a nameless array (like `[{"joke": "..."}]`), it's automatically stored as the `array` key, making it accessible via `${array[0].property}` syntax.

**Template Expansion Examples:**
```json
{
  "url": "https://api.example.com/v1/%{args.type}",
  "output": {
    "response": "Here's a joke: ${array[0].joke}"
  }
}
```

### Foreach Processing

DataMap foreach loops concatenate strings from array elements:

```json
{
  "foreach": {
    "input_key": "chunks",
    "output_key": "formatted_results", 
    "max": 3,
    "append": "=== RESULT ===\n${this.text}\n====================\n\n"
  }
}
```

This processes each item in `response.chunks` and builds a single concatenated string in `formatted_results`.

## Webhook Function Testing

### Post Data Simulation Modes

#### 1. Default Mode (Minimal Data)
```bash
swaig-test my_agent.py my_function '{"param":"value"}'
```
**Includes**: `function`, `argument`, `call_id`, `meta_data`, `global_data`

#### 2. Comprehensive Mode (Full SignalWire Environment)
```bash
swaig-test my_agent.py my_function '{"param":"value"}' --fake-full-data
```

**Includes complete post_data with all SignalWire keys:**
- **Core identification**: `function`, `argument`, `call_id`, `call_session_id`, `node_id`
- **Metadata**: `meta_data_token`, `meta_data` (function-level shared data)
- **Global data**: `global_data` (agent configuration and state)
- **Conversation context**: `call_log`, `raw_call_log` (OpenAI conversation format)
- **SWML variables**: `prompt_vars` (includes SWML vars + global_data keys)
- **Permissions**: `swaig_allow_swml`, `swaig_post_conversation`, `swaig_post_swml_vars`
- **HTTP context**: `http_method`, `webhook_url`, `user_agent`, `request_headers`

#### 3. Custom Data Mode
```bash
swaig-test my_agent.py my_function '{"param":"value"}' --custom-data '{"call_id":"test-123","global_data":{"environment":"production"}}'
```

### Comprehensive Post Data Example

```json
{
  "function": "search_knowledge",
  "argument": {"query": "SignalWire"},
  "call_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "call_session_id": "session-uuid",
  "node_id": "test-node-001",
  "meta_data_token": "func_hash_token",
  "meta_data": {
    "test_mode": true,
    "function_name": "search_knowledge"
  },
  "global_data": {
    "app_name": "test_application",
    "environment": "test",
    "user_preferences": {"language": "en"}
  },
  "call_log": [
    {
      "role": "system",
      "content": "You are a helpful AI assistant..."
    },
    {
      "role": "user",
      "content": "Please call the search_knowledge function"
    },
    {
      "role": "assistant",
      "content": "I'll call the search_knowledge function for you.",
      "tool_calls": [
        {
          "id": "call_12345678",
          "type": "function",
          "function": {
            "name": "search_knowledge",
            "arguments": "{\"query\":\"SignalWire\"}"
          }
        }
      ]
    }
  ],
  "raw_call_log": "... complete conversation history ...",
  "prompt_vars": {
    "ai_instructions": "You are a helpful assistant",
    "temperature": 0.7,
    "app_name": "test_application",
    "current_timestamp": "2024-01-15T10:30:00Z"
  },
  "swaig_allow_swml": true,
  "swaig_post_conversation": true,
  "swaig_post_swml_vars": true
}
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--list-tools` | List all available SWAIG functions and their types |
| `--verbose`, `-v` | Enable detailed execution tracing and debugging |
| `--fake-full-data` | Generate comprehensive post_data with all SignalWire metadata |
| `--minimal` | Use minimal post_data (essential keys only) |
| `--custom-data` | JSON string with custom post_data overrides |

## Real-World Examples

### DataSphere Knowledge Search

```bash
# Test DataSphere serverless function
swaig-test examples/datasphere_serverless_env_demo.py search_knowledge '{"query":"AI agents"}' --verbose
```

**Expected Output:**
```
Executing DataMap function: search_knowledge
=== DataMap Function Execution ===

--- Processing Webhooks ---
Making POST request to: https://tony.signalwire.com/api/datasphere/documents/search
Response status: 200
Webhook 1 succeeded!

--- Processing Webhook Foreach ---
Found array data in response.chunks: 1 items
Processed 1 items

--- Processing Webhook Output ---
Set response = I found results for "AI agents":

=== RESULT ===
[Actual knowledge base content about AI agents...]

RESULT:
Response: I found results for "AI agents": ...
```

### Math Skill Function

```bash
# Test webhook-style math function
swaig-test examples/datasphere_serverless_env_demo.py calculate '{"expression":"25 * 47"}' --verbose
```

**Expected Output:**
```
Calling webhook function: calculate
Arguments: {"expression": "25 * 47"}
Function description: Perform mathematical calculations and return the result

RESULT:
SwaigFunctionResult: The result of 25 * 47 is 1175.
```

### DateTime Skill Function

```bash
# Test datetime function with comprehensive data
swaig-test examples/datasphere_serverless_env_demo.py get_datetime '{}' --fake-full-data
```

## Function Type Detection

The tool automatically detects function types:

- **DataMap Functions**: Stored as `dict` objects with `data_map` configuration
- **Webhook Functions**: Stored as `SWAIGFunction` objects with description and handler
- **Skill Functions**: Detected from loaded skills

**Detection Example:**
```bash
swaig-test my_agent.py --list-tools --verbose

Available SWAIG functions:
  search_knowledge - DataMap function (serverless)
    Config: {"webhooks": [...], "output": {...}}
  calculate - Perform mathematical calculations and return the result
    Function: <SWAIGFunction object>
```

## Advanced Usage

### Testing DataMap Error Handling

Test how DataMap functions handle API failures:

```bash
# Test with verbose output to see fallback processing
swaig-test my_agent.py my_datamap_func '{"input":"test"}' --verbose
```

If the primary webhook fails, you'll see:
```
Webhook 1 request failed: Connection timeout
--- Using DataMap Fallback Output ---
Fallback result = Sorry, the service is temporarily unavailable.
```

### Custom Environment Testing

Simulate different environments with custom data:

```bash
# Simulate production environment
swaig-test my_agent.py my_function '{"input":"test"}' --fake-full-data --custom-data '{
  "global_data": {
    "environment": "production", 
    "api_tier": "premium",
    "user_id": "prod-user-123"
  },
  "prompt_vars": {
    "ai_instructions": "You are a premium production assistant",
    "temperature": 0.3
  }
}'
```

### Testing Complex DataMap Configurations

For DataMap functions with multiple webhooks and complex foreach processing:

```bash
swaig-test my_agent.py complex_search '{"query":"test","filters":["type1","type2"]}' --verbose
```

This shows the complete processing pipeline:
- Template expansion in URLs and parameters
- Multiple webhook attempts with fallback
- Foreach processing of array responses
- Final output template expansion

## Troubleshooting

### Common Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **Agent Loading** | "No AgentBase instance found" | Ensure file has `agent` variable or AgentBase subclass |
| **Function Missing** | "Function 'X' not found" | Use `--list-tools` to verify function registration |
| **DataMap HTTP Error** | "Webhook request failed" | Check network connectivity and API credentials |
| **Template Expansion** | "MISSING:variable" in output | Verify template variable names match data structure |
| **JSON Parsing** | "Invalid JSON in args" | Check JSON syntax in function arguments |

### Debug Strategies

1. **Use `--verbose`**: Shows complete execution flow
2. **Check function list**: Use `--list-tools --verbose` to see configurations
3. **Test connectivity**: For DataMap functions, ensure API endpoints are reachable
4. **Validate JSON**: Use online JSON validators for complex arguments
5. **Check logs**: Agent initialization logs show skill loading status

### DataMap-Specific Debugging

For DataMap function issues:

```bash
# Enable verbose to see HTTP details
swaig-test my_agent.py my_datamap '{"input":"test"}' --verbose

# Check the complete configuration
swaig-test my_agent.py --list-tools --verbose | grep -A 20 my_datamap
```

Look for:
- Template expansion in request data
- HTTP response status and content
- Foreach processing details
- Output template expansion

## Integration with Development

### Pre-Deployment Testing

```bash
# Test all functions systematically
functions=$(swaig-test my_agent.py --list-tools | grep "  " | cut -d' ' -f3)
for func in $functions; do
    echo "Testing $func..."
    swaig-test my_agent.py $func '{"test":"data"}' --fake-full-data
done
```

### CI/CD Integration

The tool returns appropriate exit codes:
- `0`: Success
- `1`: Error (function failed, invalid arguments, network issues, etc.)

```yaml
# GitHub Actions example
- name: Test SWAIG Functions
  run: |
    swaig-test my_agent.py critical_function '{"input":"test"}' --fake-full-data
    if [ $? -ne 0 ]; then
      echo "Critical function test failed"
      exit 1
    fi
```

## Performance and Limitations

### Performance Considerations

- **DataMap HTTP Requests**: Real network latency applies
- **Large Responses**: Processing large API responses takes time
- **Verbose Output**: Can generate substantial debugging information
- **Memory Usage**: Comprehensive post_data mode uses more memory

### Current Limitations

1. **SignalWire Infrastructure**: Cannot perfectly replicate the serverless environment
2. **Network Dependencies**: DataMap testing requires internet connectivity
3. **Authentication**: Uses real API credentials (ensure proper security)
4. **State Isolation**: No persistence between separate test runs
5. **Concurrency**: Single-threaded execution only

### Best Practices

1. **Use minimal data mode** for basic function validation
2. **Enable verbose mode** when debugging issues
3. **Test DataMap functions** with real API credentials in secure environments
4. **Validate JSON arguments** before testing
5. **Check network connectivity** before testing DataMap functions

The `swaig-test` tool provides comprehensive local testing capabilities that closely mirror the SignalWire production environment, enabling confident development and debugging of both webhook and DataMap SWAIG functions.

### Webhook Failure Detection

DataMap webhooks are considered failed when any of these conditions occur:

1. **HTTP Status Codes**: Status outside 200-299 range
2. **Explicit Error Keys**: `parse_error` or `protocol_error` in response
3. **Custom Error Keys**: Any keys specified in webhook `error_keys` configuration
4. **Network Errors**: Connection timeouts, DNS failures, etc.

When a webhook fails, the tool:
- Tries the next webhook in sequence (if any)
- Uses fallback output if all webhooks fail
- Provides detailed error information in verbose mode

### Joke Agent Examples

#### Working Joke API (Success Case)

```bash
# Test with valid API key - shows successful DataMap processing
API_NINJAS_KEY=your_api_key swaig-test examples/joke_skill_demo.py get_joke '{"type": "jokes"}' --verbose
```

**Expected Output:**
```
=== DataMap Function Execution ===
--- Processing Webhooks ---
Making GET request to: https://api.api-ninjas.com/v1/jokes
Response status: 200
Webhook 1 succeeded!
Array response: 1 items

--- Processing Webhook Output ---
Set response = Here's a joke: What do you call a bear with no teeth? A gummy bear!

RESULT:
Response: Here's a joke: What do you call a bear with no teeth? A gummy bear!
```

#### Invalid API Key (Failure Case)

```bash
# Test with invalid API key - shows fallback output processing
swaig-test examples/joke_agent.py get_joke '{"type": "jokes"}' --verbose
```

**Expected Output (when API key is invalid):**
```
=== DataMap Function Execution ===
--- Processing Webhooks ---
Making GET request to: https://api.api-ninjas.com/v1/jokes
Response status: 400
Response data: {"error": "Invalid API Key."}
Webhook failed: HTTP status 400 outside 200-299 range
Webhook 1 failed, trying next webhook...

--- Using DataMap Fallback Output ---
Fallback result = Tell the user that the joke service is not working right now and just make up a joke on your own

RESULT:
Response: Tell the user that the joke service is not working right now and just make up a joke on your own
```

This demonstrates both:
- **Successful webhook processing** with array response handling
- **Failure detection and fallback** when APIs return errors 