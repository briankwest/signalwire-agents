"""
InfoGathererAgent - Prefab agent for collecting structured information from users
"""

from typing import List, Dict, Any, Optional, Union
import json

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
            **kwargs: Additional arguments for AgentBase
        """
        super().__init__(**kwargs)
        
        self.fields = fields
        self.confirmation_template = confirmation_template
        self.summary_format = summary_format
        
        # Build the prompt
        self._build_info_gatherer_prompt()
        
        # Set up the post-prompt template
        self._setup_post_prompt()
    
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
            
        # Define the prompt sections declaratively
        self.PROMPT_SECTIONS = {
            "Personality": "You are a friendly and efficient virtual assistant.",
            "Goal": "Your job is to collect specific information from the user.",
            "Instructions": instructions
        }
        
        # Process the prompt sections 
        self._process_prompt_sections()
    
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
    
    def on_summary(self, summary: Dict[str, Any]) -> None:
        """
        Process the collected information summary
        
        Args:
            summary: Dictionary of collected field values
            
        Override this method in subclasses to use the collected data.
        """
        print(f"Information collected: {json.dumps(summary, indent=2)}")
        
        # Subclasses should override this to save or process the collected data
