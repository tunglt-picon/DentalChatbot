"""Services module."""
# Lazy imports to avoid circular dependencies
# Import only when needed, not at module level

__all__ = ["GuardrailService", "ChatService", "MemoryService"]

def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name == "GuardrailService":
        from .guardrail import GuardrailService
        return GuardrailService
    elif name == "ChatService":
        from .chat_service import ChatService
        return ChatService
    elif name == "MemoryService":
        from .memory import MemoryService
        return MemoryService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
