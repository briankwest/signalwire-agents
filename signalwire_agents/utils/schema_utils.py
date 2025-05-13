"""
Utilities for working with the SWML JSON schema.

This module provides functions for loading, parsing, and validating SWML schemas.
It also provides utilities for working with SWML documents based on the schema.
"""

import json
import os
from typing import Dict, List, Any, Optional, Set, Tuple


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
        self.schema = self.load_schema()
        self.verbs = self._extract_verb_definitions()
        
    def _get_default_schema_path(self) -> str:
        """
        Get the default path to the schema file
        
        Returns:
            Path to the schema file
        """
        # Default path is the schema.json in the root directory
        package_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(package_dir, "schema.json")
        
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
            with open(self.schema_path, "r") as f:
                schema = json.load(f)
            print(f"Successfully loaded schema from {self.schema_path}")
            return schema
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
            if "anyOf" in swml_method:
                for ref in swml_method["anyOf"]:
                    if "$ref" in ref:
                        # Extract the verb name from the reference
                        verb_ref = ref["$ref"]
                        verb_name = verb_ref.split("/")[-1]
                        
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