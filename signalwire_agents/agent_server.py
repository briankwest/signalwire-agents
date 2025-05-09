"""
AgentServer - Class for hosting multiple SignalWire AI Agents in a single server
"""

import logging
from typing import Dict, Any, Optional, List, Tuple

try:
    from fastapi import FastAPI
    import uvicorn
except ImportError:
    raise ImportError(
        "fastapi and uvicorn are required. Install them with: pip install fastapi uvicorn"
    )

from signalwire_agents.core.agent_base import AgentBase


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
            version="0.1.0"
        )
        
        # Keep track of registered agents
        self.agents: Dict[str, AgentBase] = {}
    
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
