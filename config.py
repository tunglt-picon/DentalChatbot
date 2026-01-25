"""Application configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields from .env (e.g., old Google/Gemini configs)
    )
    
    # ============================================
    # LLM Provider Selection
    # ============================================
    # Only Ollama is supported
    llm_provider: str = "ollama"
    
    # Guardrail Provider (for checking if question is dental-related)
    # Only Ollama is supported
    guardrail_provider: str = "ollama"
    
    # ============================================
    # Ollama Configuration
    # ============================================
    # Ollama server URL (default: localhost)
    ollama_base_url: str = "http://localhost:11434"
    
    # Ollama model for chat responses (main model - heavier for reasoning)
    # Best: qwen2.5:7b-instruct (4.7GB, excellent Vietnamese support)
    # Alternative: qwen2.5:3b-instruct (1.9GB, lighter), llama3.2:latest (2.0GB)
    # Default: qwen2.5:7b-instruct (best quality for Vietnamese)
    ollama_model: str = "qwen2.5:7b-instruct"
    
    # Ollama model for guardrail (lighter models for fast checks)
    # Best: phi3:latest (2.2GB, fast and efficient)
    # Alternative: llama3.2:latest (2.0GB, also good)
    # Default: phi3:latest (lightweight, fast for guardrail checks)
    ollama_guardrail_model: str = "phi3:latest"
    
    # ============================================
    # MCP Server Configuration
    # ============================================
    # MCP HTTP Server URL (default: localhost:8001)
    mcp_server_url: str = "http://localhost:8001"


settings = Settings()
