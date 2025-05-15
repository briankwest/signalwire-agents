"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

"""
Utilities for working with the SWML JSON schema.

This module provides functions for loading, parsing, and validating SWML schemas.
It also provides utilities for working with SWML documents based on the schema.
"""

import json
import os
import re
from typing import Dict, List, Any, Optional, Set, Tuple, Callable


class SchemaUtils:
    """
    Utilities for working with SWML JSON schema.
    
    This class provides methods for:
    - Loading and parsing schema files
    - Extracting verb definitions
    - Validating SWML objects against the schema
    - Generating helpers for schema operations
    """
    
    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize the SchemaUtils with the provided schema
        
        Args:
            schema_path: Path to the schema file (optional)
        """
        self.schema_path = schema_path
        if not self.schema_path:
            self.schema_path = self._get_default_schema_path()
            print(f"No schema_path provided, using default: {self.schema_path}")
        
        self.schema = self.load_schema()
        self.verbs = self._extract_verb_definitions()
        print(f"Extracted {len(self.verbs)} verbs from schema")
        if self.verbs:
            print(f"First few verbs: {list(self.verbs.keys())[:5]}")
        
    def _get_default_schema_path(self) -> str:
        """
        Get the default path to the schema file
        
        Returns:
            Path to the schema file
        """
        # Default path is the schema.json in the root directory
        package_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        default_path = os.path.join(package_dir, "schema.json")
        print(f"Default schema path: {default_path}")
        print(f"Path exists: {os.path.exists(default_path)}")
        
        return default_path
        
    def load_schema(self) -> Dict[str, Any]:
        """
        Load the JSON schema from the specified path
        
        Returns:
            The schema as a dictionary
        """
        if not self.schema_path:
            print(f"Warning: No schema path provided. Using empty schema.")
            return {}
            
        try:
            print(f"Attempting to load schema from: {self.schema_path}")
            print(f"File exists: {os.path.exists(self.schema_path)}")
            
            if os.path.exists(self.schema_path):
                with open(self.schema_path, "r") as f:
                    schema = json.load(f)
                print(f"Successfully loaded schema from {self.schema_path}")
                print(f"Schema has {len(schema.keys()) if schema else 0} top-level keys")
                if "$defs" in schema:
                    print(f"Schema has {len(schema['$defs'])} definitions")
                return schema
            else:
                print(f"Schema file not found at {self.schema_path}")
                return {}
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading schema: {e}")
            print(f"Using empty schema as fallback")
            return {}
    
    def _extract_verb_definitions(self) -> Dict[str, Dict[str, Any]]:
        """
        Extract verb definitions from the schema
        
        Returns:
            A dictionary mapping verb names to their definitions
        """
        verbs = {}
        
        # Extract from SWMLMethod anyOf
        if "$defs" in self.schema and "SWMLMethod" in self.schema["$defs"]:
            swml_method = self.schema["$defs"]["SWMLMethod"]
            print(f"Found SWMLMethod in schema with keys: {swml_method.keys()}")
            
            if "anyOf" in swml_method:
                print(f"Found anyOf in SWMLMethod with {len(swml_method['anyOf'])} items")
                
                for ref in swml_method["anyOf"]:
                    if "$ref" in ref:
                        # Extract the verb name from the reference
                        verb_ref = ref["$ref"]
                        verb_name = verb_ref.split("/")[-1]
                        print(f"Processing verb reference: {verb_ref} -> {verb_name}")
                        
                        # Look up the verb definition
                        if verb_name in self.schema["$defs"]:
                            verb_def = self.schema["$defs"][verb_name]
                            
                            # Extract the actual verb name (lowercase)
                            if "properties" in verb_def:
                                prop_names = list(verb_def["properties"].keys())
                                if prop_names:
                                    actual_verb = prop_names[0]
                                    verbs[actual_verb] = {
                                        "name": actual_verb,
                                        "schema_name": verb_name,
                                        "definition": verb_def
                                    }
                                    print(f"Added verb: {actual_verb}")
        else:
            print(f"Missing $defs or SWMLMethod in schema")
            if "$defs" in self.schema:
                print(f"Available definitions: {list(self.schema['$defs'].keys())}")
        
        return verbs
    
    def get_verb_properties(self, verb_name: str) -> Dict[str, Any]:
        """
        Get the properties for a specific verb
        
        Args:
            verb_name: The name of the verb (e.g., "ai", "answer", etc.)
            
        Returns:
            The properties for the verb or an empty dict if not found
        """
        if verb_name in self.verbs:
            verb_def = self.verbs[verb_name]["definition"]
            if "properties" in verb_def and verb_name in verb_def["properties"]:
                return verb_def["properties"][verb_name]
        return {}
    
    def get_verb_required_properties(self, verb_name: str) -> List[str]:
        """
        Get the required properties for a specific verb
        
        Args:
            verb_name: The name of the verb (e.g., "ai", "answer", etc.)
            
        Returns:
            List of required property names for the verb or an empty list if not found
        """
        if verb_name in self.verbs:
            verb_def = self.verbs[verb_name]["definition"]
            if "properties" in verb_def and verb_name in verb_def["properties"]:
                verb_props = verb_def["properties"][verb_name]
                return verb_props.get("required", [])
        return []
    
    def validate_verb(self, verb_name: str, verb_config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a verb configuration against the schema
        
        Args:
            verb_name: The name of the verb (e.g., "ai", "answer", etc.)
            verb_config: The configuration for the verb
            
        Returns:
            (is_valid, error_messages) tuple
        """
        # Simple validation for now - can be enhanced with more complete JSON Schema validation
        errors = []
        
        # Check if the verb exists in the schema
        if verb_name not in self.verbs:
            errors.append(f"Unknown verb: {verb_name}")
            return False, errors
            
        # Get the required properties for this verb
        required_props = self.get_verb_required_properties(verb_name)
        
        # Check if all required properties are present
        for prop in required_props:
            if prop not in verb_config:
                errors.append(f"Missing required property '{prop}' for verb '{verb_name}'")
                
        # Return validation result
        return len(errors) == 0, errors
    
    def get_all_verb_names(self) -> List[str]:
        """
        Get all verb names defined in the schema
        
        Returns:
            List of verb names
        """
        return list(self.verbs.keys())
        
    def get_verb_parameters(self, verb_name: str) -> Dict[str, Any]:
        """
        Get the parameter definitions for a specific verb
        
        Args:
            verb_name: The name of the verb (e.g., "ai", "answer", etc.)
            
        Returns:
            Dictionary mapping parameter names to their definitions
        """
        properties = self.get_verb_properties(verb_name)
        if "properties" in properties:
            return properties["properties"]
        return {}
        
    def generate_method_signature(self, verb_name: str) -> str:
        """
        Generate a Python method signature for a verb
        
        Args:
            verb_name: The name of the verb
            
        Returns:
            A Python method signature string
        """
        # Get the verb properties
        verb_props = self.get_verb_properties(verb_name)
        
        # Get verb parameters
        verb_params = self.get_verb_parameters(verb_name)
        
        # Get required parameters
        required_params = self.get_verb_required_properties(verb_name)
        
        # Initialize method parameters
        param_list = ["self"]
        
        # Add the parameters
        for param_name, param_def in verb_params.items():
            # Check if this is a required parameter
            is_required = param_name in required_params
            
            # Determine parameter type annotation
            param_type = self._get_type_annotation(param_def)
            
            # Add default value if not required
            if is_required:
                param_list.append(f"{param_name}: {param_type}")
            else:
                param_list.append(f"{param_name}: Optional[{param_type}] = None")
        
        # Add **kwargs at the end
        param_list.append("**kwargs")
        
        # Generate method docstring
        docstring = f'"""\n        Add the {verb_name} verb to the current document\n        \n'
        
        # Add parameter documentation
        for param_name, param_def in verb_params.items():
            description = param_def.get("description", "")
            # Clean up the description for docstring
            description = description.replace('\n', ' ').strip()
            docstring += f"        Args:\n            {param_name}: {description}\n"
            
        # Add return documentation
        docstring += f'        \n        Returns:\n            True if the verb was added successfully, False otherwise\n        """\n'
        
        # Create the full method signature with docstring
        method_signature = f"def {verb_name}({', '.join(param_list)}) -> bool:\n{docstring}"
        
        return method_signature
        
    def generate_method_body(self, verb_name: str) -> str:
        """
        Generate the method body implementation for a verb
        
        Args:
            verb_name: The name of the verb
            
        Returns:
            The method body as a string
        """
        # Get verb parameters
        verb_params = self.get_verb_parameters(verb_name)
        
        body = []
        body.append("        # Prepare the configuration")
        body.append("        config = {}")
        
        # Add handling for each parameter
        for param_name in verb_params.keys():
            body.append(f"        if {param_name} is not None:")
            body.append(f"            config['{param_name}'] = {param_name}")
            
        # Add handling for kwargs
        body.append("        # Add any additional parameters from kwargs")
        body.append("        for key, value in kwargs.items():")
        body.append("            if value is not None:")
        body.append("                config[key] = value")
        
        # Add the call to add_verb
        body.append("")
        body.append(f"        # Add the {verb_name} verb")
        body.append(f"        return self.add_verb('{verb_name}', config)")
        
        return "\n".join(body)
    
    def _get_type_annotation(self, param_def: Dict[str, Any]) -> str:
        """
        Get the Python type annotation for a parameter
        
        Args:
            param_def: Parameter definition from the schema
            
        Returns:
            Python type annotation as a string
        """
        schema_type = param_def.get("type")
        
        if schema_type == "string":
            return "str"
        elif schema_type == "integer":
            return "int"
        elif schema_type == "number":
            return "float"
        elif schema_type == "boolean":
            return "bool"
        elif schema_type == "array":
            item_type = "Any"
            if "items" in param_def:
                item_def = param_def["items"]
                item_type = self._get_type_annotation(item_def)
            return f"List[{item_type}]"
        elif schema_type == "object":
            return "Dict[str, Any]"
        else:
            # Handle complex types or oneOf/anyOf
            if "anyOf" in param_def or "oneOf" in param_def:
                return "Any"
            if "$ref" in param_def:
                return "Any"  # Could be enhanced to resolve references
            return "Any" 