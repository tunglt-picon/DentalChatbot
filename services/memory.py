"""Memory service for managing conversation history."""
import logging
from typing import List, Dict, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

# Note: Old compression logic removed. Now using single summary variable that accumulates all responses.


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
        self.summary: Optional[str] = None  # Single summary variable that accumulates all previous responses
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
    
    def get_summary(self) -> Optional[str]:
        """
        Get conversation summary (if exists).
        
        Returns:
            Summary text or None
        """
        return self.summary
    
    def get_all_messages(self) -> List[Dict]:
        """
        Get ALL messages in conversation (full history for display).
        This includes both old and recent messages, even after compression.
        
        Returns:
            List of all messages (full history)
        """
        return self.messages.copy()
    
    def get_user_messages(self) -> List[str]:
        """Get all user messages from conversation."""
        return [msg["content"] for msg in self.messages if msg["role"] == "user"]
    
    def clear(self) -> None:
        """Clear all messages from conversation."""
        self.messages = []
        self.summary = None
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
    
    def get_conversation_summary_text(self, conversation_id: str) -> Optional[str]:
        """
        Get conversation summary text (if exists).
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Summary text or None
        """
        if conversation_id not in self.conversations:
            return None
        
        return self.conversations[conversation_id].get_summary()
    
    def set_conversation_summary(
        self,
        conversation_id: str,
        summary: str,
        compress: bool = False
    ) -> None:
        """
        Set summary for conversation.
        
        IMPORTANT: This is a single summary variable that accumulates all previous responses.
        It is updated after each response to include the new response summary.
        Full history is ALWAYS preserved for display purposes.
        
        Args:
            conversation_id: Conversation ID
            summary: Summary text (accumulated summary of all previous responses)
            compress: Not used anymore, kept for compatibility (default: False)
        """
        if conversation_id not in self.conversations:
            return
        
        conv = self.conversations[conversation_id]
        
        # Always set summary, regardless of message count
        # This is a single summary variable that accumulates all responses
        conv.summary = summary
        logger.info(f"Set summary for conversation {conversation_id}. Summary length: {len(summary)} characters. Total messages: {len(conv.messages)}")
    
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
    
    def get_all_messages(self, conversation_id: str) -> List[Dict]:
        """
        Get ALL messages in conversation (full history for display).
        This includes both old and recent messages, even after compression.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            List of all messages (full history)
        """
        if conversation_id not in self.conversations:
            return []
        
        conv = self.conversations[conversation_id]
        return conv.get_all_messages()
    
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
