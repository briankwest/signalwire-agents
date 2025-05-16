"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

"""
AgentServer - Class for hosting multiple SignalWire AI Agents in a single server
"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple, Callable

try:
    from fastapi import FastAPI, Request, Response
    import uvicorn
except ImportError:
    raise ImportError(
        "fastapi and uvicorn are required. Install them with: pip install fastapi uvicorn"
    )

from signalwire_agents.core.agent_base import AgentBase
from signalwire_agents.core.swml_service import SWMLService


class AgentServer:
    """
    Server for hosting multiple SignalWire AI Agents under a single FastAPI application.
    
    This allows you to run multiple agents on different routes of the same server,
    which is useful for deployment and resource management.
    
    Example:
        server = AgentServer()
        server.register(SupportAgent(), "/support")
        server.register(SalesAgent(), "/sales") 
        server.run()
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 3000, log_level: str = "info"):
        """
        Initialize a new agent server
        
        Args:
            host: Host to bind the server to
            port: Port to bind the server to
            log_level: Logging level (debug, info, warning, error)
        """
        self.host = host
        self.port = port
        self.log_level = log_level.lower()
        
        # Set up logging
        numeric_level = getattr(logging, self.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=numeric_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("AgentServer")
        
        # Create FastAPI app
        self.app = FastAPI(
            title="SignalWire AI Agents",
            description="Hosted SignalWire AI Agents",
            version="0.1.2"
        )
        
        # Keep track of registered agents
        self.agents: Dict[str, AgentBase] = {}
        
        # Keep track of SIP routing configuration
        self._sip_routing_enabled = False
        self._sip_route = None
        self._sip_username_mapping: Dict[str, str] = {}  # Maps SIP usernames to routes
    
    def register(self, agent: AgentBase, route: Optional[str] = None) -> None:
        """
        Register an agent with the server
        
        Args:
            agent: The agent to register
            route: Optional route to override the agent's default route
            
        Raises:
            ValueError: If the route is already in use
        """
        # Use agent's route if none provided
        if route is None:
            route = agent.route
            
        # Normalize route format
        if not route.startswith("/"):
            route = f"/{route}"
            
        route = route.rstrip("/")
        
        # Check for conflicts
        if route in self.agents:
            raise ValueError(f"Route '{route}' is already in use")
            
        # Store the agent
        self.agents[route] = agent
        
        # Get the router and register it
        router = agent.as_router()
        self.app.include_router(router, prefix=route)
        
        self.logger.info(f"Registered agent '{agent.get_name()}' at route '{route}'")
        
        # If SIP routing is enabled and auto-mapping is on, register SIP usernames for this agent
        if self._sip_routing_enabled:
            # Auto-map SIP usernames if enabled
            if getattr(self, '_sip_auto_map', False):
                self._auto_map_agent_sip_usernames(agent, route)
            
            # Register the SIP routing callback with this agent if we have one
            if hasattr(self, '_sip_routing_callback') and self._sip_routing_callback:
                agent.register_routing_callback(self._sip_routing_callback, path=self._sip_route)
            
    def setup_sip_routing(self, route: str = "/sip", auto_map: bool = True) -> None:
        """
        Set up central SIP-based routing for the server
        
        This configures all agents to handle SIP requests at the specified path,
        using a coordinated routing system where each agent checks if it can
        handle SIP requests for specific usernames.
        
        Args:
            route: The path for SIP routing (default: "/sip")
            auto_map: Whether to automatically map SIP usernames to agent routes
        """
        if self._sip_routing_enabled:
            self.logger.warning("SIP routing is already enabled")
            return
            
        # Normalize the route
        if not route.startswith("/"):
            route = f"/{route}"
            
        route = route.rstrip("/")
        
        # Store configuration
        self._sip_routing_enabled = True
        self._sip_route = route
        self._sip_auto_map = auto_map
        
        # If auto-mapping is enabled, map existing agents
        if auto_map:
            for agent_route, agent in self.agents.items():
                self._auto_map_agent_sip_usernames(agent, agent_route)
        
        # Create a unified routing callback that checks all registered usernames
        def server_sip_routing_callback(request: Request, body: Dict[str, Any]) -> Optional[str]:
            """Unified SIP routing callback that checks all registered usernames"""
            # Extract the SIP username
            sip_username = SWMLService.extract_sip_username(body)
            
            if sip_username:
                self.logger.info(f"Extracted SIP username: {sip_username}")
                
                # Look up the route for this username
                target_route = self._lookup_sip_route(sip_username)
                
                if target_route:
                    self.logger.info(f"Routing SIP request to {target_route}")
                    return target_route
                else:
                    self.logger.warning(f"No route found for SIP username: {sip_username}")
            
            # No routing needed (will be handled by the current agent)
            return None
        
        # Save the callback for later use with new agents
        self._sip_routing_callback = server_sip_routing_callback
        
        # Register this callback with each agent
        for agent in self.agents.values():
            # Each agent gets the same routing callback but at their own path
            agent.register_routing_callback(server_sip_routing_callback, path=route)
        
        self.logger.info(f"SIP routing enabled at {route} on all agents")
        
    def register_sip_username(self, username: str, route: str) -> None:
        """
        Register a mapping from SIP username to agent route
        
        Args:
            username: The SIP username
            route: The route to the agent
        """
        if not self._sip_routing_enabled:
            self.logger.warning("SIP routing is not enabled. Call setup_sip_routing() first.")
            return
            
        # Normalize the route
        if not route.startswith("/"):
            route = f"/{route}"
            
        route = route.rstrip("/")
        
        # Check if the route exists
        if route not in self.agents:
            self.logger.warning(f"Route {route} not found. SIP username will be registered but may not work.")
            
        # Add the mapping
        self._sip_username_mapping[username.lower()] = route
        self.logger.info(f"Registered SIP username '{username}' to route '{route}'")
        
    def _lookup_sip_route(self, username: str) -> Optional[str]:
        """
        Look up the route for a SIP username
        
        Args:
            username: The SIP username
            
        Returns:
            The route or None if not found
        """
        return self._sip_username_mapping.get(username.lower())
        
    def _auto_map_agent_sip_usernames(self, agent: AgentBase, route: str) -> None:
        """
        Automatically map SIP usernames for an agent
        
        This creates mappings based on the agent name and route.
        
        Args:
            agent: The agent to map
            route: The route to the agent
        """
        # Get the agent name and clean it for use as a SIP username
        agent_name = agent.get_name().lower()
        clean_name = re.sub(r'[^a-z0-9_]', '', agent_name)
        
        if clean_name:
            self.register_sip_username(clean_name, route)
            
        # Also use the route path (without slashes) as a username
        if route:
            # Extract just the last part of the route
            route_part = route.split("/")[-1]
            clean_route = re.sub(r'[^a-z0-9_]', '', route_part)
            
            if clean_route and clean_route != clean_name:
                self.register_sip_username(clean_route, route)
    
    def unregister(self, route: str) -> bool:
        """
        Unregister an agent from the server
        
        Args:
            route: The route of the agent to unregister
            
        Returns:
            True if the agent was unregistered, False if not found
        """
        # Normalize route format
        if not route.startswith("/"):
            route = f"/{route}"
            
        route = route.rstrip("/")
        
        # Check if the agent exists
        if route not in self.agents:
            return False
            
        # FastAPI doesn't support unregistering routes, so we'll just track it ourselves
        # and rebuild the app if needed
        del self.agents[route]
        
        self.logger.info(f"Unregistered agent at route '{route}'")
        return True
    
    def get_agents(self) -> List[Tuple[str, AgentBase]]:
        """
        Get all registered agents
        
        Returns:
            List of (route, agent) tuples
        """
        return [(route, agent) for route, agent in self.agents.items()]
    
    def get_agent(self, route: str) -> Optional[AgentBase]:
        """
        Get an agent by route
        
        Args:
            route: The route of the agent
            
        Returns:
            The agent or None if not found
        """
        # Normalize route format
        if not route.startswith("/"):
            route = f"/{route}"
            
        route = route.rstrip("/")
        
        return self.agents.get(route)
    
    def run(self, host: Optional[str] = None, port: Optional[int] = None) -> None:
        """
        Start the server
        
        Args:
            host: Optional host to override the default
            port: Optional port to override the default
        """
        if not self.agents:
            self.logger.warning("Starting server with no registered agents")
            
        # Add a health check endpoint
        @self.app.get("/health")
        def health_check():
            return {
                "status": "ok",
                "agents": len(self.agents),
                "routes": list(self.agents.keys())
            }
            
        # Print server info
        host = host or self.host
        port = port or self.port
        
        self.logger.info(f"Starting server on {host}:{port}")
        for route, agent in self.agents.items():
            username, password = agent.get_basic_auth_credentials()
            self.logger.info(f"Agent '{agent.get_name()}' available at:")
            self.logger.info(f"URL: http://{host}:{port}{route}")
            self.logger.info(f"Basic Auth: {username}:{password}")
            
        # Start the server
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level=self.log_level
        )

    def register_global_routing_callback(self, callback_fn: Callable[[Request, Dict[str, Any]], Optional[str]], 
                                        path: str) -> None:
        """
        Register a routing callback across all agents
        
        This allows you to add unified routing logic to all agents at the same path.
        
        Args:
            callback_fn: The callback function to register
            path: The path to register the callback at
        """
        # Normalize the path
        if not path.startswith("/"):
            path = f"/{path}"
        
        path = path.rstrip("/")
        
        # Register with all existing agents
        for agent in self.agents.values():
            agent.register_routing_callback(callback_fn, path=path)
        
        self.logger.info(f"Registered global routing callback at {path} on all agents")
