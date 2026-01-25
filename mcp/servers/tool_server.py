"""MCP Tool Server - exposes search tools as Tools."""
import logging
from typing import Dict, Any, List
from ..base import MCPServer
from .tools.duckduckgo_search import DuckDuckGoSearchTool

logger = logging.getLogger(__name__)


class ToolMCPServer(MCPServer):
    """MCP Server for search tools (exposes as Tools)."""
    
    def __init__(self):
        """Initialize Tool MCP Server."""
        super().__init__("tool-server")
        # Initialize tools (standalone, no dependency on main app)
        self.duckduckgo_tool = DuckDuckGoSearchTool()
    
    def _register_methods(self) -> None:
        """Register tool methods."""
        # Tool methods only - tool selection is code-driven, not LLM-driven
        self.register_method("tools/list", self._list_tools_handler)
        self.register_method("tools/call", self._call_tool_handler)
    
    def _list_tools(self) -> list:
        """List available search tools."""
        return [
            {
                "name": "duckduckgo_search",
                "description": "Search using DuckDuckGo (free, unlimited, privacy-focused). Returns up to 5 relevant search results with titles, content snippets, and links.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query - should be specific and descriptive for best results"
                        }
                    },
                    "required": ["query"]
                }
            }
        ]
    
    def _list_resources(self) -> list:
        """No resources, only tools."""
        return []
    
    def _list_prompts(self) -> list:
        """No prompts - tool selection is code-driven."""
        return []
    
    async def _list_tools_handler(self) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = self._list_tools()
        return {"tools": tools}
    
    async def _call_tool_handler(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle tools/call request.
        
        Args:
            name: Tool name (duckduckgo_search)
            arguments: Tool arguments
        """
        query = arguments.get("query")
        if not query:
            raise ValueError("Query is required")
        
        if name != "duckduckgo_search":
            raise ValueError(f"Unknown tool: {name}. Only 'duckduckgo_search' is supported.")
        
        try:
            # Use tool from MCP server (standalone, no dependency on main app)
            results = await self.duckduckgo_tool.search(query)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": results
                    }
                ]
            }
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}", exc_info=True)
            raise ValueError(f"Tool execution failed: {str(e)}")
