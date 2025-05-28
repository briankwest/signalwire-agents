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
- `--chunk-size SIZE` - Chunk size in characters (default: 500)
- `--chunk-overlap SIZE` - Overlap between chunks (default: 50)
- `--file-types TYPES` - Comma-separated file extensions (default: md,txt)
- `--exclude PATTERNS` - Comma-separated glob patterns to exclude
- `--model MODEL` - Embedding model name (default: sentence-transformers/all-mpnet-base-v2)
- `--tags TAGS` - Comma-separated tags to add to all chunks
- `--verbose` - Show detailed progress information
- `--validate` - Validate the created index after building

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
- Simulate serverless environments
- Auto-discover agents and functions

**Examples:**

```bash
# List available agents
swaig-test examples/my_agent.py --list-agents

# List available functions
swaig-test examples/my_agent.py --list-tools

# Test SWML generation
swaig-test examples/my_agent.py --dump-swml

# Test a specific function
swaig-test examples/my_agent.py --exec my_function --param value

# Simulate serverless environment
swaig-test examples/my_agent.py --simulate-serverless lambda --dump-swml
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