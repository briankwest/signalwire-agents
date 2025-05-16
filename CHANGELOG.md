# Changelog

## [Unreleased]

### Added

- **SIP Routing:** Added support for routing SIP requests based on username
  - `SWMLService.extract_sip_username()` method for extracting SIP usernames from request bodies
  - `register_routing_callback()` method for SWMLService to handle custom routing
  - `enable_sip_routing()` method for AgentBase to automatically handle SIP requests
  - `register_sip_username()` method for AgentBase to register custom SIP usernames
  - `setup_sip_routing()` method for AgentServer to enable centralized SIP routing
  - Added global `/sip` endpoint for both SWMLService and AgentBase when SIP routing is enabled
  - Example: Added SIP routing to simple_agent.py
  - Documentation: Added docs/sip_routing.md with full documentation

### Fixed

- Fixed the `sleep` verb auto-vivification to properly handle direct integer values

### Changed

- **Dynamic Method Generation:** Implemented auto-vivification in SWMLService class for more intuitive verb usage
  - Now you can use `service.play(url="say:Hello")` instead of `service.add_verb("play", {"url": "say:Hello"})`
  - All verbs from the schema are automatically available as methods
  - Special handling for the `sleep` verb which takes a direct integer value

## [0.1.2] - 2023-04-15

### Added

- Initial release of the SignalWire AI Agent SDK
- Base classes for building and serving AI Agents
- SWML document creation and manipulation
- Web server for handling agent requests
- Documentation and examples 