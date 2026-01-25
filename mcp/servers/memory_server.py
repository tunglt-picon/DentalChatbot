"""MCP Memory Server - exposes memory as Resources."""
import logging
from typing import Dict, Any, List, Optional
import uuid
from ..base import MCPServer
from services.memory import MemoryService

logger = logging.getLogger(__name__)


class MemoryMCPServer(MCPServer):
    """MCP Server for memory/conversation history (exposes as Resources)."""
    
    def __init__(self):
        """Initialize Memory MCP Server."""
        super().__init__("memory-server")
        self.memory_service = MemoryService()
    
    def _register_methods(self) -> None:
        """Register memory resource methods."""
        # Resource methods
        self.register_method("resources/list", self._list_resources_handler)
        self.register_method("resources/read", self._read_resource_handler)
        
        # Memory management methods
        self.register_method("memory/get_all_messages", self._get_all_messages)
        self.register_method("memory/set_summary", self._set_summary)
        self.register_method("memory/add_message", self._add_message)
        self.register_method("memory/get_or_create", self._get_or_create)
        self.register_method("memory/get_summary", self._get_summary)
        self.register_method("memory/clear", self._clear)
        self.register_method("memory/delete", self._delete)
    
    def _list_tools(self) -> list:
        """No tools, only resources."""
        return []
    
    def _list_resources(self) -> list:
        """List memory resources (conversations)."""
        return [
            {
                "uri": f"memory://conversation/{conv_id}",
                "name": f"Conversation {conv_id[:8]}",
                "description": f"Conversation history for {conv_id}",
                "mimeType": "application/json"
            }
            for conv_id in self.memory_service.conversations.keys()
        ]
    
    def _list_prompts(self) -> list:
        """No prompts."""
        return []
    
    async def _list_resources_handler(self) -> Dict[str, Any]:
        """Handle resources/list request."""
        resources = self._list_resources()
        return {"resources": resources}
    
    async def _read_resource_handler(self, uri: str) -> Dict[str, Any]:
        """
        Handle resources/read request.
        
        Args:
            uri: Resource URI (e.g., "memory://conversation/{id}")
        """
        # Parse conversation ID from URI
        if not uri.startswith("memory://conversation/"):
            raise ValueError(f"Invalid resource URI: {uri}")
        
        conversation_id = uri.replace("memory://conversation/", "")
        context = self.memory_service.get_conversation_context(conversation_id)
        summary = self.memory_service.get_conversation_summary(conversation_id)
        
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": str({"messages": context, "summary": summary})
                }
            ]
        }
    
    async def _get_all_messages(self, conversation_id: str) -> Dict[str, Any]:
        """Get ALL messages in conversation (full history for display)."""
        all_messages = self.memory_service.get_all_messages(conversation_id)
        return {"messages": all_messages}
    
    async def _set_summary(
        self,
        conversation_id: str,
        summary: str,
        compress: bool = False
    ) -> Dict[str, Any]:
        """
        Set summary for conversation.
        
        This is a single summary variable that accumulates all previous responses.
        It is updated after each response to include the new response summary.
        
        Args:
            conversation_id: Conversation ID
            summary: Summary text (accumulated summary of all previous responses)
            compress: Not used anymore, kept for compatibility (default: False)
        """
        self.memory_service.set_conversation_summary(conversation_id, summary, compress=compress)
        return {"status": "success", "conversation_id": conversation_id}
    
    async def _add_message(self, conversation_id: str, role: str, content: str) -> Dict[str, Any]:
        """Add message to conversation."""
        self.memory_service.add_message(conversation_id, role, content)
        return {"status": "success", "conversation_id": conversation_id}
    
    async def _get_or_create(self, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Get or create conversation."""
        conv_id = self.memory_service.get_or_create_conversation(conversation_id)
        return {"conversation_id": conv_id}
    
    async def _get_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation summary text (if exists)."""
        summary_text = self.memory_service.get_conversation_summary_text(conversation_id)
        return {"summary": summary_text or ""}
    
    async def _clear(self, conversation_id: str) -> Dict[str, Any]:
        """Clear conversation."""
        self.memory_service.clear_conversation(conversation_id)
        return {"status": "cleared", "conversation_id": conversation_id}
    
    async def _delete(self, conversation_id: str) -> Dict[str, Any]:
        """Delete conversation."""
        self.memory_service.delete_conversation(conversation_id)
        return {"status": "deleted", "conversation_id": conversation_id}
