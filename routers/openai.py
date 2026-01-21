"""OpenAI-compatible API routes with MCP (Model Context Protocol) support."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import logging
from services.chat_service import ChatService
from mcp.base import MCPHost
from mcp.servers import MemoryMCPServer, ToolMCPServer

logger = logging.getLogger(__name__)

# Initialize MCP Host and servers
logger.info("Initializing MCP Host and servers...")
mcp_host = MCPHost()
memory_server = MemoryMCPServer()
tool_server = ToolMCPServer()
mcp_host.register_server(memory_server)
mcp_host.register_server(tool_server)
logger.info("MCP servers registered successfully")

# Initialize ChatService with MCP
chat_service = ChatService(mcp_host=mcp_host)

router = APIRouter()


class Message(BaseModel):
    """Message model for chat."""
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    """Request model for chat completion."""
    model_config = ConfigDict(extra="allow")  # Allow extra fields from OpenWebUI
    
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    # OpenWebUI sends chat_id in payload
    chat_id: Optional[str] = None
    # OpenWebUI background tasks
    background_tasks: Optional[dict] = None


class ChatCompletionResponse(BaseModel):
    """Response model for chat completion."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[dict]
    usage: dict


@router.get("/v1/models")
async def list_models():
    """
    List available models (OpenAI-compatible endpoint).
    Open WebUI uses this to know what models are available.
    """
    return {
        "object": "list",
        "data": [
            {"id": "dental-google", "object": "model", "owned_by": "me"},
            {"id": "dental-duckduckgo", "object": "model", "owned_by": "me"},
        ]
    }


@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    Handle chat completion requests (OpenAI-compatible endpoint).
    Routes to appropriate search tool based on model name.
    Supports conversation memory via chat_id in request payload.
    
    Note: If chat_id is not provided, a new conversation_id will be automatically created.
    """
    import time
    
    # Validate model
    valid_models = ["dental-google", "dental-duckduckgo"]
    if request.model not in valid_models:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model. Must be one of: {', '.join(valid_models)}"
        )
    
    try:
        logger.info(f"[REQUEST] Received chat completion request - Model: {request.model}")
        
        # Convert Pydantic models to dict for service
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        logger.debug(f"[REQUEST] Parsed {len(messages)} messages from request")
        
        # Check if this is a background task (title generation, follow-up generation, etc.)
        is_background_task = False
        if request.background_tasks:
            is_background_task = any(request.background_tasks.values())
            logger.debug(f"[REQUEST] Background tasks: {request.background_tasks}")
        
        # Also check message content for background task patterns
        if messages:
            last_message_content = messages[-1].get("content", "")
            # OpenWebUI background tasks often have specific prompts
            background_patterns = [
                "Generate a concise",
                "Suggest 3-5 relevant follow-up",
                "### Task:",
                "Task:"
            ]
            if any(pattern in last_message_content for pattern in background_patterns):
                is_background_task = True
                logger.debug(f"[REQUEST] Detected background task pattern in message")
        
        if is_background_task:
            logger.info("[REQUEST] Detected background task, skipping guardrail and search")
        
        # Get chat_id from payload (if provided)
        # OpenWebUI sends chat_id in the payload
        # Try to get from both direct attribute and model dump (in case of parsing issues)
        request_dump = request.model_dump()
        conversation_id = request.chat_id or request_dump.get("chat_id")
        
        # Log conversation_id status (for debugging)
        if conversation_id:
            logger.info(f"[REQUEST] Received chat_id from payload: {conversation_id}")
        else:
            logger.warning("[REQUEST] No chat_id in payload, will create new conversation")
        
        # For background tasks, return a simple response without processing
        if is_background_task:
            logger.info("Skipping full processing for background task")
            # Return a simple response for background tasks
            response_data = {
                "id": f"chatcmpl-bg-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": ""  # Empty content for background tasks
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }
            return response_data
        
        # Process chat with conversation memory
        # If conversation_id is None, service will automatically create a new one
        response_text, conversation_id = await chat_service.process_chat(
            messages,
            request.model,
            conversation_id=conversation_id
        )
        
        logger.debug(f"Processed chat with conversation_id: {conversation_id}")
        
        # Format response in OpenAI format
        response_data = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 0,  # Could implement token counting if needed
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
        
        # Add conversation_id to response for conversation continuity
        # Note: FastAPI response headers should be set via Response object
        # For now, we include it in the response body metadata
        response_data["system_fingerprint"] = conversation_id
        
        return response_data
        
    except ValueError as e:
        # This should not happen now as guardrail returns friendly message
        # But keep for other validation errors
        logger.warning(f"Validation error: {str(e)}")
        error_message = str(e)
        
        # Format error response in OpenAI format
        error_response = {
            "id": f"chatcmpl-error-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model if hasattr(request, 'model') else "unknown",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": error_message
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            },
            "error": {
                "message": error_message,
                "type": "invalid_request_error",
                "code": "guardrail_rejection"
            }
        }
        
        # Return error response with 200 status (OpenAI-compatible)
        # OpenWebUI will display the error message to user
        return error_response
        
    except Exception as e:
        logger.error(f"Error processing chat completion: {e}", exc_info=True)
        # Return error in OpenAI format
        error_response = {
            "id": f"chatcmpl-error-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model if hasattr(request, 'model') else "unknown",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"Internal server error: {str(e)}"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            },
            "error": {
                "message": str(e),
                "type": "server_error",
                "code": "internal_error"
            }
        }
        return error_response


@router.get("/v1/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Get conversation context (using MCP).
    """
    try:
        memory_client = mcp_host.get_client("memory-server")
        if not memory_client:
            raise HTTPException(status_code=500, detail="Memory server not available")
        
        # Get context via MCP
        context_result = await memory_client.call_method(
            "memory/get_context",
            {"conversation_id": conversation_id}
        )
        
        # Get summary directly from memory_server instance
        summary = memory_server.memory_service.get_conversation_summary(conversation_id)
        
        return {
            "conversation_id": conversation_id,
            "messages": context_result.get("messages", []),
            "summary": summary
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")


@router.delete("/v1/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete conversation (using MCP).
    """
    try:
        memory_client = mcp_host.get_client("memory-server")
        if not memory_client:
            raise HTTPException(status_code=500, detail="Memory server not available")
        
        result = await memory_client.call_method(
            "memory/delete",
            {"conversation_id": conversation_id}
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")


@router.post("/v1/conversations/{conversation_id}/clear")
async def clear_conversation(conversation_id: str):
    """
    Clear conversation history (using MCP).
    """
    try:
        memory_client = mcp_host.get_client("memory-server")
        if not memory_client:
            raise HTTPException(status_code=500, detail="Memory server not available")
        
        result = await memory_client.call_method(
            "memory/clear",
            {"conversation_id": conversation_id}
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")
