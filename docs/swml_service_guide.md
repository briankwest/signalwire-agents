# SignalWire SWML Service Guide

## Table of Contents
- [Introduction](#introduction)
- [Installation](#installation)
- [Basic Usage](#basic-usage)
- [Centralized Logging System](#centralized-logging-system)
- [SWML Document Creation](#swml-document-creation)
- [Verb Handling](#verb-handling)
- [Web Service Features](#web-service-features)
- [Advanced Usage](#advanced-usage)
- [API Reference](#api-reference)
- [Examples](#examples)

## Introduction

The `SWMLService` class provides a foundation for creating and serving SignalWire Markup Language (SWML) documents. It serves as the base class for all SignalWire services, including AI Agents, and handles common tasks such as:

- SWML document creation and manipulation
- Schema validation
- Web service functionality
- Authentication
- Centralized logging

The class is designed to be extended for specific use cases, while providing powerful capabilities out of the box.

## Installation

The `SWMLService` class is part of the SignalWire AI Agent SDK. Install it using pip:

```bash
pip install signalwire-agents
```

## Basic Usage

Here's a simple example of creating an SWML service:

```python
from signalwire_agents.core.swml_service import SWMLService

class SimpleVoiceService(SWMLService):
    def __init__(self, host="0.0.0.0", port=3000):
        super().__init__(
            name="voice-service",
            route="/voice",
            host=host,
            port=port
        )
        
        # Build the SWML document
        self.build_document()
    
    def build_document(self):
        # Reset the document to start fresh
        self.reset_document()
        
        # Add answer verb
        self.add_answer_verb()
        
        # Add play verb for greeting
        self.add_verb("play", {
            "url": "say:Hello, thank you for calling our service."
        })
        
        # Add hangup verb
        self.add_hangup_verb()

# Create and start the service
service = SimpleVoiceService()
service.serve()
```

## Centralized Logging System

The `SWMLService` class includes a centralized logging system based on `structlog` that provides structured, JSON-formatted logs. This logging system is automatically set up when you import the module, so you don't need to configure it in each service or example.

### How It Works

1. When `swml_service.py` is imported, it configures `structlog` (if not already configured)
2. Each `SWMLService` instance gets a logger bound to its service name
3. All logs include contextual information like service name, timestamp, and log level
4. Logs are formatted as JSON for easy parsing and analysis

### Using the Logger

Every `SWMLService` instance has a `log` attribute that can be used for logging:

```python
# Basic logging
self.log.info("service_started")

# Logging with context
self.log.debug("document_created", size=len(document))

# Error logging
try:
    # Some operation
    pass
except Exception as e:
    self.log.error("operation_failed", error=str(e))
```

### Log Levels

The following log levels are available (in increasing order of severity):
- `debug`: Detailed information for debugging
- `info`: General information about operation
- `warning`: Warning about potential issues
- `error`: Error information when operations fail
- `critical`: Critical error that might cause the application to terminate

### Suppressing Logs

To suppress logs when running a service, you can set the log level:

```python
import logging
logging.getLogger().setLevel(logging.WARNING)  # Only show warnings and above
```

## SWML Document Creation

The `SWMLService` class provides methods for creating and manipulating SWML documents.

### Document Structure

SWML documents have the following basic structure:

```json
{
  "version": "1.0.0",
  "sections": {
    "main": [
      { "verb1": { /* configuration */ } },
      { "verb2": { /* configuration */ } }
    ],
    "section1": [
      { "verb3": { /* configuration */ } }
    ]
  }
}
```

### Document Methods

- `reset_document()`: Reset the document to an empty state
- `add_verb(verb_name, config)`: Add a verb to the main section
- `add_section(section_name)`: Add a new section
- `add_verb_to_section(section_name, verb_name, config)`: Add a verb to a specific section
- `get_document()`: Get the current document as a dictionary
- `render_document()`: Get the current document as a JSON string

### Common Verb Shortcuts

- `add_answer_verb(max_duration=None, codecs=None)`: Add an answer verb
- `add_hangup_verb(reason=None)`: Add a hangup verb
- `add_ai_verb(prompt_text=None, prompt_pom=None, ...)`: Add an AI verb

## Verb Handling

The `SWMLService` class provides validation for SWML verbs using the SignalWire schema.

### Verb Validation

When adding a verb, the service validates it against the schema to ensure it has the correct structure and parameters.

```python
# This will validate the configuration against the schema
self.add_verb("play", {
    "url": "say:Hello, world!",
    "volume": 5
})

# This would fail validation (invalid parameter)
self.add_verb("play", {
    "invalid_param": "value"
})
```

### Custom Verb Handlers

You can register custom verb handlers for specialized verb processing:

```python
from signalwire_agents.core.swml_handler import SWMLVerbHandler

class CustomPlayHandler(SWMLVerbHandler):
    def __init__(self):
        super().__init__("play")
    
    def validate_config(self, config):
        # Custom validation logic
        return True, []
    
    def build_config(self, **kwargs):
        # Custom configuration building
        return kwargs

service.register_verb_handler(CustomPlayHandler())
```

## Web Service Features

The `SWMLService` class includes built-in web service capabilities for serving SWML documents.

### Endpoints

By default, a service provides the following endpoints:

- `GET /route`: Return the SWML document
- `POST /route`: Process request data and return the SWML document
- `GET /route/`: Same as above but with trailing slash
- `POST /route/`: Same as above but with trailing slash

Where `route` is the route path specified when creating the service.

### Authentication

Basic authentication is automatically set up for all endpoints. Credentials are generated if not provided, or can be specified:

```python
service = SWMLService(
    name="my-service",
    basic_auth=("username", "password")
)
```

You can also set credentials using environment variables:
- `SWML_BASIC_AUTH_USER`
- `SWML_BASIC_AUTH_PASSWORD`

### Dynamic SWML Generation

You can override the `on_request` method to customize SWML documents based on request data:

```python
def on_request(self, request_data=None):
    if not request_data:
        return None
        
    # Customize document based on request_data
    self.reset_document()
    self.add_answer_verb()
    
    # Add custom verbs based on request_data
    if request_data.get("caller_type") == "vip":
        self.add_verb("play", {
            "url": "say:Welcome VIP caller!"
        })
    else:
        self.add_verb("play", {
            "url": "say:Welcome caller!"
        })
    
    # Return None to use the document we've built
    return None
```

## Advanced Usage

### Creating a FastAPI Router

You can get a FastAPI router for the service to include in a larger application:

```python
from fastapi import FastAPI

app = FastAPI()
service = SWMLService(name="my-service")
router = service.as_router()
app.include_router(router, prefix="/voice")
```

### Schema Path Customization

You can specify a custom path to the schema file:

```python
service = SWMLService(
    name="my-service",
    schema_path="/path/to/schema.json"
)
```

## API Reference

### Constructor Parameters

- `name`: Service name/identifier (required)
- `route`: HTTP route path (default: "/")
- `host`: Host to bind to (default: "0.0.0.0")
- `port`: Port to bind to (default: 3000)
- `basic_auth`: Optional tuple of (username, password)
- `schema_path`: Optional path to schema.json

### Document Methods

- `reset_document()`
- `add_verb(verb_name, config)`
- `add_section(section_name)`
- `add_verb_to_section(section_name, verb_name, config)`
- `get_document()`
- `render_document()`

### Service Methods

- `as_router()`
- `serve(host=None, port=None)`
- `stop()`
- `get_basic_auth_credentials()`
- `on_request(request_data=None)`

### Verb Helper Methods

- `add_answer_verb(max_duration=None, codecs=None)`
- `add_hangup_verb(reason=None)`
- `add_ai_verb(prompt_text=None, prompt_pom=None, ...)`

## Examples

### Basic Voicemail Service

```python
from signalwire_agents.core.swml_service import SWMLService

class VoicemailService(SWMLService):
    def __init__(self, host="0.0.0.0", port=3000):
        super().__init__(
            name="voicemail",
            route="/voicemail",
            host=host,
            port=port
        )
        
        # Build the SWML document
        self.build_voicemail_document()
    
    def build_voicemail_document(self):
        """Build the voicemail SWML document"""
        # Reset the document
        self.reset_document()
        
        # Add answer verb
        self.add_answer_verb()
        
        # Add play verb for greeting
        self.add_verb("play", {
            "url": "say:Hello, you've reached the voicemail service. Please leave a message after the beep."
        })
        
        # Play a beep
        self.add_verb("play", {
            "url": "https://example.com/beep.wav"
        })
        
        # Record the message
        self.add_verb("record", {
            "format": "mp3",
            "stereo": False,
            "max_length": 120,  # 2 minutes max
            "terminators": "#"
        })
        
        # Thank the caller
        self.add_verb("play", {
            "url": "say:Thank you for your message. Goodbye!"
        })
        
        # Hang up
        self.add_hangup_verb()
        
        self.log.debug("voicemail_document_built")
```

### Dynamic Call Routing Service

```python
class CallRouterService(SWMLService):
    def on_request(self, request_data=None):
        # If there's no request data, use default routing
        if not request_data:
            self.log.debug("no_request_data_using_default")
            return None
        
        # Create a new document
        self.reset_document()
        self.add_answer_verb()
        
        # Get routing parameters
        department = request_data.get("department", "").lower()
        
        # Add play verb for greeting
        self.add_verb("play", {
            "url": f"say:Thank you for calling our {department} department. Please hold."
        })
        
        # Route based on department
        phone_numbers = {
            "sales": "+15551112222",
            "support": "+15553334444",
            "billing": "+15555556666"
        }
        
        # Get the appropriate number or use default
        to_number = phone_numbers.get(department, "+15559990000")
        
        # Connect to the department
        self.add_verb("connect", {
            "to": to_number,
            "timeout": 30,
            "answer_on_bridge": True
        })
        
        # Add fallback message and hangup
        self.add_verb("play", {
            "url": "say:We're sorry, but all of our agents are currently busy. Please try again later."
        })
        self.add_hangup_verb()
        
        return None  # Use the document we've built
```

For more examples, see the `examples` directory in the SignalWire AI Agent SDK repository. 