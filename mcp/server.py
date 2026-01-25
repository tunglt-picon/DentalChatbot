"""MCP HTTP Server - Standalone server for MCP protocol."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, Optional, Union
import logging
import sys
import os

# Add parent directory to path for imports when running directly
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from .protocol import JSONRPCRequest, JSONRPCResponse, JSONRPCError, JSONRPCErrorCode
    from .servers import MemoryMCPServer, ToolMCPServer
except ImportError:
    # Fallback for direct execution
    from mcp.protocol import JSONRPCRequest, JSONRPCResponse, JSONRPCError, JSONRPCErrorCode
    from mcp.servers import MemoryMCPServer, ToolMCPServer

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="MCP Server",
    description="Model Context Protocol Server - Memory and Tool services",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize MCP servers
memory_server = MemoryMCPServer()
tool_server = ToolMCPServer()

# Server registry
servers = {
    "memory-server": memory_server,
    "tool-server": tool_server
}


class JSONRPCRequestModel(BaseModel):
    """JSON-RPC request model."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None


@app.post("/jsonrpc")
async def handle_jsonrpc(request: JSONRPCRequestModel):
    """
    Handle JSON-RPC requests.
    
    Method format: {server_name}/{method}
    Example: memory-server/memory/get_context
    """
    try:
        # Parse method to get server name and method
        # Format: {server_name}/{method}
        method_parts = request.method.split("/", 1)
        if len(method_parts) != 2:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid method format. Expected: {{server_name}}/{{method}}, got: {request.method}"
            )
        
        server_name, method = method_parts
        
        # Get server
        server = servers.get(server_name)
        if not server:
            error_response = JSONRPCResponse.error(
                JSONRPCError(
                    JSONRPCErrorCode.METHOD_NOT_FOUND.value,
                    f"Server '{server_name}' not found. Available servers: {list(servers.keys())}"
                ),
                request_id=request.id
            )
            return error_response.to_dict()
        
        # Create JSON-RPC request
        jsonrpc_request = JSONRPCRequest(
            method=method,
            params=request.params or {},
            request_id=request.id
        )
        
        # Handle request
        response = await server.handle_request(jsonrpc_request)
        
        return response.to_dict()
        
    except Exception as e:
        logger.error(f"Error handling JSON-RPC request: {e}", exc_info=True)
        error_response = JSONRPCResponse.error(
            JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR.value,
                f"Internal server error: {str(e)}"
            ),
            request_id=request.id if hasattr(request, 'id') else None
        )
        return error_response.to_dict()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "servers": list(servers.keys())}


@app.get("/servers")
async def list_servers():
    """List available MCP servers."""
    return {
        "servers": [
            {
                "name": name,
                "capabilities": server.get_capabilities()
            }
            for name, server in servers.items()
        ]
    }


@app.get("/servers/{server_name}/capabilities")
async def get_server_capabilities(server_name: str):
    """Get capabilities of a specific server."""
    server = servers.get(server_name)
    if not server:
        raise HTTPException(status_code=404, detail=f"Server '{server_name}' not found")
    
    return {
        "server_name": server_name,
        "capabilities": server.get_capabilities()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
