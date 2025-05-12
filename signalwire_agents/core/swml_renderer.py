"""
SwmlRenderer for generating complete SWML documents for SignalWire AI Agents
"""

from typing import Dict, List, Any, Optional, Union
import json
import yaml


class SwmlRenderer:
    """
    Renders SWML documents for SignalWire AI Agents with AI and SWAIG components
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
        default_webhook_url: Optional[str] = None
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
            
        Returns:
            SWML document as a string
        """
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
            
        # SWAIG is always included and always starts with defaults
        ai_block["ai"]["SWAIG"] = []
        
        # Add defaults as the first element when a default webhook URL is provided
        if default_webhook_url:
            defaults = {
                "defaults": {
                    "web_hook_url": default_webhook_url
                }
            }
            ai_block["ai"]["SWAIG"].append(defaults)
        
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
            ai_block["ai"]["SWAIG"].append(startup_hook)
            
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
            ai_block["ai"]["SWAIG"].append(hangup_hook)
        
        # Add regular functions from the provided list
        if swaig_functions:
            for func in swaig_functions:
                # Skip special hooks as we've already added them
                if func.get("function") not in ["startup_hook", "hangup_hook"]:
                    ai_block["ai"]["SWAIG"].append(func)
            
        # Add AI params if provided (but not rendering settings)
        if params:
            # Filter out non-AI parameters that should be separate SWML methods
            ai_params = {k: v for k, v in params.items() 
                         if k not in ["auto_answer", "record_call", "record_format", "record_stereo"]}
            
            # Only update if we have valid AI parameters
            if ai_params:
                ai_block["ai"].update(ai_params)
            
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
        format: str = "json"
    ) -> str:
        """
        Generate a SWML document for a function response
        
        Args:
            response_text: Text to say/display
            actions: List of SWML actions to execute
            format: Output format, 'json' or 'yaml'
            
        Returns:
            SWML document as a string
        """
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
