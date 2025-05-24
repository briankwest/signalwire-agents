"""
Contexts and Steps System for SignalWire Agents

This module provides an alternative to traditional POM-based prompts by allowing
agents to be defined as structured contexts with sequential steps. Each step
contains its own prompt, completion criteria, and function restrictions.
"""

from typing import Dict, List, Optional, Union, Any


class Step:
    """Represents a single step within a context"""
    
    def __init__(self, name: str):
        self.name = name
        self._text: Optional[str] = None
        self._step_criteria: Optional[str] = None
        self._functions: Optional[Union[str, List[str]]] = None
        self._valid_steps: Optional[List[str]] = None
        
        # POM-style sections for rich prompts
        self._sections: List[Dict[str, Any]] = []
    
    def set_text(self, text: str) -> 'Step':
        """
        Set the step's prompt text directly
        
        Args:
            text: The prompt text for this step
            
        Returns:
            Self for method chaining
        """
        if self._sections:
            raise ValueError("Cannot use set_text() when POM sections have been added. Use one approach or the other.")
        self._text = text
        return self
    
    def add_section(self, title: str, body: str) -> 'Step':
        """
        Add a POM section to the step
        
        Args:
            title: Section title
            body: Section body text
            
        Returns:
            Self for method chaining
        """
        if self._text is not None:
            raise ValueError("Cannot add POM sections when set_text() has been used. Use one approach or the other.")
        self._sections.append({"title": title, "body": body})
        return self
    
    def add_bullets(self, title: str, bullets: List[str]) -> 'Step':
        """
        Add a POM section with bullet points
        
        Args:
            title: Section title
            bullets: List of bullet points
            
        Returns:
            Self for method chaining
        """
        if self._text is not None:
            raise ValueError("Cannot add POM sections when set_text() has been used. Use one approach or the other.")
        self._sections.append({"title": title, "bullets": bullets})
        return self
    
    def set_step_criteria(self, criteria: str) -> 'Step':
        """
        Set the criteria for determining when this step is complete
        
        Args:
            criteria: Description of step completion criteria
            
        Returns:
            Self for method chaining
        """
        self._step_criteria = criteria
        return self
    
    def set_functions(self, functions: Union[str, List[str]]) -> 'Step':
        """
        Set which functions are available in this step
        
        Args:
            functions: "none" to disable all functions, or list of function names
            
        Returns:
            Self for method chaining
        """
        self._functions = functions
        return self
    
    def set_valid_steps(self, steps: List[str]) -> 'Step':
        """
        Set which steps can be navigated to from this step
        
        Args:
            steps: List of valid step names (include "next" for sequential flow)
            
        Returns:
            Self for method chaining
        """
        self._valid_steps = steps
        return self
    
    def _render_text(self) -> str:
        """Render the step's prompt text"""
        if self._text is not None:
            return self._text
        
        if not self._sections:
            raise ValueError(f"Step '{self.name}' has no text or POM sections defined")
        
        # Convert POM sections to markdown
        markdown_parts = []
        for section in self._sections:
            if "bullets" in section:
                markdown_parts.append(f"## {section['title']}")
                for bullet in section["bullets"]:
                    markdown_parts.append(f"- {bullet}")
            else:
                markdown_parts.append(f"## {section['title']}")
                markdown_parts.append(section["body"])
            markdown_parts.append("")  # Add spacing
        
        return "\n".join(markdown_parts).strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary for SWML generation"""
        step_dict = {
            "text": self._render_text()
        }
        
        if self._step_criteria:
            step_dict["step_criteria"] = self._step_criteria
            
        if self._functions is not None:
            step_dict["functions"] = self._functions
            
        if self._valid_steps is not None:
            step_dict["valid_steps"] = self._valid_steps
            
        return step_dict


class Context:
    """Represents a single context containing multiple steps"""
    
    def __init__(self, name: str):
        self.name = name
        self._steps: Dict[str, Step] = {}
        self._step_order: List[str] = []
        self._valid_contexts: Optional[List[str]] = None
    
    def add_step(self, name: str) -> Step:
        """
        Add a new step to this context
        
        Args:
            name: Step name
            
        Returns:
            Step object for method chaining
        """
        if name in self._steps:
            raise ValueError(f"Step '{name}' already exists in context '{self.name}'")
        
        step = Step(name)
        self._steps[name] = step
        self._step_order.append(name)
        return step
    
    def set_valid_contexts(self, contexts: List[str]) -> 'Context':
        """
        Set which contexts can be navigated to from this context
        
        Args:
            contexts: List of valid context names
            
        Returns:
            Self for method chaining
        """
        self._valid_contexts = contexts
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for SWML generation"""
        if not self._steps:
            raise ValueError(f"Context '{self.name}' has no steps defined")
        
        context_dict = {
            "steps": [self._steps[name].to_dict() for name in self._step_order]
        }
        
        if self._valid_contexts is not None:
            context_dict["valid_contexts"] = self._valid_contexts
            
        return context_dict


class ContextBuilder:
    """Main builder class for creating contexts and steps"""
    
    def __init__(self, agent):
        self._agent = agent
        self._contexts: Dict[str, Context] = {}
        self._context_order: List[str] = []
    
    def add_context(self, name: str) -> Context:
        """
        Add a new context
        
        Args:
            name: Context name
            
        Returns:
            Context object for method chaining
        """
        if name in self._contexts:
            raise ValueError(f"Context '{name}' already exists")
        
        context = Context(name)
        self._contexts[name] = context
        self._context_order.append(name)
        return context
    
    def validate(self) -> None:
        """Validate the contexts configuration"""
        if not self._contexts:
            raise ValueError("At least one context must be defined")
        
        # If only one context, it must be named "default"
        if len(self._contexts) == 1:
            context_name = list(self._contexts.keys())[0]
            if context_name != "default":
                raise ValueError("When using a single context, it must be named 'default'")
        
        # Validate each context has at least one step
        for context_name, context in self._contexts.items():
            if not context._steps:
                raise ValueError(f"Context '{context_name}' must have at least one step")
        
        # Validate step references in valid_steps
        for context_name, context in self._contexts.items():
            for step_name, step in context._steps.items():
                if step._valid_steps:
                    for valid_step in step._valid_steps:
                        if valid_step != "next" and valid_step not in context._steps:
                            raise ValueError(
                                f"Step '{step_name}' in context '{context_name}' "
                                f"references unknown step '{valid_step}'"
                            )
        
        # Validate context references in valid_contexts
        for context_name, context in self._contexts.items():
            if context._valid_contexts:
                for valid_context in context._valid_contexts:
                    if valid_context not in self._contexts:
                        raise ValueError(
                            f"Context '{context_name}' references unknown context '{valid_context}'"
                        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert all contexts to dictionary for SWML generation"""
        self.validate()
        
        return {
            context_name: context.to_dict() 
            for context_name in self._context_order 
            for context_name, context in [(context_name, self._contexts[context_name])]
        }


def create_simple_context(name: str = "default") -> Context:
    """
    Helper function to create a simple single context
    
    Args:
        name: Context name (defaults to "default")
        
    Returns:
        Context object for method chaining
    """
    return Context(name) 