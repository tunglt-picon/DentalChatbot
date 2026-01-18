"""OpenAI-compatible API routes with MCP (Memory Context Protocol)."""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import List, Optional
import logging
from services.chat_service import ChatService
from services.memory import MemoryService

logger = logging.getLogger(__name__)

router = APIRouter()
memory_service = MemoryService()
chat_service = ChatService(memory_service=memory_service)


class Message(BaseModel):
    """Message model for chat."""
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    """Request model for chat completion."""
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False


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
async def chat_completions(
    request: ChatCompletionRequest,
    x_conversation_id: Optional[str] = Header(None, alias="X-Conversation-ID")
):
    """
    Handle chat completion requests (OpenAI-compatible endpoint with MCP).
    Routes to appropriate search tool based on model name.
    Supports conversation memory via X-Conversation-ID header.
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
        # Convert Pydantic models to dict for service
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Process chat with MCP (Memory Context Protocol)
        response_text, conversation_id = await chat_service.process_chat(
            messages,
            request.model,
            conversation_id=x_conversation_id
        )
        
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
        
        # Add conversation_id to response headers for MCP
        # Note: FastAPI response headers should be set via Response object
        # For now, we include it in the response body metadata
        response_data["system_fingerprint"] = conversation_id
        
        return response_data
        
    except ValueError as e:
        # Guardrail rejection or validation error
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing chat completion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/v1/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Get conversation context (MCP endpoint).
    """
    try:
        context = memory_service.get_conversation_context(conversation_id)
        summary = memory_service.get_conversation_summary(conversation_id)
        
        return {
            "conversation_id": conversation_id,
            "messages": context,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")


@router.delete("/v1/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete conversation (MCP endpoint).
    """
    try:
        memory_service.delete_conversation(conversation_id)
        return {"status": "deleted", "conversation_id": conversation_id}
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")


@router.post("/v1/conversations/{conversation_id}/clear")
async def clear_conversation(conversation_id: str):
    """
    Clear conversation history (MCP endpoint).
    """
    try:
        memory_service.clear_conversation(conversation_id)
        return {"status": "cleared", "conversation_id": conversation_id}
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")
