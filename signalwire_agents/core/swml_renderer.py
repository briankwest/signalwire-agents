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
        add_answer: bool = True,
        format: str = "json"
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
            format: Output format, 'json' or 'yaml'
            
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
            
        # Add SWAIG if provided
        if swaig_functions:
            ai_block["ai"]["SWAIG"] = swaig_functions
            
        # Add special hooks if provided
        if startup_hook_url:
            if not "SWAIG" in ai_block["ai"]:
                ai_block["ai"]["SWAIG"] = []
                
            ai_block["ai"]["SWAIG"].append({
                "function": "startup_hook",
                "request": {
                    "url": startup_hook_url,
                    "method": "POST"
                }
            })
            
        if hangup_hook_url:
            if not "SWAIG" in ai_block["ai"]:
                ai_block["ai"]["SWAIG"] = []
                
            ai_block["ai"]["SWAIG"].append({
                "function": "hangup_hook", 
                "request": {
                    "url": hangup_hook_url,
                    "method": "POST"
                }
            })
            
        # Add params if provided
        if params:
            ai_block["ai"].update(params)
            
        # Add the AI block to the main section
        swml["sections"]["main"].append(ai_block)
        
        # Add answer block if requested
        if add_answer:
            swml["sections"]["main"].append({"answer": {}})
            
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
            return json.dumps(swml, indent=2)
