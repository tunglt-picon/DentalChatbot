"""Chat Service with MCP (Model Context Protocol) implementation."""
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import logging
import asyncio
from typing import Optional, Tuple
from mcp.base import MCPHost
from mcp.servers import MemoryMCPServer, ToolMCPServer
from services.guardrail import GuardrailService
import config

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=config.settings.google_api_key)


class ChatServiceMCP:
    """Chat Service using MCP (Model Context Protocol) architecture."""
    
    def __init__(self, mcp_host: Optional[MCPHost] = None):
        """
        Initialize ChatService with MCP.
        
        Args:
            mcp_host: MCP Host instance (creates new with servers if None)
        """
        self.model = genai.GenerativeModel(config.settings.google_base_model)
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
        # Step 1: MCP - Get or create conversation via Memory Server
        memory_result = await self.memory_client.call_method(
            "memory/get_or_create",
            {"conversation_id": conversation_id}
        )
        conv_id = memory_result["conversation_id"]
        
        # Step 2: MCP - Get conversation context from Memory Server (Resource)
        context_result = await self.memory_client.call_method(
            "memory/get_context",
            {"conversation_id": conv_id, "max_messages": 20}
        )
        memory_context = context_result.get("messages", [])
        
        # Step 3: Merge incoming messages with memory context
        all_messages = memory_context.copy()
        user_message = None
        
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                if not all_messages or all_messages[-1].get("content") != user_message:
                    all_messages.append(msg)
                break
        
        if not user_message:
            raise ValueError("User message not found")
        
        # Step 4: Guardrail
        is_dental = await self.guardrail.is_dental_related(user_message)
        if not is_dental:
            raise ValueError(
                "Sorry, I can only answer questions related to the dental field. "
                "Please ask about teeth, gums, dental treatments, or other oral health issues."
            )
        
        # Step 5: MCP - Call search tool via Tool Server
        tool_name = "google_search" if model == "dental-google" else "duckduckgo_search"
        
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
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            # Fallback to DuckDuckGo if Google fails
            if tool_name == "google_search":
                logger.info("Fallback to DuckDuckGo...")
                tool_result = await self.tool_client.call_method(
                    "tools/call",
                    {
                        "name": "duckduckgo_search",
                        "arguments": {"query": user_message}
                    }
                )
                search_results = tool_result["content"][0]["text"]
            else:
                raise
        
        # Step 6: Build prompt with conversation context
        conversation_summary = ""
        if len(all_messages) > 1:
            prev_messages = [msg for msg in all_messages[:-1] if msg.get("role") in ["user", "assistant"]]
            if prev_messages:
                conversation_summary = "\n\nPrevious conversation context:\n"
                for msg in prev_messages[-5:]:
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
        
        # Step 7: Generate response with LLM (with retry for rate limits)
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # generate_content is sync, but we're in async context
                response = self.model.generate_content(prompt)
                response_text = response.text
                break  # Success, exit retry loop
            except google_exceptions.ResourceExhausted as e:
                if attempt < max_retries - 1:
                    # Extract retry delay from error if available
                    retry_seconds = 60  # Default 60 seconds
                    if "retry in" in str(e).lower():
                        # Try to extract seconds from error message
                        import re
                        match = re.search(r'retry in ([\d.]+)s', str(e), re.IGNORECASE)
                        if match:
                            retry_seconds = int(float(match.group(1))) + 5  # Add buffer
                    
                    logger.warning(
                        f"Rate limit exceeded (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {retry_seconds} seconds..."
                    )
                    await asyncio.sleep(retry_seconds)
                else:
                    # Last attempt failed
                    logger.error(f"Rate limit exceeded after {max_retries} attempts")
                    raise Exception(
                        f"Gemini API rate limit exceeded. Please wait before retrying. "
                        f"Free tier allows 5 requests/minute. Error: {str(e)}"
                    )
            except Exception as e:
                # Other errors - don't retry
                logger.error(f"Error generating response from LLM: {e}")
                raise Exception(f"Error generating response: {str(e)}")
            
            # Step 8: MCP - Save messages to Memory Server
            await self.memory_client.call_method(
                "memory/add_message",
                {"conversation_id": conv_id, "role": "user", "content": user_message}
            )
            await self.memory_client.call_method(
                "memory/add_message",
                {"conversation_id": conv_id, "role": "assistant", "content": response_text}
            )
            
            return response_text, conv_id
