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
    
    # Ollama model for guardrail and summary (lighter models for fast checks)
    # Best: qwen2.5:3b-instruct (1.9GB, fast and efficient, good Vietnamese support)
    # Alternative: phi3:latest (2.2GB, also good), llama3.2:latest (2.0GB)
    # Default: qwen2.5:3b-instruct (lightweight, fast for guardrail checks and summarization)
    ollama_guardrail_model: str = "qwen2.5:3b-instruct"
    
    # ============================================
    # MCP Server Configuration
    # ============================================
    # MCP HTTP Server URL (default: localhost:8001)
    mcp_server_url: str = "http://localhost:8001"
    
    # ============================================
    # Phoenix Observability Configuration
    # ============================================
    phoenix_enabled: bool = True
    
    # Phoenix server endpoint (default: localhost:4317 for gRPC OTLP)
    # Phoenix OTLP receiver uses gRPC on port 4317, not HTTP on port 6006
    # Port 6006 is for UI only
    # Khi chạy trong Docker, sử dụng: http://phoenix:4317
    # Khi chạy local, sử dụng: http://localhost:4317
    phoenix_endpoint: str = "http://localhost:4317"
    
    # Phoenix project name (default: dental-chatbot)
    phoenix_project_name: str = "dental-chatbot"


settings = Settings()
