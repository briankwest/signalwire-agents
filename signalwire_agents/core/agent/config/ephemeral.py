"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

"""Ephemeral agent configuration for dynamic per-request settings."""

from typing import Dict, Any, Optional, List


class EphemeralAgentConfig:
    """
    An ephemeral configurator object that mimics AgentBase's configuration interface.
    
    This allows dynamic configuration callbacks to use the same familiar methods
    they would use during agent initialization, but for per-request configuration.
    """
    
    def __init__(self):
        # Initialize all configuration containers
        self._hints = []
        self._languages = []
        self._pronounce = []
        self._params = {}
        self._global_data = {}
        self._prompt_sections = []
        self._raw_prompt = None
        self._post_prompt = None
        self._function_includes = []
        self._native_functions = []
    
    # Mirror all the AgentBase configuration methods
    
    def add_hint(self, hint: str) -> 'EphemeralAgentConfig':
        """Add a simple string hint"""
        if isinstance(hint, str) and hint:
            self._hints.append(hint)
        return self
    
    def add_hints(self, hints: List[str]) -> 'EphemeralAgentConfig':
        """Add multiple string hints"""
        if hints and isinstance(hints, list):
            for hint in hints:
                if isinstance(hint, str) and hint:
                    self._hints.append(hint)
        return self
    
    def add_language(self, name: str, code: str, voice: str, **kwargs) -> 'EphemeralAgentConfig':
        """Add a language configuration"""
        language = {
            "name": name,
            "code": code,
            "voice": voice
        }
        
        # Handle additional parameters
        for key, value in kwargs.items():
            if key in ["engine", "model", "speech_fillers", "function_fillers", "fillers"]:
                language[key] = value
        
        self._languages.append(language)
        return self
    
    def add_pronunciation(self, replace: str, with_text: str, ignore_case: bool = False) -> 'EphemeralAgentConfig':
        """Add a pronunciation rule"""
        if replace and with_text:
            rule = {"replace": replace, "with": with_text}
            if ignore_case:
                rule["ignore_case"] = True
            self._pronounce.append(rule)
        return self
    
    def set_param(self, key: str, value: Any) -> 'EphemeralAgentConfig':
        """Set a single AI parameter"""
        if key:
            self._params[key] = value
        return self
    
    def set_params(self, params: Dict[str, Any]) -> 'EphemeralAgentConfig':
        """Set multiple AI parameters"""
        if params and isinstance(params, dict):
            self._params.update(params)
        return self
    
    def set_global_data(self, data: Dict[str, Any]) -> 'EphemeralAgentConfig':
        """Set global data"""
        if data and isinstance(data, dict):
            self._global_data = data
        return self
    
    def update_global_data(self, data: Dict[str, Any]) -> 'EphemeralAgentConfig':
        """Update global data"""
        if data and isinstance(data, dict):
            self._global_data.update(data)
        return self
    
    def set_prompt_text(self, text: str) -> 'EphemeralAgentConfig':
        """Set raw prompt text"""
        self._raw_prompt = text
        return self
    
    def set_post_prompt(self, text: str) -> 'EphemeralAgentConfig':
        """Set post-prompt text"""
        self._post_prompt = text
        return self
    
    def prompt_add_section(self, title: str, body: str = "", bullets: Optional[List[str]] = None, **kwargs) -> 'EphemeralAgentConfig':
        """Add a prompt section"""
        section = {
            "title": title,
            "body": body
        }
        if bullets:
            section["bullets"] = bullets
        
        # Handle additional parameters
        for key, value in kwargs.items():
            if key in ["numbered", "numbered_bullets", "subsections"]:
                section[key] = value
        
        self._prompt_sections.append(section)
        return self
    
    def set_native_functions(self, function_names: List[str]) -> 'EphemeralAgentConfig':
        """Set native functions"""
        if function_names and isinstance(function_names, list):
            self._native_functions = [name for name in function_names if isinstance(name, str)]
        return self
    
    def add_function_include(self, url: str, functions: List[str], meta_data: Optional[Dict[str, Any]] = None) -> 'EphemeralAgentConfig':
        """Add a function include"""
        if url and functions and isinstance(functions, list):
            include = {"url": url, "functions": functions}
            if meta_data and isinstance(meta_data, dict):
                include["meta_data"] = meta_data
            self._function_includes.append(include)
        return self
    
    def extract_config(self) -> Dict[str, Any]:
        """
        Extract the configuration as a dictionary for applying to the real agent.
        
        Returns:
            Dictionary containing all the configuration changes
        """
        config = {}
        
        if self._hints:
            config["hints"] = self._hints
        if self._languages:
            config["languages"] = self._languages
        if self._pronounce:
            config["pronounce"] = self._pronounce
        if self._params:
            config["params"] = self._params
        if self._global_data:
            config["global_data"] = self._global_data
        if self._function_includes:
            config["function_includes"] = self._function_includes
        if self._native_functions:
            config["native_functions"] = self._native_functions
        
        # Handle prompt sections - these should be applied to the agent's POM, not as raw config
        # The calling code should use these to build the prompt properly
        if self._prompt_sections:
            config["_ephemeral_prompt_sections"] = self._prompt_sections
        if self._raw_prompt:
            config["_ephemeral_raw_prompt"] = self._raw_prompt
        if self._post_prompt:
            config["_ephemeral_post_prompt"] = self._post_prompt
        
        return config