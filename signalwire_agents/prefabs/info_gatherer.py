"""
InfoGathererAgent - Prefab agent for collecting structured information from users
"""

from typing import List, Dict, Any, Optional, Union
import json
import os

from signalwire_agents.core.agent_base import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult


class InfoGathererAgent(AgentBase):
    """
    A prefab agent designed to collect specific fields of information from a user.
    
    This agent will:
    1. Ask for each requested field
    2. Confirm the collected information
    3. Return a structured JSON summary
    
    Example:
        agent = InfoGathererAgent(
            fields=[
                {"name": "full_name", "prompt": "What is your full name?"},
                {"name": "reason", "prompt": "How can I help you today?"}
            ],
            confirmation_template="Thanks {full_name}, I'll help you with {reason}."
        )
    """
    
    def __init__(
        self,
        fields: List[Dict[str, str]],
        confirmation_template: Optional[str] = None,
        summary_format: Optional[Dict[str, Any]] = None,
        name: str = "info_gatherer", 
        route: str = "/info_gatherer",
        schema_path: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize an information gathering agent
        
        Args:
            fields: List of fields to collect, each with:
                - name: Field name (for storage)
                - prompt: Question to ask to collect the field
                - validation: Optional regex or description of valid inputs
            confirmation_template: Optional template string for confirming collected info
                Format with field names in {brackets}, e.g. "Thanks {name}!"
            summary_format: Optional JSON template for the post_prompt summary
            name: Agent name for the route
            route: HTTP route for this agent
            schema_path: Optional path to a custom schema
            **kwargs: Additional arguments for AgentBase
        """
        # Find schema.json if not provided
        if not schema_path:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(os.path.dirname(current_dir))
            
            schema_locations = [
                os.path.join(current_dir, "schema.json"),
                os.path.join(parent_dir, "schema.json")
            ]
            
            for loc in schema_locations:
                if os.path.exists(loc):
                    schema_path = loc
                    break
                    
        # Initialize the base agent
        super().__init__(
            name=name,
            route=route,
            use_pom=True,
            schema_path=schema_path,
            **kwargs
        )
        
        self.fields = fields
        self.confirmation_template = confirmation_template
        self.summary_format = summary_format
        
        # Build the prompt
        self._build_info_gatherer_prompt()
        
        # Set up the post-prompt template
        self._setup_post_prompt()
        
        # Configure additional agent settings
        self._configure_agent_settings()
    
    def _build_info_gatherer_prompt(self):
        """Build the agent prompt for information gathering"""
        # Create base instructions
        instructions = [
            "Ask for ONLY ONE piece of information at a time.",
            "Confirm each answer before moving to the next question.",
            "Do not ask for information not in your field list.",
            "Be polite but direct with your questions."
        ]
        
        # Add field-specific instructions
        for i, field in enumerate(self.fields, 1):
            field_name = field.get("name")
            field_prompt = field.get("prompt")
            validation = field.get("validation", "")
            
            field_text = f"{i}. {field_name}: \"{field_prompt}\""
            if validation:
                field_text += f" ({validation})"
                
            instructions.append(field_text)
        
        # Add confirmation instruction if a template is provided
        if self.confirmation_template:
            instructions.append(
                f"After collecting all fields, confirm with: {self.confirmation_template}"
            )
            
        # Create the prompt sections directly using prompt_add_section
        self.prompt_add_section(
            "Personality", 
            body="You are a friendly and efficient virtual assistant."
        )
        
        self.prompt_add_section(
            "Goal", 
            body="Your job is to collect specific information from the user."
        )
        
        self.prompt_add_section(
            "Instructions",
            bullets=instructions
        )
    
    def _setup_post_prompt(self):
        """Set up the post-prompt for summary formatting"""
        # Build a JSON template for the collected data
        if not self.summary_format:
            # Default format: a flat dictionary of field values
            field_list = ", ".join([f'"{f["name"]}": "%{{{f["name"]}}}"' for f in self.fields])
            post_prompt = f"""
            Return a JSON object with all the information collected:
            {{
                {field_list}
            }}
            """
        else:
            # Format is provided as a template - just serialize it
            post_prompt = f"""
            Return the following JSON structure with the collected information:
            {json.dumps(self.summary_format, indent=2)}
            """
            
        self.set_post_prompt(post_prompt)
    
    def _configure_agent_settings(self):
        """Configure additional agent settings"""
        # Add field names as hints to help the AI recognize them
        field_names = [field.get("name") for field in self.fields if "name" in field]
        self.add_hints(field_names)
        
        # Set AI behavior parameters for better information collection
        self.set_params({
            "wait_for_user": False,
            "end_of_speech_timeout": 1200,  # Slightly longer for thoughtful responses
            "ai_volume": 5,
            "digit_timeout": 3000,  # 3 seconds for DTMF input timeout
            "energy_level": 50  # Medium energy threshold
        })
        
        # Add global data with the fields structure
        self.set_global_data({
            "fields": [
                {
                    "name": field.get("name"),
                    "prompt": field.get("prompt")
                }
                for field in self.fields
            ]
        })
    
    @AgentBase.tool(
        name="validate_field",
        description="Validate if the provided value is valid for a specific field",
        parameters={
            "field_name": {
                "type": "string",
                "description": "The name of the field to validate"
            },
            "value": {
                "type": "string",
                "description": "The value provided by the user"
            }
        }
    )
    def validate_field(self, args, raw_data):
        """
        Validate if a provided value is valid for a specific field
        
        This function checks if a user's input meets any validation criteria
        specified for the field.
        """
        field_name = args.get("field_name", "")
        value = args.get("value", "")
        
        # Find the field by name
        field = None
        for f in self.fields:
            if f.get("name") == field_name:
                field = f
                break
                
        if not field:
            return SwaigFunctionResult(f"Error: Field '{field_name}' not found in configuration.")
        
        # Check if the field has validation requirements
        validation = field.get("validation", "")
        
        # Simple validation check (in a real implementation, you would perform
        # more sophisticated validation based on the validation rules)
        if validation and not value.strip():
            return SwaigFunctionResult({
                "response": f"The field '{field_name}' cannot be empty.",
                "valid": False
            })
        
        # For this simple example, we'll consider any non-empty value valid
        return SwaigFunctionResult({
            "response": f"The value for '{field_name}' is valid.",
            "valid": True
        })
    
    def on_summary(self, summary, raw_data=None):
        """
        Process the collected information summary
        
        Args:
            summary: Dictionary of collected field values
            raw_data: The complete raw POST data from the request
            
        Override this method in subclasses to use the collected data.
        """
        if summary:
            if isinstance(summary, dict):
                print(f"Information collected: {json.dumps(summary, indent=2)}")
            else:
                print(f"Information collected: {summary}")
        
        # Subclasses should override this to save or process the collected data
