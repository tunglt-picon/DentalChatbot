"""MCP Tool Server - exposes search tools as Tools."""
import logging
from typing import Dict, Any, List
from ..base import MCPServer
from tools.factory import SearchToolFactory

logger = logging.getLogger(__name__)


class ToolMCPServer(MCPServer):
    """MCP Server for search tools (exposes as Tools)."""
    
    def __init__(self):
        """Initialize Tool MCP Server."""
        super().__init__("tool-server")
    
    def _register_methods(self) -> None:
        """Register tool methods."""
        # Tool methods
        self.register_method("tools/list", self._list_tools_handler)
        self.register_method("tools/call", self._call_tool_handler)
    
    def _list_tools(self) -> list:
        """List available search tools."""
        return [
            {
                "name": "google_search",
                "description": "Search using Google Custom Search API (high accuracy, limited quota)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "duckduckgo_search",
                "description": "Search using DuckDuckGo (free, unlimited)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
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
        """No prompts."""
        return []
    
    async def _list_tools_handler(self) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = self._list_tools()
        return {"tools": tools}
    
    async def _call_tool_handler(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle tools/call request.
        
        Args:
            name: Tool name (google_search or duckduckgo_search)
            arguments: Tool arguments
        """
        query = arguments.get("query")
        if not query:
            raise ValueError("Query is required")
        
        # Map tool name to model
        model_mapping = {
            "google_search": "dental-google",
            "duckduckgo_search": "dental-duckduckgo"
        }
        
        if name not in model_mapping:
            raise ValueError(f"Unknown tool: {name}")
        
        model = model_mapping[name]
        
        try:
            # Get search tool via factory
            search_tool = SearchToolFactory.create_search_tool(model)
            results = await search_tool.search(query)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": results
                    }
                ]
            }
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            raise ValueError(f"Tool execution failed: {str(e)}")
