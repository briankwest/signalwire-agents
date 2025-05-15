"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

"""
SwmlRenderer for generating complete SWML documents for SignalWire AI Agents
"""

from typing import Dict, List, Any, Optional, Union
import json
import yaml

from signalwire_agents.core.swml_service import SWMLService
from signalwire_agents.core.swml_builder import SWMLBuilder


class SwmlRenderer:
    """
    Renders SWML documents for SignalWire AI Agents with AI and SWAIG components
    
    This class provides backward-compatible methods for rendering SWML documents
    while also supporting the new SWMLService architecture. It can work either
    standalone (legacy mode) or with a SWMLService instance.
    """
    
    @staticmethod
    def render_swml(
        prompt: Union[str, List[Dict[str, Any]]],
        post_prompt: Optional[str] = None,
        post_prompt_url: Optional[str] = None,
        swaig_functions: Optional[List[Dict[str, Any]]] = None,
        startup_hook_url: Optional[str] = None,
        hangup_hook_url: Optional[str] = None,
        prompt_is_pom: bool = False,
        params: Optional[Dict[str, Any]] = None,
        add_answer: bool = False,
        record_call: bool = False,
        record_format: str = "mp4",
        record_stereo: bool = True,
        format: str = "json",
        default_webhook_url: Optional[str] = None,
        service: Optional[SWMLService] = None
    ) -> str:
        """
        Generate a complete SWML document with AI configuration
        
        Args:
            prompt: Either a string prompt or a POM in list-of-dict format
            post_prompt: Optional post-prompt text (for summary)
            post_prompt_url: URL to receive the post-prompt result
            swaig_functions: List of SWAIG function definitions
            startup_hook_url: URL for startup hook
            hangup_hook_url: URL for hangup hook
            prompt_is_pom: Whether prompt is a POM object or raw text
            params: Additional AI params (temperature, etc)
            add_answer: Whether to auto-add the answer block after AI
            record_call: Whether to add a record_call block
            record_format: Format for recording the call
            record_stereo: Whether to record in stereo
            format: Output format, 'json' or 'yaml'
            default_webhook_url: Optional default webhook URL for all SWAIG functions
            service: Optional SWMLService instance to use
            
        Returns:
            SWML document as a string
        """
        # If we have a service, use it to build the document
        if service:
            # Create a builder for the service
            builder = SWMLBuilder(service)
            
            # Reset the document to start fresh
            builder.reset()
            
            # Add answer block if requested
            if add_answer:
                builder.answer()
            
            # Add record_call if requested
            if record_call:
                # TODO: Add record_call to builder API
                service.add_verb("record_call", {
                    "format": record_format,
                    "stereo": record_stereo
                })
            
            # Configure SWAIG object for AI verb
            swaig_config = {}
            functions = []
            
            # Add startup hook if provided
            if startup_hook_url:
                functions.append({
                    "function": "startup_hook",
                    "description": "Called when the call starts",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    },
                    "web_hook_url": startup_hook_url
                })
            
            # Add hangup hook if provided
            if hangup_hook_url:
                functions.append({
                    "function": "hangup_hook",
                    "description": "Called when the call ends",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    },
                    "web_hook_url": hangup_hook_url
                })
            
            # Add regular functions if provided
            if swaig_functions:
                for func in swaig_functions:
                    # Skip special hooks as we've already added them
                    if func.get("function") not in ["startup_hook", "hangup_hook"]:
                        functions.append(func)
            
            # Only add SWAIG if we have functions or a default URL
            if functions or default_webhook_url:
                swaig_config = {}
                
                # Add defaults if we have a default webhook URL
                if default_webhook_url:
                    swaig_config["defaults"] = {
                        "web_hook_url": default_webhook_url
                    }
                
                # Add functions if we have any
                if functions:
                    swaig_config["functions"] = functions
            
            # Add AI verb with appropriate configuration
            builder.ai(
                prompt_text=None if prompt_is_pom else prompt,
                prompt_pom=prompt if prompt_is_pom else None,
                post_prompt=post_prompt,
                post_prompt_url=post_prompt_url,
                swaig=swaig_config if swaig_config else None,
                **(params or {})
            )
            
            # Get the document as a dictionary or string based on format
            if format.lower() == "yaml":
                import yaml
                return yaml.dump(builder.build(), sort_keys=False)
            else:
                return builder.render()
        else:
            # Legacy implementation (unchanged for backward compatibility)
            # Start building the SWML document
            swml = {
                "version": "1.0.0",
                "sections": {
                    "main": []
                }
            }
            
            # Build the AI block
            ai_block = {
                "ai": {
                    "prompt": {}
                }
            }
            
            # Set prompt based on type
            if prompt_is_pom:
                ai_block["ai"]["prompt"]["pom"] = prompt
            else:
                ai_block["ai"]["prompt"]["text"] = prompt
                
            # Add post_prompt if provided
            if post_prompt:
                ai_block["ai"]["post_prompt"] = {
                    "text": post_prompt
                }
                
            # Add post_prompt_url if provided
            if post_prompt_url:
                ai_block["ai"]["post_prompt_url"] = post_prompt_url
                
            # SWAIG is a dictionary not an array (fix from old implementation)
            ai_block["ai"]["SWAIG"] = {}
            
            # Add defaults if we have a default webhook URL
            if default_webhook_url:
                ai_block["ai"]["SWAIG"]["defaults"] = {
                    "web_hook_url": default_webhook_url
                }
            
            # Collect all functions
            functions = []
            
            # Add SWAIG hooks if provided
            if startup_hook_url:
                startup_hook = {
                    "function": "startup_hook",
                    "description": "Called when the call starts",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    },
                    "web_hook_url": startup_hook_url
                }
                functions.append(startup_hook)
                
            if hangup_hook_url:
                hangup_hook = {
                    "function": "hangup_hook",
                    "description": "Called when the call ends",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    },
                    "web_hook_url": hangup_hook_url
                }
                functions.append(hangup_hook)
            
            # Add regular functions from the provided list
            if swaig_functions:
                for func in swaig_functions:
                    # Skip special hooks as we've already added them
                    if func.get("function") not in ["startup_hook", "hangup_hook"]:
                        functions.append(func)
            
            # Add functions to SWAIG if we have any
            if functions:
                ai_block["ai"]["SWAIG"]["functions"] = functions
                
            # Add AI params if provided (but not rendering settings)
            if params:
                # Filter out non-AI parameters that should be separate SWML methods
                ai_params = {k: v for k, v in params.items() 
                             if k not in ["auto_answer", "record_call", "record_format", "record_stereo"]}
                
                # Only update if we have valid AI parameters
                if ai_params:
                    ai_block["ai"]["params"] = ai_params
                
            # Start building the SWML blocks
            main_blocks = []
            
            # Add answer block first if requested (to answer the call)
            if add_answer:
                main_blocks.append({"answer": {}})
                
            # Add record_call block next if requested
            if record_call:
                main_blocks.append({
                    "record_call": {
                        "format": record_format,
                        "stereo": record_stereo  # SWML expects a boolean not a string
                    }
                })
            
            # Add the AI block
            main_blocks.append(ai_block)
            
            # Set the main section to our ordered blocks
            swml["sections"]["main"] = main_blocks
            
            # Return in requested format
            if format.lower() == "yaml":
                return yaml.dump(swml, sort_keys=False)
            else:
                return json.dumps(swml, indent=2)
            
    @staticmethod
    def render_function_response_swml(
        response_text: str,
        actions: Optional[List[Dict[str, Any]]] = None,
        format: str = "json",
        service: Optional[SWMLService] = None
    ) -> str:
        """
        Generate a SWML document for a function response
        
        Args:
            response_text: Text to say/display
            actions: List of SWML actions to execute
            format: Output format, 'json' or 'yaml'
            service: Optional SWMLService instance to use
            
        Returns:
            SWML document as a string
        """
        if service:
            # Use the service to build the document
            service.reset_document()
            
            # Add a play block for the response if provided
            if response_text:
                service.add_verb("play", {
                    "url": f"say:{response_text}"
                })
                
            # Add any actions
            if actions:
                for action in actions:
                    if action["type"] == "play":
                        service.add_verb("play", {
                            "url": action["url"]
                        })
                    elif action["type"] == "transfer":
                        service.add_verb("connect", [
                            {"to": action["dest"]}
                        ])
                    elif action["type"] == "hang_up":
                        service.add_verb("hangup", {})
                    # Additional action types could be added here
            
            # Return in requested format
            if format.lower() == "yaml":
                import yaml
                return yaml.dump(service.get_document(), sort_keys=False)
            else:
                return service.render_document()
        else:
            # Legacy implementation (unchanged for backward compatibility)
            swml = {
                "version": "1.0.0",
                "sections": {
                    "main": []
                }
            }
            
            # Add a play block for the response if provided
            if response_text:
                swml["sections"]["main"].append({
                    "play": {
                        "url": f"say:{response_text}"
                    }
                })
                
            # Add any actions
            if actions:
                for action in actions:
                    if action["type"] == "play":
                        swml["sections"]["main"].append({
                            "play": {
                                "url": action["url"]
                            }
                        })
                    elif action["type"] == "transfer":
                        swml["sections"]["main"].append({
                            "connect": [
                                {"to": action["dest"]}
                            ]
                        })
                    elif action["type"] == "hang_up":
                        swml["sections"]["main"].append({
                            "hangup": {}
                        })
                    # Additional action types could be added here
                    
            # Return in requested format
            if format.lower() == "yaml":
                return yaml.dump(swml, sort_keys=False)
            else:
                return json.dumps(swml)
