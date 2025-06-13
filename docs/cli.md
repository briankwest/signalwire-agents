# Command Line Interface (CLI) Tools

The SignalWire Agents SDK provides several command-line tools to help with development, testing, and deployment.

## Available Commands

### sw-search - Build Search Indexes

Build local search indexes from document collections for use with the native vector search skill.

```bash
sw-search <source_dir> [options]
```

**Arguments:**
- `source_dir` - Directory containing documents to index

**Options:**
- `--output FILE` - Output .swsearch file (default: `<source_dir>.swsearch`)
- `--chunk-size SIZE` - Chunk size in words (default: 50)
- `--chunk-overlap SIZE` - Overlap between chunks in words (default: 10)
- `--file-types TYPES` - Comma-separated file extensions (default: md,txt,rst)
- `--exclude PATTERNS` - Comma-separated glob patterns to exclude
- `--model MODEL` - Embedding model name (default: sentence-transformers/all-mpnet-base-v2)
- `--tags TAGS` - Comma-separated tags to add to all chunks
- `--verbose` - Show detailed progress information
- `--validate` - Validate the created index after building
- `--chunking-strategy STRATEGY` - Chunking strategy: sentence, sliding, paragraph, page, semantic, topic, qa (default: sentence)
- `--max-sentences-per-chunk NUM` - Maximum sentences per chunk (default: 3)
- `--semantic-threshold FLOAT` - Threshold for semantic chunking (default: 0.5)
- `--topic-threshold FLOAT` - Threshold for topic-based chunking (default: 0.3)
- `--index-nlp-backend BACKEND` - NLP backend for processing (default: basic)
- `--split-newlines` - Split on newlines in addition to sentence boundaries
- `--languages LANGS` - Comma-separated language codes (default: en)

**Subcommands:**

#### validate - Validate Search Index

```bash
sw-search validate <index_file> [options]
```

**Arguments:**
- `index_file` - Path to .swsearch file to validate

**Options:**
- `--verbose` - Show detailed information about the index

#### search - Search Within Index

```bash
sw-search search <index_file> <query> [options]
```

**Arguments:**
- `index_file` - Path to .swsearch file to search
- `query` - Search query text

**Options:**
- `--count COUNT` - Number of results to return (default: 5)
- `--distance-threshold FLOAT` - Minimum similarity score (default: 0.0)
- `--tags TAGS` - Comma-separated tags to filter by
- `--verbose` - Show detailed information
- `--json` - Output results as JSON
- `--no-content` - Hide content in results (show only metadata)
- `--query-nlp-backend BACKEND` - NLP backend for query processing

#### remote - Search Remote Index via API

```bash
sw-search remote <endpoint> <query> [options]
```

**Arguments:**
- `endpoint` - URL of the search API endpoint
- `query` - Search query text

**Options:**
- `--index-name NAME` - Name of the index to search (required)
- `--count COUNT` - Number of results to return (default: 5)
- `--distance-threshold FLOAT` - Minimum similarity score (default: 0.0)
- `--tags TAGS` - Comma-separated tags to filter by
- `--verbose` - Show detailed information
- `--json` - Output results as JSON
- `--no-content` - Hide content in results (show only metadata)
- `--timeout SECONDS` - Request timeout in seconds (default: 30)

**Examples:**

```bash
# Build from the comprehensive concepts guide
sw-search docs/signalwire_agents_concepts_guide.md --output concepts.swsearch

# Build from multiple sources
sw-search docs/signalwire_agents_concepts_guide.md examples README.md --output comprehensive.swsearch

# Validate an index
sw-search validate concepts.swsearch

# Search within an index  
sw-search search concepts.swsearch "how to create an agent"
sw-search search concepts.swsearch "API reference" --count 3 --verbose
sw-search search concepts.swsearch "configuration" --tags documentation --json

# Search remote index via API
sw-search remote http://localhost:8001/search "how to create an agent" --index-name docs
sw-search remote https://api.example.com/search "configuration" --index-name docs --count 3 --json

# Traditional directory approach
sw-search docs --output docs.swsearch
```

For complete documentation on the search system, see [Local Search System](search-system.md).

### swaig-test - Test SWAIG Functions

Test SignalWire AI Agent SWAIG functions and SWML generation locally.

```bash
swaig-test <agent_file> [function_name] [options]
```

**Key Features:**
- Test SWAIG functions with mock data
- Generate and validate SWML documents
- Simulate serverless environments (Lambda, CGI, Cloud Functions, Azure Functions)
- Auto-discover agents and functions
- Environment variable management
- HTTP request simulation
- Call configuration options

**Basic Usage:**

```bash
# List available agents
swaig-test examples/my_agent.py --list-agents

# List available functions
swaig-test examples/my_agent.py --list-tools

# Test SWML generation
swaig-test examples/my_agent.py --dump-swml

# Test a specific function
swaig-test examples/my_agent.py --exec my_function --param value
```

**Serverless Environment Simulation:**

```bash
# AWS Lambda simulation
swaig-test examples/my_agent.py --simulate-serverless lambda --dump-swml
swaig-test examples/my_agent.py --simulate-serverless lambda \
  --aws-function-name my-function --aws-region us-west-2 \
  --exec my_function --param value

# CGI simulation
swaig-test examples/my_agent.py --simulate-serverless cgi \
  --cgi-host my-server.com --cgi-https --dump-swml

# Google Cloud Functions
swaig-test examples/my_agent.py --simulate-serverless cloud_function \
  --gcp-function-url https://my-function.cloudfunctions.net \
  --exec my_function

# Azure Functions
swaig-test examples/my_agent.py --simulate-serverless azure_function \
  --azure-function-url https://my-function.azurewebsites.net \
  --exec my_function
```

**Environment Management:**

```bash
# Use environment file
swaig-test examples/my_agent.py --env-file production.env --exec my_function

# Override specific variables
swaig-test examples/my_agent.py --env DEBUG=true --env API_KEY=test_key \
  --exec my_function

# Set call configuration
swaig-test examples/my_agent.py --call-type webrtc --call-direction inbound \
  --exec my_function
```

For complete documentation, see [CLI Testing Guide](cli_testing_guide.md).

## Installation

All CLI tools are included when you install the SignalWire Agents SDK:

```bash
pip install signalwire-agents

# For search functionality
pip install signalwire-agents[search]

# For full functionality
pip install signalwire-agents[search-all]
```

## Getting Help

Each command provides help information:

```bash
# General help
sw-search --help

# SWAIG testing help
swaig-test --help
``` 