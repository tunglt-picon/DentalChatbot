"""Chat Service with MCP (Model Context Protocol) implementation."""
import logging
import re
import asyncio
import json
from typing import Optional, Tuple
from clients.mcp_client import MCPHost
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
    
    link_pattern = re.compile(r'Link:\s*(https?://[^\s\n]+)', re.IGNORECASE)
    title_pattern = re.compile(r'Title:\s*([^\n]+)', re.IGNORECASE)
    
    sections = re.split(r'\n*---\n*', search_results)
    
    for section in sections:
        if not section.strip():
            continue
            
        title_match = title_pattern.search(section)
        link_match = link_pattern.search(section)
        
        if link_match:
            link = link_match.group(1).strip()
            link = re.sub(r'[^\w\-_./?#=&:]+$', '', link)
            
            title = title_match.group(1).strip() if title_match else "Nguồn"
            title = re.sub(r'\[\[([^\]]+)\]\]\([^\)]+\)', r'\1', title)
            title = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', title)
            title = title.strip('"\'')
            
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
    
    # Step 1: Normalize existing line breaks
    response_text = re.sub(r'\r\n', '\n', response_text)  # Windows line breaks
    response_text = re.sub(r'\r', '\n', response_text)  # Old Mac line breaks
    response_text = re.sub(r'\n{3,}', '\n\n', response_text)  # Multiple newlines -> double
    
    # Step 2: Ensure double line breaks after sentences ending with .!?
    # Match both English and Vietnamese capital letters
    vietnamese_caps = 'ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ'
    pattern = f'([.!?])\\s+([A-Z{vietnamese_caps}])'
    response_text = re.sub(pattern, r'\1\n\n\2', response_text)
    
    # Step 3: Add paragraph breaks after numbered/bulleted items
    numbered_pattern = f'(\\d+\\.\\s+[^\\n]+)\\n([A-Z{vietnamese_caps}])'
    response_text = re.sub(numbered_pattern, r'\1\n\n\2', response_text)
    
    # Step 4: Add paragraph breaks after bold items (**text**)
    bold_pattern = r'(\*\*[^\*]+\*\*\.?)\s+([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ])'
    response_text = re.sub(bold_pattern, r'\1\n\n\2', response_text)
    
    # Step 5: Clean up extra spaces
    response_text = re.sub(r'[ \t]+', ' ', response_text)
    response_text = re.sub(r' \n', '\n', response_text)
    response_text = re.sub(r'\n ', '\n', response_text)
    
    # Step 6: Ensure proper spacing around line breaks
    response_text = re.sub(r'\n\n+', '\n\n', response_text)
    
    # Step 7: If no double newlines exist, try to add them intelligently
    if '\n\n' not in response_text and '\n' in response_text:
        lines = response_text.split('\n')
        formatted_lines = []
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            formatted_lines.append(line)
            if i < len(lines) - 1:
                next_line = lines[i + 1].strip()
                if next_line and next_line[0].isupper() and not line.endswith(('.', '!', '?', ':', ';')):
                    formatted_lines.append('')
        response_text = '\n\n'.join(formatted_lines)
    
    # Step 8: Trim whitespace
    response_text = response_text.strip()
    
    # Step 9: Add sources section if available
    if sources:
        if user_lang == "vi":
            sources_section = "\n\n---\n\n**Nguồn tham khảo:**\n\n"
            for idx, source in enumerate(sources, 1):
                title = source['title'].replace('[', '\\[').replace(']', '\\]')
                sources_section += f"{idx}. [{title}]({source['link']})\n"
        else:
            sources_section = "\n\n---\n\n**Sources:**\n\n"
            for idx, source in enumerate(sources, 1):
                title = source['title'].replace('[', '\\[').replace(']', '\\]')
                sources_section += f"{idx}. [{title}]({source['link']})\n"
        
        sources_section = sources_section.rstrip() + "\n"
        response_text += sources_section
    
    return response_text


class ChatService:
    """Chat Service using MCP (Model Context Protocol) architecture."""
    
    def __init__(self, mcp_host: Optional[MCPHost] = None):
        """
        Initialize ChatService with MCP.
        
        Args:
            mcp_host: MCP Host instance (creates new if None)
        """
        # Use configured LLM provider (Ollama)
        self.llm = create_llm_provider(config.settings.llm_provider)
        self.guardrail = GuardrailService()
        
        # Setup MCP Host (connects to standalone MCP HTTP server)
        if mcp_host is None:
            import config as app_config
            self.mcp_host = MCPHost(base_url=app_config.settings.mcp_server_url)
        else:
            self.mcp_host = mcp_host
        
        self.memory_client = self.mcp_host.get_client("memory-server")
        self.tool_client = self.mcp_host.get_client("tool-server")
    
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
        
        # Step 1: Extract user message from incoming messages
        logger.debug(f"[STEP 1.1] Extracting user message from {len(messages)} message(s)")
        user_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                logger.info(f"[STEP 1.2] Extracted user message: {user_message[:100]}...")
                break
        
        if not user_message:
            logger.error("[STEP 1.3] No user message found in messages")
            raise ValueError("User message not found")
        
        from services.guardrail import detect_language_llm
        from services.phoenix_tracing import phoenix_span
        
        user_lang = await detect_language_llm(user_message, self.guardrail.llm)
        
        logger.info(f"[STEP 1.5] Detected user language: {user_lang}")
        
        from services.phoenix_tracing import phoenix_span
        
        is_dental, user_lang, llm_response = await self.guardrail.is_dental_related(user_message, user_lang=user_lang)
        
        logger.info(f"[STEP 2.1] Guardrail result: {'PASSED' if is_dental else 'REJECTED'}")
        if not is_dental:
            logger.warning(f"[STEP 2.2] Guardrail rejected question: {user_message}")
            
            friendly_message = PromptManager.get_rejection_message(user_lang)
            conv_id = conversation_id if conversation_id else None
            logger.info(f"[STEP 2.3] Question rejected - NOT saved to memory. Returned friendly rejection message. Conversation ID: {conv_id or 'None'}")
            
            with phoenix_span("guardrail.reject") as span:
                span.set_attribute("guardrail.input.user_message", user_message)
                span.set_attribute("guardrail.input.user_lang", user_lang)
                span.set_attribute("guardrail.output.action", "reject")
                span.set_attribute("guardrail.output.rejection_message", friendly_message)
                if conv_id:
                    span.set_attribute("custom.conversation_id", conv_id)
            
            return friendly_message, conv_id
        
        with phoenix_span("memory.get_or_create_conversation") as span:
            request_payload = {"conversation_id": conversation_id}
            span.set_attribute("memory.input.conversation_id", conversation_id or "new")
            span.set_attribute("memory.input.request", json.dumps(request_payload, ensure_ascii=False))
            span.set_attribute("memory.input.method", "memory/get_or_create")
            
            memory_result = await self.memory_client.call_method(
                "memory/get_or_create",
                {"conversation_id": conversation_id}
            )
            conv_id = memory_result["conversation_id"]
            
            span.set_attribute("memory.output.conversation_id", conv_id)
            span.set_attribute("memory.output.is_new", str(conversation_id is None or conversation_id != conv_id))
            span.set_attribute("memory.output.full", json.dumps(memory_result, ensure_ascii=False))
        
        logger.info(f"[STEP 3.1] Conversation ID: {conv_id}")
        
        with phoenix_span("memory.get_conversation_summary") as span:
            request_payload = {"conversation_id": conv_id}
            span.set_attribute("memory.input.conversation_id", conv_id)
            span.set_attribute("memory.input.request", json.dumps(request_payload, ensure_ascii=False))
            span.set_attribute("memory.input.method", "memory/get_summary")
            
            summary_result = await self.memory_client.call_method(
                "memory/get_summary",
                {"conversation_id": conv_id}
            )
            existing_summary = summary_result.get("summary", "")
            
            span.set_attribute("memory.output.summary.exists", str(bool(existing_summary)))
            if existing_summary:
                span.set_attribute("memory.output.summary", existing_summary)
                span.set_attribute("memory.output.summary.length", len(existing_summary))
            span.set_attribute("memory.output.full", json.dumps(summary_result, ensure_ascii=False))
        
        if existing_summary:
            logger.info(f"[STEP 4.1] Found existing summary: {existing_summary[:100]}...")
        else:
            logger.info(f"[STEP 4.1] No existing summary (first question in conversation)")
        
        # Step 6: Call search tool
        tool_name = "duckduckgo_search"
        logger.info(f"[STEP 6] Calling search tool: {tool_name} for query: {user_message[:50]}...")
        
        try:
            from services.phoenix_tracing import phoenix_span
            from openinference.semconv.trace import SpanAttributes
            
            tool_input = {"query": user_message}
            
            with phoenix_span("tool.duckduckgo_search") as span:
                span.set_attribute(SpanAttributes.TOOL_NAME, tool_name)
                span.set_attribute("tool.input.query", user_message)
                span.set_attribute("tool.input.method", "tools/call")
                span.set_attribute("tool.input.arguments", json.dumps(tool_input, ensure_ascii=False))
                span.set_attribute("custom.conversation_id", conv_id)
                
                tool_result = await self.tool_client.call_method(
                    "tools/call",
                    {"name": tool_name, "arguments": tool_input}
                )
                
                search_results = tool_result["content"][0]["text"]
                span.set_attribute("tool.input.full", json.dumps(tool_input, ensure_ascii=False))
                span.set_attribute("tool.output", search_results)
                span.set_attribute("tool.output.length", len(search_results))
                span.set_attribute("tool.output.full", json.dumps(tool_result, ensure_ascii=False))
            
            logger.info(f"[STEP 6.1] Search completed. Results length: {len(search_results)} characters")
            logger.info(f"[STEP 6.2] Search results (full):\n{search_results}")
        except Exception as e:
            logger.error(f"[STEP 6.2] Error calling tool {tool_name}: {e}", exc_info=True)
            raise Exception(f"Search tool error: {str(e)}")
        
        # Step 7: Build prompt
        logger.info(f"[STEP 7] Building prompt with conversation summary")
        logger.info(f"[STEP 7.1] Using detected user language: {user_lang}")
        
        # Step 7.2: Build conversation summary text for prompt
        conversation_summary = existing_summary if existing_summary else ""
        
        if existing_summary:
            logger.info(f"[STEP 7.2] Using existing summary as context. Summary length: {len(existing_summary)} characters")
            logger.info(f"[STEP 7.2.1] Summary content: {existing_summary[:200]}...")
        else:
            logger.info(f"[STEP 7.2] No summary (first question in conversation)")
        
        # Build prompt using PromptManager
        prompt = PromptManager.get_chat_response_prompt(
            user_message=user_message,
            search_results=search_results,
            conversation_summary=conversation_summary,
            language=user_lang
        )
        
        logger.info(f"[STEP 7.4] Prompt built. Length: {len(prompt)} characters")
        logger.info(f"[STEP 7.4.1] Conversation summary in prompt: {conversation_summary[:200] if conversation_summary else 'EMPTY'}...")
        
        with phoenix_span("tool.extract_sources") as span:
            span.set_attribute("sources.input.search_results", search_results)
            span.set_attribute("sources.input.search_results_length", len(search_results))
            
            sources = _extract_sources(search_results)
            
            sources_json = json.dumps(sources, ensure_ascii=False)
            span.set_attribute("sources.output.sources", sources_json)
            span.set_attribute("sources.output.count", len(sources))
        
        logger.debug(f"[STEP 7.3] Extracted {len(sources)} sources from search results")
        
        # Step 8: Generate response with LLM
        logger.info(f"[STEP 8] Generating response with LLM provider: {config.settings.llm_provider}")
        try:
            response_text = await self.llm.generate(prompt)
            
            logger.info(f"[STEP 8.1] LLM response generated. Length: {len(response_text)} characters")
            
            # Format response
            response_text = _format_response(response_text, sources, user_lang)
            logger.info(f"[STEP 8.2] Response formatted. Final length: {len(response_text)} characters")
            logger.info(f"[STEP 8.3] --- FORMATTED RESPONSE START ---\n{response_text}\n[STEP 8.3] --- FORMATTED RESPONSE END ---")
        except Exception as e:
            logger.error(f"[STEP 8.3] Error generating response from LLM: {e}", exc_info=True)
            raise Exception(f"Error generating response: {str(e)}")
        
        # Step 9: Save messages to memory
        logger.info(f"[STEP 9] Saving messages to memory for conversation: {conv_id}")
        
        with phoenix_span("memory.save_messages") as span:
            span.set_attribute("memory.input.conversation_id", conv_id)
            
            user_message_payload = {"conversation_id": conv_id, "role": "user", "content": user_message}
            span.set_attribute("memory.input.user_message", user_message)
            span.set_attribute("memory.input.user_message.request", json.dumps(user_message_payload, ensure_ascii=False))
            
            await self.memory_client.call_method(
                "memory/add_message",
                user_message_payload
            )
            
            assistant_message_payload = {"conversation_id": conv_id, "role": "assistant", "content": response_text}
            span.set_attribute("memory.input.assistant_message", response_text)
            span.set_attribute("memory.input.assistant_message.request", json.dumps(assistant_message_payload, ensure_ascii=False))
            
            await self.memory_client.call_method(
                "memory/add_message",
                assistant_message_payload
            )
            
            span.set_attribute("memory.output.messages_saved", "2")
            span.set_attribute("memory.output.method", "memory/add_message")
        
        # Step 9.3: Start summarization as background task
        logger.info(f"[STEP 9.3] Starting summarization as background task (non-blocking)")
        asyncio.create_task(
            self._summarize_and_update_summary(
                conv_id=conv_id,
                user_message=user_message,
                response_text=response_text,
                existing_summary=existing_summary,
                user_lang=user_lang
            )
        )
        
        logger.info(f"[STEP 9.4] Chat processing completed successfully. Response returned immediately, summarization running in background.")
        
        return response_text, conv_id
    
    async def _summarize_and_update_summary(
        self,
        conv_id: str,
        user_message: str,
        response_text: str,
        existing_summary: str,
        user_lang: str
    ) -> None:
        """
        Background task to summarize response and update summary.
        
        Args:
            conv_id: Conversation ID
            user_message: User question
            response_text: Assistant response
            existing_summary: Existing summary (if any)
            user_lang: User language
        """
        try:
            logger.info(f"[BACKGROUND] Starting summarization for conversation: {conv_id}")
            
            from services.phoenix_tracing import phoenix_span
            from openinference.semconv.trace import SpanAttributes
            
            summarize_prompt = PromptManager.get_summarize_response_prompt(
                question=user_message,
                response=response_text,
                language=user_lang
            )
            
            with phoenix_span("llm.generate.summary") as span:
                span.set_attribute(SpanAttributes.LLM_MODEL_NAME, config.settings.ollama_guardrail_model)
                span.set_attribute("custom.conversation_id", conv_id)
                span.set_attribute("custom.user_lang", user_lang)
                span.set_attribute("summary.input.user_message", user_message)
                span.set_attribute("summary.input.user_message.length", len(user_message))
                span.set_attribute("summary.input.response_text", response_text)
                span.set_attribute("summary.input.response_text.length", len(response_text))
                span.set_attribute("summary.input.existing_summary", existing_summary)
                span.set_attribute("summary.input.existing_summary.length", len(existing_summary))
                
                input_messages = [{"role": "user", "content": summarize_prompt}]
                span.set_attribute(SpanAttributes.LLM_INPUT_MESSAGES, json.dumps(input_messages, ensure_ascii=False))
                span.set_attribute("summary.input.prompt", summarize_prompt)
                span.set_attribute("summary.input.prompt.length", len(summarize_prompt))
                span.set_attribute("summary.input.max_tokens", "100")
                
                new_response_summary = await self.guardrail.llm.generate(summarize_prompt, use_guardrail_model=True, max_tokens=100)
                new_response_summary = new_response_summary.strip()
                
                output_messages = [{"role": "assistant", "content": new_response_summary}]
                span.set_attribute(SpanAttributes.LLM_OUTPUT_MESSAGES, json.dumps(output_messages, ensure_ascii=False))
                span.set_attribute("summary.output.summary", new_response_summary)
                span.set_attribute("summary.output.summary.length", len(new_response_summary))
            
            logger.info(f"[BACKGROUND] Summary generated: {new_response_summary[:100]}...")
            
            with phoenix_span("memory.update_summary") as span:
                span.set_attribute("memory.input.conversation_id", conv_id)
                span.set_attribute("memory.input.new_summary", new_response_summary)
                span.set_attribute("memory.input.existing_summary", existing_summary)
                span.set_attribute("memory.input.existed", str(bool(existing_summary)))
                
                if existing_summary:
                    updated_summary = f"{existing_summary}\n\n{new_response_summary}"
                else:
                    updated_summary = new_response_summary
                
                request_payload = {"conversation_id": conv_id, "summary": updated_summary, "compress": False}
                span.set_attribute("memory.input.request", json.dumps(request_payload, ensure_ascii=False))
                span.set_attribute("memory.input.method", "memory/set_summary")
                
                await self.memory_client.call_method(
                    "memory/set_summary",
                    request_payload
                )
                
                span.set_attribute("memory.output.updated_summary", updated_summary)
                span.set_attribute("memory.output.updated_summary.length", len(updated_summary))
                span.set_attribute("memory.output.summary_increased", str(len(updated_summary) > len(existing_summary) if existing_summary else True))
        except Exception as e:
            logger.error(f"[BACKGROUND] Error updating summary: {e}", exc_info=True)