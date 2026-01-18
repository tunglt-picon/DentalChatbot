"""Service for handling chat completions."""
import google.generativeai as genai
import logging
from typing import Optional
from tools.factory import SearchToolFactory
from services.guardrail import GuardrailService
from services.memory import MemoryService
import config

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=config.settings.google_api_key)


class ChatService:
    """Service for handling chat completion logic with MCP (Memory Context Protocol)."""
    
    def __init__(self, memory_service: Optional[MemoryService] = None):
        """
        Initialize ChatService.
        
        Args:
            memory_service: Memory service instance (creates new if None)
        """
        self.model = genai.GenerativeModel(config.settings.google_base_model)
        self.guardrail = GuardrailService()
        self.memory_service = memory_service or MemoryService()
    
    async def process_chat(
        self,
        messages: list,
        model: str,
        conversation_id: Optional[str] = None
    ) -> tuple[str, str]:
        """
        Process chat completion with workflow: Memory Context -> Guardrail -> Search -> Summarize.
        
        Args:
            messages: List of messages in OpenAI format
            model: Selected model name
            conversation_id: Optional conversation ID for memory context (MCP)
            
        Returns:
            Tuple of (response_text, conversation_id)
            
        Raises:
            ValueError: If question is not related to dentistry
            Exception: If there's an error during processing
        """
        # MCP: Get or create conversation and merge with memory context
        conv_id = self.memory_service.get_or_create_conversation(conversation_id)
        
        # Get conversation context from memory
        memory_context = self.memory_service.get_conversation_context(conv_id)
        
        # Merge incoming messages with memory context
        # Avoid duplicates by comparing last few messages
        all_messages = memory_context.copy()
        
        # Get last user message from incoming messages
        user_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                # Check if this message is already in memory
                if not all_messages or all_messages[-1].get("content") != user_message:
                    all_messages.append(msg)
                break
        
        if not user_message:
            raise ValueError("User message not found")
        
        # Step 1: Guardrail
        is_dental = await self.guardrail.is_dental_related(user_message)
        if not is_dental:
            raise ValueError(
                "Sorry, I can only answer questions related to the dental field. "
                "Please ask about teeth, gums, dental treatments, or other oral health issues."
            )
        
        # Step 2: Select Tool and perform Search
        try:
            search_tool = SearchToolFactory.create_search_tool(model)
            search_results = await search_tool.search(user_message)
        except Exception as e:
            logger.error(f"Error during search: {e}")
            # If Google Search fails and hasn't fallback, try DuckDuckGo
            if model == "dental-google":
                logger.info("Attempting fallback to DuckDuckGo...")
                search_tool = SearchToolFactory.create_search_tool("dental-duckduckgo")
                search_results = await search_tool.search(user_message)
            else:
                raise
        
        # Step 3: Build prompt with conversation context (MCP)
        conversation_summary = ""
        if len(all_messages) > 1:
            # Include relevant previous conversation context
            prev_messages = [msg for msg in all_messages[:-1] if msg.get("role") in ["user", "assistant"]]
            if prev_messages:
                conversation_summary = "\n\nPrevious conversation context:\n"
                for msg in prev_messages[-5:]:  # Last 5 messages for context
                    role = "Patient" if msg.get("role") == "user" else "Dentist"
                    conversation_summary += f"{role}: {msg.get('content', '')}\n"
        
        prompt = f"""You are a professional dental consultant with extensive knowledge. 
Your task is to answer the patient's question based on the search information and conversation context.

{conversation_summary}

Current patient's question: {user_message}

Search information:
{search_results}

Please answer the question in a way that is:
- Accurate and based on search information
- Consistent with previous conversation context (if any)
- Easy to understand and friendly
- Mentions reference sources if available
- Note: If information is incomplete, suggest the patient consult a dentist

Answer:"""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # MCP: Save messages to memory
            self.memory_service.add_message(conv_id, "user", user_message)
            self.memory_service.add_message(conv_id, "assistant", response_text)
            
            return response_text, conv_id
        except Exception as e:
            logger.error(f"Error generating response from LLM: {e}")
            raise Exception(f"Error generating response: {str(e)}")
