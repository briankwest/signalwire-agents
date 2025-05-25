# SWAIG Function CLI Testing Tool

This CLI tool allows you to test SWAIG functions from agent applications without starting the full server. It's particularly useful for debugging webhook-style tools.

## Installation

### Option 1: Via pip install (Recommended)

When you install the SignalWire Agents SDK, the CLI tool is automatically available:

```bash
pip install signalwire_agents
```

After installation, the `swaig-test` command is available globally:

```bash
swaig-test --help
```

### Option 2: Development Installation

If you're working with the source code:

```bash
# Install in development mode
pip install -e .

# Or run directly from source
python signalwire_agents/cli/test_swaig.py --help
```

## Usage

### Method 1: Using the pip-installed command (Recommended)
```bash
swaig-test <agent_path> <tool_name> <args_json>
```

### Method 2: Using the Python module
```bash
python -m signalwire_agents.cli.test_swaig <agent_path> <tool_name> <args_json>
```

### Method 3: Direct Python execution (development)
```bash
python signalwire_agents/cli/test_swaig.py <agent_path> <tool_name> <args_json>
```

## Options

- `--list-tools` - List all available SWAIG functions in the agent and exit
- `--verbose, -v` - Enable verbose output showing function details
- `--raw-data JSON` - Optional JSON string containing raw data (e.g., call_id, etc.)

## Examples

### List available tools in an agent
```bash
swaig-test examples/datasphere_webhook_env_demo.py --list-tools
```

### Test DataSphere search function
```bash
swaig-test examples/datasphere_webhook_env_demo.py search_knowledge '{"query":"test search"}'
```

### Test math skill with verbose output
```bash
swaig-test examples/simple_agent.py calculate '{"expression":"2+2"}' --verbose
```

### Test with raw data (simulating call context)
```bash
swaig-test examples/my_agent.py my_tool '{"param":"value"}' --raw-data '{"call_id":"test-123"}'
```

### Test datetime skill
```bash
swaig-test examples/datasphere_webhook_env_demo.py get_current_time '{}'
```

## How It Works

1. **Agent Loading**: The tool loads your agent application without starting the web server
2. **Server Prevention**: It intercepts `agent.serve()` calls to prevent blocking
3. **Function Discovery**: It finds all registered SWAIG functions in the loaded agent
4. **Direct Calling**: It calls the function handler directly, bypassing HTTP webhooks
5. **Result Display**: It formats and displays the function result

## Supported Function Types

- ✅ **Webhook SWAIG Functions**: Traditional functions with Python handlers
- ✅ **Skill-based Functions**: Functions registered through the skills system
- ❌ **DataMap Functions**: Serverless functions (execute on SignalWire servers only)

## Agent Loading Strategies

The tool uses multiple strategies to find your agent:

1. **Agent Variable**: Looks for `agent` variable in the module
2. **Instance Discovery**: Scans for any AgentBase instances in module globals
3. **Class Instantiation**: Finds AgentBase subclasses and instantiates them
4. **Main Function**: As a last resort, calls `main()` with server interception

## Installation Details

When you run `pip install signalwire_agents`, the package automatically creates a console script called `swaig-test` that you can use from anywhere in your terminal. This is defined in the package's `pyproject.toml`:

```toml
[project.scripts]
swaig-test = "signalwire_agents.cli.test_swaig:console_entry_point"
```

## Troubleshooting

### "No AgentBase instance found"
- Make sure your agent file contains an `agent` variable or AgentBase subclass
- Check that all required environment variables are set
- Try using `--verbose` to see loading details

### "Function not found"
- Use `--list-tools` to see available functions
- Check that skills are properly loaded
- Verify function names match exactly

### DataMap functions not supported
- DataMap functions execute on SignalWire servers and can't be tested locally
- Use the regular agent server for testing DataMap functions

### Command not found after pip install
- Make sure the package was installed correctly: `pip show signalwire_agents`
- Check that your Python environment's scripts directory is in your PATH
- Try using the Python module version: `python -m signalwire_agents.cli.test_swaig`

## Development Benefits

- **Fast Iteration**: Test functions without starting/stopping servers
- **Debugging**: Get immediate feedback and error messages
- **CI/CD Integration**: Use in automated tests and build pipelines
- **Skill Development**: Test individual skills in isolation
- **API Testing**: Verify function logic without HTTP overhead
- **Global Availability**: Available as `swaig-test` command after pip install

## Environment Requirements

All environment variables required by your agent must be set before running the tool. The tool will show clear error messages if required variables are missing.

## Quick Start Examples

After installing with `pip install signalwire_agents`:

```bash
# Quick function test
swaig-test my_agent.py my_function '{"param": "value"}'

# Explore available functions
swaig-test my_agent.py --list-tools

# Debug with verbose output
swaig-test my_agent.py my_function '{"param": "value"}' --verbose

# Test with call context
swaig-test my_agent.py my_function '{"param": "value"}' --raw-data '{"call_id": "test-123"}'
``` 