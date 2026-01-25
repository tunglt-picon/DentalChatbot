"""Memory service for managing conversation history."""
import logging
from typing import List, Dict, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

# Configuration for memory compression
KEEP_RECENT_MESSAGES = 6  # Number of recent messages to keep in full (3 user + 3 assistant)
SUMMARIZE_THRESHOLD = 10  # Start summarizing when conversation has more than this many messages
COMPRESS_AFTER_SUMMARY = True  # Delete old messages after summarizing to reduce storage


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
        self.summary: Optional[str] = None  # Summary of old messages to reduce context size
        self.summarized_count: int = 0  # Number of messages that have been summarized
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
    
    def get_context(self, max_messages: Optional[int] = None, keep_recent: int = KEEP_RECENT_MESSAGES) -> List[Dict]:
        """
        Get conversation context (messages) with smart compression.
        
        Strategy:
        - If conversation <= keep_recent: return all messages
        - If conversation > keep_recent: return recent messages only (old messages are not included)
        - Summary is handled separately in chat_service when building prompt
        
        Args:
            max_messages: Maximum number of messages to return (None = all, but still applies compression)
            keep_recent: Number of recent messages to keep in full (default: 6 = 3 user + 3 assistant)
            
        Returns:
            List of messages for context (only recent messages, old ones are excluded to reduce size)
        """
        total_messages = len(self.messages)
        
        # If conversation is short, return all messages
        if total_messages <= keep_recent:
            if max_messages is None:
                return self.messages.copy()
            return self.messages[-max_messages:] if total_messages > max_messages else self.messages.copy()
        
        # For long conversations: only return recent messages (old ones excluded to reduce context size)
        recent_messages = self.messages[-keep_recent:]
        
        # Apply max_messages limit if specified
        if max_messages is not None and len(recent_messages) > max_messages:
            return recent_messages[-max_messages:]
        
        return recent_messages
    
    def get_old_messages_for_summary(self, keep_recent: int = KEEP_RECENT_MESSAGES) -> List[Dict]:
        """
        Get old messages that should be summarized (excludes recent messages).
        
        Args:
            keep_recent: Number of recent messages to exclude from summary
            
        Returns:
            List of old messages to summarize
        """
        total_messages = len(self.messages)
        if total_messages <= keep_recent:
            return []
        
        return self.messages[:-keep_recent]
    
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
        self.summarized_count = 0
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
        self.max_context_messages = 20  # Maximum messages to keep in context (legacy, now uses KEEP_RECENT_MESSAGES)
    
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
        Get conversation context (only recent messages to reduce size).
        Old messages are summarized and stored separately.
        
        Args:
            conversation_id: Conversation ID
            max_messages: Maximum messages to return (uses default if None)
            
        Returns:
            List of messages for context (only recent messages, old ones are summarized)
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
    
    def get_old_messages(
        self,
        conversation_id: str
    ) -> tuple[List[Dict], int]:
        """
        Get old messages that should be summarized (excludes recent messages).
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Tuple of (old_messages, total_count)
        """
        if conversation_id not in self.conversations:
            return [], 0
        
        conv = self.conversations[conversation_id]
        old_messages = conv.get_old_messages_for_summary()
        total_count = len(conv.messages)
        
        # Convert to OpenAI format
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in old_messages
        ], total_count
    
    def set_conversation_summary(
        self,
        conversation_id: str,
        summary: str,
        compress: bool = COMPRESS_AFTER_SUMMARY
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
