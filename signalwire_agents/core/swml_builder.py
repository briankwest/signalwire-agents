"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

"""
SWML Builder - Fluent API for building SWML documents

This module provides a fluent builder API for creating SWML documents.
It allows for chaining method calls to build up a document step by step.
"""

from typing import Dict, List, Any, Optional, Union, TypeVar
try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # For Python 3.9-3.10

from signalwire_agents.core.swml_service import SWMLService


T = TypeVar('T', bound='SWMLBuilder')


class SWMLBuilder:
    """
    Fluent builder for SWML documents
    
    This class provides a fluent interface for building SWML documents
    by chaining method calls. It delegates to an underlying SWMLService
    instance for the actual document creation.
    """
    
    def __init__(self, service: SWMLService):
        """
        Initialize with a SWMLService instance
        
        Args:
            service: The SWMLService to delegate to
        """
        self.service = service
    
    def answer(self, max_duration: Optional[int] = None, codecs: Optional[str] = None) -> Self:
        """
        Add an 'answer' verb to the main section
        
        Args:
            max_duration: Maximum duration in seconds
            codecs: Comma-separated list of codecs
            
        Returns:
            Self for method chaining
        """
        self.service.add_answer_verb(max_duration, codecs)
        return self
    
    def hangup(self, reason: Optional[str] = None) -> Self:
        """
        Add a 'hangup' verb to the main section
        
        Args:
            reason: Optional reason for hangup
            
        Returns:
            Self for method chaining
        """
        self.service.add_hangup_verb(reason)
        return self
    
    def ai(self, 
          prompt_text: Optional[str] = None,
          prompt_pom: Optional[List[Dict[str, Any]]] = None,
          post_prompt: Optional[str] = None,
          post_prompt_url: Optional[str] = None,
          swaig: Optional[Dict[str, Any]] = None,
          **kwargs) -> Self:
        """
        Add an 'ai' verb to the main section
        
        Args:
            prompt_text: Text prompt for the AI (mutually exclusive with prompt_pom)
            prompt_pom: POM structure for the AI prompt (mutually exclusive with prompt_text)
            post_prompt: Optional post-prompt text
            post_prompt_url: Optional URL for post-prompt processing
            swaig: Optional SWAIG configuration
            **kwargs: Additional AI parameters
            
        Returns:
            Self for method chaining
        """
        self.service.add_ai_verb(
            prompt_text=prompt_text,
            prompt_pom=prompt_pom,
            post_prompt=post_prompt,
            post_prompt_url=post_prompt_url,
            swaig=swaig,
            **kwargs
        )
        return self
    
    def play(self, url: Optional[str] = None, urls: Optional[List[str]] = None, 
             volume: Optional[float] = None, say_voice: Optional[str] = None, 
             say_language: Optional[str] = None, say_gender: Optional[str] = None,
             auto_answer: Optional[bool] = None) -> Self:
        """
        Add a 'play' verb to the main section
        
        Args:
            url: Single URL to play (mutually exclusive with urls)
            urls: List of URLs to play (mutually exclusive with url)
            volume: Volume level (-40 to 40)
            say_voice: Voice for text-to-speech
            say_language: Language for text-to-speech
            say_gender: Gender for text-to-speech
            auto_answer: Whether to auto-answer the call
            
        Returns:
            Self for method chaining
        """
        # Create base config
        config = {}
        
        # Add play config (either single URL or list)
        if url is not None:
            config["url"] = url
        elif urls is not None:
            config["urls"] = urls
        else:
            raise ValueError("Either url or urls must be provided")
        
        # Add optional parameters
        if volume is not None:
            config["volume"] = volume
        if say_voice is not None:
            config["say_voice"] = say_voice
        if say_language is not None:
            config["say_language"] = say_language
        if say_gender is not None:
            config["say_gender"] = say_gender
        if auto_answer is not None:
            config["auto_answer"] = auto_answer
        
        # Add the verb
        self.service.add_verb("play", config)
        return self
    
    def say(self, text: str, voice: Optional[str] = None, 
            language: Optional[str] = None, gender: Optional[str] = None,
            volume: Optional[float] = None) -> Self:
        """
        Add a 'play' verb with say: prefix for text-to-speech
        
        Args:
            text: Text to speak
            voice: Voice for text-to-speech
            language: Language for text-to-speech
            gender: Gender for text-to-speech
            volume: Volume level (-40 to 40)
            
        Returns:
            Self for method chaining
        """
        # Create play config with say: prefix
        url = f"say:{text}"
        
        # Add the verb
        return self.play(
            url=url,
            say_voice=voice,
            say_language=language,
            say_gender=gender,
            volume=volume
        )
    
    def add_section(self, section_name: str) -> Self:
        """
        Add a new section to the document
        
        Args:
            section_name: Name of the section to add
            
        Returns:
            Self for method chaining
        """
        self.service.add_section(section_name)
        return self
    
    def build(self) -> Dict[str, Any]:
        """
        Build and return the SWML document
        
        Returns:
            The complete SWML document as a dictionary
        """
        return self.service.get_document()
    
    def render(self) -> str:
        """
        Build and render the SWML document as a JSON string
        
        Returns:
            The complete SWML document as a JSON string
        """
        return self.service.render_document()
    
    def reset(self) -> Self:
        """
        Reset the document to an empty state
        
        Returns:
            Self for method chaining
        """
        self.service.reset_document()
        return self 