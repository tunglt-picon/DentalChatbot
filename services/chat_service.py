"""Chat Service with MCP (Model Context Protocol) implementation."""
import logging
import re
from typing import Optional, Tuple
from mcp.base import MCPHost
from mcp.servers import MemoryMCPServer, ToolMCPServer
from services.guardrail import GuardrailService
from services.llm_provider import create_llm_provider
from services.prompts import PromptManager
import config

logger = logging.getLogger(__name__)


def _extract_sources(search_results: str) -> list:
    """
    Extract source links from search results.
    
    Args:
        search_results: Formatted search results text
        
    Returns:
        List of source dictionaries with title and link
    """
    sources = []
    import re
    
    # Pattern to match "Link: <url>" in search results
    link_pattern = re.compile(r'Link:\s*(https?://[^\s\n]+)', re.IGNORECASE)
    title_pattern = re.compile(r'Title:\s*([^\n]+)', re.IGNORECASE)
    
    # Split by "---" separator (both with and without newlines)
    sections = re.split(r'\n*---\n*', search_results)
    
    for section in sections:
        if not section.strip():
            continue
            
        # Extract title and link from each section
        title_match = title_pattern.search(section)
        link_match = link_pattern.search(section)
        
        if link_match:
            link = link_match.group(1).strip()
            # Remove trailing characters that might be part of formatting
            link = re.sub(r'[^\w\-_./?#=&:]+$', '', link)
            
            title = title_match.group(1).strip() if title_match else "Nguồn"
            # Clean title
            title = title.strip('"\'')
            
            # Avoid duplicates
            if link and link not in [s.get('link', '') for s in sources]:
                sources.append({
                    'title': title,
                    'link': link
                })
    
    logger.debug(f"[EXTRACT_SOURCES] Extracted {len(sources)} unique sources")
    return sources


def _format_response(response_text: str, sources: list, user_lang: str) -> str:
    """
    Format response with proper line breaks and add sources.
    
    Args:
        response_text: Raw response from LLM
        sources: List of source dictionaries
        user_lang: User language ("vi" or "en")
        
    Returns:
        Formatted response with sources
    """
    import re
    
    # Step 1: Normalize existing line breaks
    response_text = re.sub(r'\r\n', '\n', response_text)  # Windows line breaks
    response_text = re.sub(r'\r', '\n', response_text)  # Old Mac line breaks
    response_text = re.sub(r'\n{3,}', '\n\n', response_text)  # Multiple newlines -> double
    
    # Step 2: Ensure double line breaks after sentences ending with .!?
    # Match both English and Vietnamese capital letters
    vietnamese_caps = 'ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ'
    pattern = f'([.!?])\\s+([A-Z{vietnamese_caps}])'
    response_text = re.sub(pattern, r'\1\n\n\2', response_text)
    
    # Step 3: Add paragraph breaks after numbered/bulleted items (1., 2., -, *, etc.)
    # Pattern: number or bullet followed by text starting with capital
    numbered_pattern = f'(\\d+\\.\\s+[^\\n]+)\\n([A-Z{vietnamese_caps}])'
    response_text = re.sub(numbered_pattern, r'\1\n\n\2', response_text)
    
    # Step 4: Add paragraph breaks after bold items (**text**)
    bold_pattern = r'(\*\*[^\*]+\*\*\.?)\s+([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ])'
    response_text = re.sub(bold_pattern, r'\1\n\n\2', response_text)
    
    # Step 5: Clean up extra spaces but preserve intentional spacing
    response_text = re.sub(r'[ \t]+', ' ', response_text)  # Multiple spaces/tabs -> single space
    response_text = re.sub(r' \n', '\n', response_text)  # Space before newline
    response_text = re.sub(r'\n ', '\n', response_text)  # Space after newline
    
    # Step 6: Ensure proper spacing around line breaks
    response_text = re.sub(r'\n\n+', '\n\n', response_text)  # Multiple double newlines -> single double
    
    # Step 7: If no double newlines exist, try to add them intelligently
    # Split by single newlines and check if we should combine or separate
    if '\n\n' not in response_text and '\n' in response_text:
        lines = response_text.split('\n')
        formatted_lines = []
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            formatted_lines.append(line)
            # Add double newline if next line starts with capital and current doesn't end with punctuation
            if i < len(lines) - 1:
                next_line = lines[i + 1].strip()
                if next_line and next_line[0].isupper() and not line.endswith(('.', '!', '?', ':', ';')):
                    formatted_lines.append('')  # Add empty line for double newline
        response_text = '\n\n'.join(formatted_lines)
    
    # Step 8: Trim whitespace
    response_text = response_text.strip()
    
    # Step 9: Add sources section if available
    if sources:
        if user_lang == "vi":
            sources_section = "\n\n---\n\n**Nguồn tham khảo:**\n\n"
            for idx, source in enumerate(sources, 1):
                sources_section += f"{idx}. [{source['title']}]({source['link']})\n"
        else:
            sources_section = "\n\n---\n\n**Sources:**\n\n"
            for idx, source in enumerate(sources, 1):
                sources_section += f"{idx}. [{source['title']}]({source['link']})\n"
        
        response_text += sources_section
    
    return response_text


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
            
            # Detect language from user message using LLM
            from services.guardrail import detect_language_llm
            user_lang = await detect_language_llm(user_message, self.guardrail.llm)
            logger.info(f"[STEP 2.2.1] Detected user language: {user_lang}")
            
            friendly_message = PromptManager.get_rejection_message(user_lang)
            
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
            logger.info(f"[STEP 6.2] Search results (full):\n{search_results}")
        except Exception as e:
            logger.error(f"[STEP 6.2] Error calling tool {tool_name}: {e}", exc_info=True)
            # No fallback - just raise error
            raise Exception(f"Search tool error: {str(e)}")
        
        # Step 7: Build prompt with conversation context
        logger.debug(f"[STEP 7] Building prompt with {len(all_messages)} messages in context")
        
        # Detect language from user message using LLM
        from services.guardrail import detect_language_llm
        user_lang = await detect_language_llm(user_message, self.guardrail.llm)
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
        
        # Extract sources from search results
        sources = _extract_sources(search_results)
        logger.debug(f"[STEP 7.3] Extracted {len(sources)} sources from search results")
        
        # Build prompt using PromptManager
        prompt = PromptManager.get_chat_response_prompt(
            user_message=user_message,
            search_results=search_results,
            conversation_summary=conversation_summary,
            language=user_lang
        )
        
        logger.info(f"[STEP 7.4] Prompt built. Length: {len(prompt)} characters")
        logger.info(f"[STEP 7.5] Full prompt content:\n{prompt}")
        
        # Step 8: Generate response with LLM
        logger.info(f"[STEP 8] Generating response with LLM provider: {config.settings.llm_provider}")
        try:
            # Use async LLM provider
            response_text = await self.llm.generate(prompt)
            logger.info(f"[STEP 8.1] LLM response generated. Length: {len(response_text)} characters")
            logger.info(f"[STEP 8.2] Raw LLM response (full):\n{response_text}")
            
            # Format response: ensure proper line breaks and add sources
            response_text = _format_response(response_text, sources, user_lang)
            logger.info(f"[STEP 8.3] Response formatted. Final length: {len(response_text)} characters")
            logger.info(f"[STEP 8.4] Formatted response with sources (full):\n{response_text}")
        except Exception as e:
            logger.error(f"[STEP 8.3] Error generating response from LLM: {e}", exc_info=True)
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
