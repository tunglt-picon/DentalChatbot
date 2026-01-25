"""Base classes for MCP (Model Context Protocol) implementation."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, Union
import logging
import inspect
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
            if not callable(handler):
                raise JSONRPCError(
                    JSONRPCErrorCode.INTERNAL_ERROR.value,
                    f"Handler for method '{method_name}' is not callable"
                )
            
            # Call handler and check if result is coroutine
            if isinstance(request.params, dict):
                result = handler(**request.params)
            else:
                result = handler(*request.params) if request.params else handler()
            
            # If result is a coroutine, await it
            if inspect.iscoroutine(result):
                result = await result
            
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
    """MCP client for communicating with MCP servers via HTTP."""
    
    def __init__(self, server_name: str, base_url: str = "http://localhost:8001"):
        """
        Initialize MCP client.
        
        Args:
            server_name: Name of the server (e.g., "memory-server", "tool-server")
            base_url: Base URL of the MCP HTTP server
        """
        self.server_name = server_name
        self.base_url = base_url.rstrip("/")
    
    async def call_method(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        request_id: Optional[Union[str, int]] = None
    ) -> Any:
        """
        Call a method on the server via HTTP.
        
        Args:
            method: Method name (e.g., "memory/get_context")
            params: Method parameters
            request_id: Optional request ID
            
        Returns:
            Method result
            
        Raises:
            JSONRPCError: If the method call fails
        """
        import httpx
        
        # Full method path: {server_name}/{method}
        full_method = f"{self.server_name}/{method}"
        
        # Create JSON-RPC request
        request_data = {
            "jsonrpc": "2.0",
            "method": full_method,
            "params": params or {},
        }
        if request_id is not None:
            request_data["id"] = request_id
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/jsonrpc",
                    json=request_data
                )
                response.raise_for_status()
                result = response.json()
                
                # Check for JSON-RPC error
                if "error" in result:
                    error_data = result["error"]
                    raise JSONRPCError(
                        error_data.get("code", JSONRPCErrorCode.INTERNAL_ERROR.value),
                        error_data.get("message", "Unknown error"),
                        error_data.get("data")
                    )
                
                return result.get("result")
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling MCP server: {e}")
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR.value,
                f"Failed to connect to MCP server at {self.base_url}: {str(e)}"
            )
        except JSONRPCError:
            raise
        except Exception as e:
            logger.error(f"Error calling MCP method {full_method}: {e}", exc_info=True)
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR.value,
                f"Error calling MCP method: {str(e)}"
            )
    
    async def list_tools(self) -> list:
        """List available tools on the server."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/servers/{self.server_name}/capabilities")
                response.raise_for_status()
                data = response.json()
                return data.get("capabilities", {}).get("tools", [])
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return []
    
    async def list_resources(self) -> list:
        """List available resources on the server."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/servers/{self.server_name}/capabilities")
                response.raise_for_status()
                data = response.json()
                return data.get("capabilities", {}).get("resources", [])
        except Exception as e:
            logger.error(f"Error listing resources: {e}")
            return []
    
    async def list_prompts(self) -> list:
        """List available prompts on the server."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/servers/{self.server_name}/capabilities")
                response.raise_for_status()
                data = response.json()
                return data.get("capabilities", {}).get("prompts", [])
        except Exception as e:
            logger.error(f"Error listing prompts: {e}")
            return []


class MCPHost:
    """MCP Host orchestrates clients and manages context."""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        """
        Initialize MCP Host.
        
        Args:
            base_url: Base URL of the MCP HTTP server
        """
        self.base_url = base_url
        self.clients: Dict[str, MCPClient] = {}
        self.conversation_history: Dict[str, list] = {}
    
    def get_client(self, server_name: str) -> MCPClient:
        """
        Get or create client for a server.
        
        Args:
            server_name: Name of the server (e.g., "memory-server", "tool-server")
            
        Returns:
            MCP client for the server
        """
        if server_name not in self.clients:
            client = MCPClient(server_name, base_url=self.base_url)
            self.clients[server_name] = client
            logger.info(f"Created MCP client for server: {server_name} at {self.base_url}")
        return self.clients[server_name]
    
    def store_conversation_context(self, conversation_id: str, messages: list) -> None:
        """Store conversation context in host (not in servers)."""
        self.conversation_history[conversation_id] = messages
    
    def get_conversation_context(self, conversation_id: str) -> list:
        """Get conversation context from host."""
        return self.conversation_history.get(conversation_id, [])
