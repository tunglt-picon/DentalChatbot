"""Base classes for MCP (Model Context Protocol) implementation."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, Union
import logging
from .protocol import JSONRPCRequest, JSONRPCResponse, JSONRPCError, JSONRPCErrorCode

logger = logging.getLogger(__name__)


class MCPServer(ABC):
    """Base class for MCP servers."""
    
    def __init__(self, server_name: str):
        """
        Initialize MCP server.
        
        Args:
            server_name: Name of the server
        """
        self.server_name = server_name
        self.methods: Dict[str, Callable] = {}
        self._register_methods()
    
    @abstractmethod
    def _register_methods(self) -> None:
        """Register server methods (tools, resources, prompts)."""
        pass
    
    def register_method(self, method_name: str, handler: Callable) -> None:
        """Register a method handler."""
        self.methods[method_name] = handler
        logger.debug(f"Registered method {method_name} on server {self.server_name}")
    
    async def handle_request(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """
        Handle JSON-RPC request.
        
        Args:
            request: JSON-RPC request
            
        Returns:
            JSON-RPC response
        """
        method_name = request.method
        
        if method_name not in self.methods:
            return JSONRPCResponse.error(
                JSONRPCError(
                    JSONRPCErrorCode.METHOD_NOT_FOUND.value,
                    f"Method '{method_name}' not found on server '{self.server_name}'"
                ),
                request_id=request.id
            )
        
        try:
            handler = self.methods[method_name]
            # Handle both sync and async handlers
            if hasattr(handler, '__call__'):
                if hasattr(handler, '__await__'):
                    result = await handler(**request.params) if isinstance(request.params, dict) else await handler(*request.params)
                else:
                    result = handler(**request.params) if isinstance(request.params, dict) else handler(*request.params)
            else:
                raise JSONRPCError(
                    JSONRPCErrorCode.INTERNAL_ERROR.value,
                    f"Handler for method '{method_name}' is not callable"
                )
            
            return JSONRPCResponse.success(result, request_id=request.id)
            
        except JSONRPCError as e:
            return JSONRPCResponse.error(e, request_id=request.id)
        except Exception as e:
            logger.error(f"Error handling method {method_name}: {e}", exc_info=True)
            return JSONRPCResponse.error(
                JSONRPCError(
                    JSONRPCErrorCode.INTERNAL_ERROR.value,
                    f"Internal server error: {str(e)}"
                ),
                request_id=request.id
            )
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get server capabilities (tools, resources, prompts)."""
        return {
            "tools": self._list_tools(),
            "resources": self._list_resources(),
            "prompts": self._list_prompts()
        }
    
    @abstractmethod
    def _list_tools(self) -> list:
        """List available tools."""
        pass
    
    @abstractmethod
    def _list_resources(self) -> list:
        """List available resources."""
        pass
    
    @abstractmethod
    def _list_prompts(self) -> list:
        """List available prompts."""
        pass


class MCPClient:
    """MCP client for communicating with MCP servers."""
    
    def __init__(self, server: MCPServer):
        """
        Initialize MCP client.
        
        Args:
            server: MCP server instance to communicate with
        """
        self.server = server
        self.server_name = server.server_name
    
    async def call_method(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        request_id: Optional[Union[str, int]] = None
    ) -> Any:
        """
        Call a method on the server.
        
        Args:
            method: Method name
            params: Method parameters
            request_id: Optional request ID
            
        Returns:
            Method result
            
        Raises:
            JSONRPCError: If the method call fails
        """
        request = JSONRPCRequest(method=method, params=params or {}, request_id=request_id)
        response = await self.server.handle_request(request)
        
        if response.error:
            raise response.error
        
        return response.result
    
    async def list_tools(self) -> list:
        """List available tools on the server."""
        capabilities = self.server.get_capabilities()
        return capabilities.get("tools", [])
    
    async def list_resources(self) -> list:
        """List available resources on the server."""
        capabilities = self.server.get_capabilities()
        return capabilities.get("resources", [])
    
    async def list_prompts(self) -> list:
        """List available prompts on the server."""
        capabilities = self.server.get_capabilities()
        return capabilities.get("prompts", [])


class MCPHost:
    """MCP Host orchestrates clients and manages context."""
    
    def __init__(self):
        """Initialize MCP Host."""
        self.clients: Dict[str, MCPClient] = {}
        self.conversation_history: Dict[str, list] = {}
    
    def register_server(self, server: MCPServer) -> MCPClient:
        """
        Register an MCP server and create a client.
        
        Args:
            server: MCP server to register
            
        Returns:
            MCP client for the server
        """
        client = MCPClient(server)
        self.clients[server.server_name] = client
        logger.info(f"Registered MCP server: {server.server_name}")
        return client
    
    def get_client(self, server_name: str) -> Optional[MCPClient]:
        """Get client for a server."""
        return self.clients.get(server_name)
    
    def store_conversation_context(self, conversation_id: str, messages: list) -> None:
        """Store conversation context in host (not in servers)."""
        self.conversation_history[conversation_id] = messages
    
    def get_conversation_context(self, conversation_id: str) -> list:
        """Get conversation context from host."""
        return self.conversation_history.get(conversation_id, [])
