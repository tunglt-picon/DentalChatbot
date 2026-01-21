"""Chat Service with MCP (Model Context Protocol) implementation."""
import logging
import asyncio
import re
from typing import Optional, Tuple
from mcp.base import MCPHost
from mcp.servers import MemoryMCPServer, ToolMCPServer
from services.guardrail import GuardrailService
from services.llm_provider import create_llm_provider
import config

logger = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    """
    Detect language from text (Vietnamese or English).
    
    Args:
        text: Input text
        
    Returns:
        "vi" for Vietnamese, "en" for English
    """
    # Vietnamese characters (with diacritics)
    vietnamese_pattern = re.compile(
        r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]',
        re.IGNORECASE
    )
    
    # Common Vietnamese words
    vietnamese_words = [
        'là', 'và', 'của', 'cho', 'với', 'từ', 'được', 'trong', 'này', 'đó',
        'có', 'không', 'một', 'như', 'về', 'nếu', 'khi', 'sẽ', 'đã', 'đang',
        'tôi', 'bạn', 'chúng', 'họ', 'nó', 'các', 'những', 'nhiều', 'ít',
        'răng', 'nướu', 'miệng', 'nha khoa', 'điều trị', 'bệnh', 'sức khỏe'
    ]
    
    # Check for Vietnamese characters
    if vietnamese_pattern.search(text):
        logger.debug(f"[LANG] Detected Vietnamese (diacritics found)")
        return "vi"
    
    # Check for Vietnamese words (case insensitive)
    text_lower = text.lower()
    vietnamese_word_count = sum(1 for word in vietnamese_words if word in text_lower)
    
    # If more than 2 Vietnamese words found, likely Vietnamese
    if vietnamese_word_count >= 2:
        logger.debug(f"[LANG] Detected Vietnamese ({vietnamese_word_count} Vietnamese words found)")
        return "vi"
    
    # Check text length - if very short and no Vietnamese indicators, might be English
    # But if longer and has Vietnamese words, it's Vietnamese
    if vietnamese_word_count > 0:
        logger.debug(f"[LANG] Detected Vietnamese (some Vietnamese words found)")
        return "vi"
    
    # Default to English
    logger.debug(f"[LANG] Detected English (default)")
    return "en"


class ChatService:
    """Chat Service using MCP (Model Context Protocol) architecture."""
    
    def __init__(self, mcp_host: Optional[MCPHost] = None):
        """
        Initialize ChatService with MCP.
        
        Args:
            mcp_host: MCP Host instance (creates new with servers if None)
        """
        # Use configured LLM provider instead of hardcoded Gemini
        self.llm = create_llm_provider(config.settings.llm_provider)
        self.guardrail = GuardrailService()
        
        # Setup MCP Host and servers
        if mcp_host is None:
            self.mcp_host = MCPHost()
            # Register MCP servers
            memory_server = MemoryMCPServer()
            tool_server = ToolMCPServer()
            self.memory_client = self.mcp_host.register_server(memory_server)
            self.tool_client = self.mcp_host.register_server(tool_server)
        else:
            self.mcp_host = mcp_host
            self.memory_client = mcp_host.get_client("memory-server")
            self.tool_client = mcp_host.get_client("tool-server")
    
    async def process_chat(
        self,
        messages: list,
        model: str,
        conversation_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Process chat completion using MCP architecture.
        
        Args:
            messages: List of messages in OpenAI format
            model: Selected model name
            conversation_id: Optional conversation ID
            
        Returns:
            Tuple of (response_text, conversation_id)
        """
        logger.info(f"[STEP 1] Starting chat processing - Model: {model}, Conversation ID: {conversation_id}")
        
        # Step 1: Extract user message from incoming messages (before any processing)
        logger.debug(f"[STEP 1.1] Extracting user message from {len(messages)} messages")
        user_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                logger.info(f"[STEP 1.2] Extracted user message: {user_message[:100]}...")
                break
        
        if not user_message:
            logger.error("[STEP 1.3] No user message found in messages")
            raise ValueError("User message not found")
        
        # Step 2: Guardrail check FIRST (before getting context to save resources)
        logger.info(f"[STEP 2] Checking guardrail for question: {user_message[:50]}...")
        is_dental = await self.guardrail.is_dental_related(user_message)
        logger.info(f"[STEP 2.1] Guardrail result: {'PASSED' if is_dental else 'REJECTED'}")
        if not is_dental:
            logger.warning(f"[STEP 2.2] Guardrail rejected question: {user_message}")
            
            # Detect language from user message
            user_lang = detect_language(user_message)
            logger.info(f"[STEP 2.2.1] Detected user language: {user_lang}")
            
            # Return friendly message in same language as user
            if user_lang == "vi":
                friendly_message = (
                    "Xin chào! Tôi là trợ lý tư vấn nha khoa. "
                    "Tôi chỉ có thể trả lời các câu hỏi liên quan đến nha khoa như:\n"
                    "- Răng, nướu, miệng\n"
                    "- Các bệnh về răng miệng\n"
                    "- Điều trị nha khoa (trám răng, nhổ răng, niềng răng, cấy ghép răng...)\n"
                    "- Vệ sinh răng miệng\n"
                    "- Chỉnh nha\n"
                    "- Phẫu thuật nha khoa\n"
                    "- Thẩm mỹ nha khoa\n\n"
                    "Vui lòng đặt câu hỏi về chủ đề nha khoa để tôi có thể hỗ trợ bạn tốt nhất!"
                )
            else:
                friendly_message = (
                    "Hello! I am a dental consultation assistant. "
                    "I can only answer questions related to dentistry such as:\n"
                    "- Teeth, gums, mouth\n"
                    "- Dental and oral diseases\n"
                    "- Dental treatments (fillings, extractions, braces, dental implants...)\n"
                    "- Oral hygiene\n"
                    "- Orthodontics\n"
                    "- Dental surgery\n"
                    "- Cosmetic dentistry\n\n"
                    "Please ask questions about dental topics so I can help you best!"
                )
            
            # Still save to memory for conversation continuity
            memory_result = await self.memory_client.call_method(
                "memory/get_or_create",
                {"conversation_id": conversation_id}
            )
            conv_id = memory_result["conversation_id"]
            
            # Save user message and assistant response
            await self.memory_client.call_method(
                "memory/add_message",
                {"conversation_id": conv_id, "role": "user", "content": user_message}
            )
            await self.memory_client.call_method(
                "memory/add_message",
                {"conversation_id": conv_id, "role": "assistant", "content": friendly_message}
            )
            
            logger.info(f"[STEP 2.3] Returned friendly rejection message. Conversation ID: {conv_id}")
            return friendly_message, conv_id
        
        # Step 3: MCP - Get or create conversation via Memory Server (only if passed guardrail)
        logger.info(f"[STEP 3] Getting or creating conversation: {conversation_id}")
        memory_result = await self.memory_client.call_method(
            "memory/get_or_create",
            {"conversation_id": conversation_id}
        )
        conv_id = memory_result["conversation_id"]
        logger.info(f"[STEP 3.1] Conversation ID: {conv_id}")
        
        # Step 4: MCP - Get conversation context from Memory Server (Resource)
        logger.info(f"[STEP 4] Getting conversation context for: {conv_id}")
        context_result = await self.memory_client.call_method(
            "memory/get_context",
            {"conversation_id": conv_id, "max_messages": 20}
        )
        memory_context = context_result.get("messages", [])
        logger.info(f"[STEP 4.1] Retrieved {len(memory_context)} messages from memory")
        
        # Step 5: Merge incoming messages with memory context
        logger.debug(f"[STEP 5] Merging messages - Memory: {len(memory_context)}, Incoming: {len(messages)}")
        all_messages = memory_context.copy()
        
        # Add user message if not already in context
        if not all_messages or all_messages[-1].get("content") != user_message:
            all_messages.append({"role": "user", "content": user_message})
            logger.debug(f"[STEP 5.1] Added user message to context. Total messages: {len(all_messages)}")
        else:
            logger.debug(f"[STEP 5.1] User message already in context, skipping")
        
        # Step 6: MCP - Call search tool via Tool Server
        tool_name = "google_search" if model == "dental-google" else "duckduckgo_search"
        logger.info(f"[STEP 6] Calling search tool: {tool_name} for query: {user_message[:50]}...")
        
        try:
            tool_result = await self.tool_client.call_method(
                "tools/call",
                {
                    "name": tool_name,
                    "arguments": {"query": user_message}
                }
            )
            # Extract text from tool result
            search_results = tool_result["content"][0]["text"]
            logger.info(f"[STEP 6.1] Search completed. Results length: {len(search_results)} characters")
        except Exception as e:
            logger.error(f"[STEP 6.2] Error calling tool {tool_name}: {e}", exc_info=True)
            # No fallback - just raise error
            raise Exception(f"Search tool error: {str(e)}")
        
        # Step 7: Build prompt with conversation context
        logger.debug(f"[STEP 7] Building prompt with {len(all_messages)} messages in context")
        
        # Detect language from user message
        user_lang = detect_language(user_message)
        logger.info(f"[STEP 7.1] Detected user language: {user_lang}")
        
        conversation_summary = ""
        if len(all_messages) > 1:
            prev_messages = [msg for msg in all_messages[:-1] if msg.get("role") in ["user", "assistant"]]
            if prev_messages:
                conversation_summary = "\n\nPrevious conversation context:\n"
                for msg in prev_messages[-5:]:
                    role = "Patient" if msg.get("role") == "user" else "Dentist"
                    conversation_summary += f"{role}: {msg.get('content', '')}\n"
                logger.debug(f"[STEP 7.2] Added {len(prev_messages[-5:])} previous messages to context")
        
        # Build prompt in detected language
        if user_lang == "vi":
            prompt = f"""Bạn là một chuyên gia tư vấn nha khoa chuyên nghiệp với kiến thức sâu rộng. 
Nhiệm vụ của bạn là trả lời câu hỏi của bệnh nhân dựa trên thông tin tìm kiếm và ngữ cảnh cuộc trò chuyện.

{conversation_summary}

Câu hỏi hiện tại của bệnh nhân: {user_message}

Thông tin tìm kiếm:
{search_results}

Vui lòng trả lời câu hỏi một cách:
- Chính xác và dựa trên thông tin tìm kiếm
- Nhất quán với ngữ cảnh cuộc trò chuyện trước đó (nếu có)
- Dễ hiểu và thân thiện
- Đề cập đến nguồn tham khảo nếu có sẵn
- Lưu ý: Nếu thông tin không đầy đủ, đề nghị bệnh nhân tham khảo ý kiến nha sĩ

Trả lời bằng tiếng Việt:"""
        else:
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

Answer in English:"""
        
        logger.debug(f"[STEP 7.2] Prompt built. Length: {len(prompt)} characters")
        
        # Step 8: Generate response with LLM
        logger.info(f"[STEP 8] Generating response with LLM provider: {config.settings.llm_provider}")
        try:
            # Use async LLM provider
            response_text = await self.llm.generate(prompt)
            logger.info(f"[STEP 8.1] LLM response generated. Length: {len(response_text)} characters")
        except Exception as e:
            logger.error(f"[STEP 8.2] Error generating response from LLM: {e}", exc_info=True)
            raise Exception(f"Error generating response: {str(e)}")
        
        # Step 9: MCP - Save messages to Memory Server (only after successful response)
        logger.info(f"[STEP 9] Saving messages to memory for conversation: {conv_id}")
        await self.memory_client.call_method(
            "memory/add_message",
            {"conversation_id": conv_id, "role": "user", "content": user_message}
        )
        logger.debug(f"[STEP 9.1] Saved user message")
        await self.memory_client.call_method(
            "memory/add_message",
            {"conversation_id": conv_id, "role": "assistant", "content": response_text}
        )
        logger.info(f"[STEP 9.2] Saved assistant message. Chat processing completed successfully")
        
        return response_text, conv_id
