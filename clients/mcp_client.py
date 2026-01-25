"""MCP Client for main application - communicates with MCP server via HTTP only."""
import logging
from typing import Any, Dict, Optional, Union
import httpx

logger = logging.getLogger(__name__)


class MCPClient:
    """
    MCP client for communicating with MCP servers via HTTP.
    
    This client is independent from MCP server code - it only uses HTTP/JSON-RPC.
    Main application should use this client instead of importing from mcp/ folder.
    """
    
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
        Call a method on the server via HTTP (JSON-RPC 2.0).
        
        Args:
            method: Method name (e.g., "memory/get_context")
            params: Method parameters
            request_id: Optional request ID
            
        Returns:
            Method result
            
        Raises:
            Exception: If the method call fails
        """
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
                    error_msg = error_data.get("message", "Unknown error")
                    error_code = error_data.get("code", -1)
                    logger.error(f"MCP JSON-RPC error: {error_code} - {error_msg}")
                    raise Exception(f"MCP error [{error_code}]: {error_msg}")
                
                # Return result
                if "result" in result:
                    return result["result"]
                else:
                    logger.warning(f"No result in MCP response: {result}")
                    return None
                    
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling MCP server: {e}")
            raise Exception(f"Failed to connect to MCP server at {self.base_url}: {str(e)}")
        except Exception as e:
            logger.error(f"Error calling MCP method {full_method}: {e}", exc_info=True)
            raise


class MCPHost:
    """
    MCP Host - manages multiple MCP clients.
    
    This class is independent from MCP server code - it only uses HTTP clients.
    Main application should use this instead of importing from mcp/ folder.
    """
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        """
        Initialize MCP Host.
        
        Args:
            base_url: Base URL of the MCP HTTP server
        """
        self.base_url = base_url
        self._clients: Dict[str, MCPClient] = {}
        logger.info(f"MCP Host initialized - connecting to {base_url}")
    
    def get_client(self, server_name: str) -> MCPClient:
        """
        Get or create MCP client for a server.
        
        Args:
            server_name: Name of the server (e.g., "memory-server", "tool-server")
            
        Returns:
            MCPClient instance
        """
        if server_name not in self._clients:
            self._clients[server_name] = MCPClient(server_name, self.base_url)
            logger.debug(f"Created MCP client for {server_name}")
        
        return self._clients[server_name]
    
    @property
    def memory_client(self) -> MCPClient:
        """Get memory server client."""
        return self.get_client("memory-server")
    
    @property
    def tool_client(self) -> MCPClient:
        """Get tool server client."""
        return self.get_client("tool-server")
