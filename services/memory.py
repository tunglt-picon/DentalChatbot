"""Memory service for managing conversation history."""
import logging
from typing import List, Dict, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Manages conversation history for a single conversation."""
    
    def __init__(self, conversation_id: str):
        """
        Initialize conversation memory.
        
        Args:
            conversation_id: Unique identifier for the conversation
        """
        self.conversation_id = conversation_id
        self.messages: List[Dict] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to conversation history.
        
        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def get_context(self, max_messages: Optional[int] = None) -> List[Dict]:
        """
        Get conversation context (messages).
        
        Args:
            max_messages: Maximum number of messages to return (None = all)
            
        Returns:
            List of messages for context
        """
        if max_messages is None:
            return self.messages.copy()
        
        # Return last N messages
        return self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages.copy()
    
    def get_user_messages(self) -> List[str]:
        """Get all user messages from conversation."""
        return [msg["content"] for msg in self.messages if msg["role"] == "user"]
    
    def clear(self) -> None:
        """Clear all messages from conversation."""
        self.messages = []
        self.updated_at = datetime.now()


class MemoryService:
    """
    Service for managing multiple conversation memories.
    
    Note: This is a standard memory service, NOT an MCP (Model Context Protocol) server.
    MCP requires Host-Client-Server architecture with JSON-RPC 2.0 protocol,
    which is not implemented in this service.
    """
    
    def __init__(self):
        """Initialize Memory Service."""
        self.conversations: Dict[str, ConversationMemory] = {}
        self.max_context_messages = 20  # Maximum messages to keep in context
    
    def get_or_create_conversation(self, conversation_id: Optional[str] = None) -> str:
        """
        Get existing conversation or create new one.
        
        Args:
            conversation_id: Optional conversation ID. If None, creates new.
            
        Returns:
            Conversation ID
        """
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())
        
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = ConversationMemory(conversation_id)
            logger.info(f"Created new conversation: {conversation_id}")
        
        return conversation_id
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str
    ) -> None:
        """
        Add message to conversation.
        
        Args:
            conversation_id: Conversation ID
            role: Message role
            content: Message content
        """
        if conversation_id not in self.conversations:
            self.get_or_create_conversation(conversation_id)
        
        self.conversations[conversation_id].add_message(role, content)
        logger.debug(f"Added {role} message to conversation {conversation_id}")
    
    def get_conversation_context(
        self,
        conversation_id: str,
        max_messages: Optional[int] = None
    ) -> List[Dict]:
        """
        Get conversation context.
        
        Args:
            conversation_id: Conversation ID
            max_messages: Maximum messages to return (uses default if None)
            
        Returns:
            List of messages for context
        """
        if conversation_id not in self.conversations:
            return []
        
        max_msgs = max_messages or self.max_context_messages
        context = self.conversations[conversation_id].get_context(max_msgs)
        
        # Convert to OpenAI format (remove timestamp for API compatibility)
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in context
        ]
    
    def clear_conversation(self, conversation_id: str) -> None:
        """
        Clear a conversation's history.
        
        Args:
            conversation_id: Conversation ID
        """
        if conversation_id in self.conversations:
            self.conversations[conversation_id].clear()
            logger.info(f"Cleared conversation {conversation_id}")
    
    def delete_conversation(self, conversation_id: str) -> None:
        """
        Delete a conversation.
        
        Args:
            conversation_id: Conversation ID
        """
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            logger.info(f"Deleted conversation {conversation_id}")
    
    def get_conversation_summary(self, conversation_id: str) -> Dict:
        """
        Get conversation summary/metadata.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Conversation metadata
        """
        if conversation_id not in self.conversations:
            return {}
        
        conv = self.conversations[conversation_id]
        return {
            "conversation_id": conv.conversation_id,
            "message_count": len(conv.messages),
            "created_at": conv.created_at.isoformat(),
            "updated_at": conv.updated_at.isoformat()
        }
