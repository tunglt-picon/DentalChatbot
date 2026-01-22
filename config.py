"""Application configuration."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # ============================================
    # LLM Provider Selection
    # ============================================
    # Options: "ollama" or "gemini"
    # Default: "ollama" (free, no rate limits, runs locally)
    llm_provider: str = "ollama"
    
    # Guardrail Provider (for checking if question is dental-related)
    # Options: "ollama" or "gemini"
    # Default: "ollama" (can use lighter model to save resources)
    guardrail_provider: str = "ollama"
    
    # ============================================
    # Ollama Configuration
    # ============================================
    # Ollama server URL (default: localhost)
    ollama_base_url: str = "http://localhost:11434"
    
    # Ollama model for chat responses (main model - heavier for reasoning)
    # Popular models: llama3.2:3b, qwen2.5:7b, mistral:7b, llama3.1:8b
    # Default: llama3.2:3b (~2GB, good quality)
    ollama_model: str = "llama3.2:3b"
    
    # Ollama model for guardrail (lighter models for fast checks)
    # Recommended: phi-3 (~2GB), tinyllama (~700MB)
    # Default: phi-3 (lightweight, fast)
    ollama_guardrail_model: str = "phi-3"
    
    # ============================================
    # Google Gemini Configuration
    # ============================================
    # Google Gemini API Key (required only if using Gemini)
    # Get from: https://makersuite.google.com/app/apikey
    google_api_key: Optional[str] = None
    
    # Gemini model for chat responses
    # Options: gemini-1.5-flash, gemini-2.5-flash
    # Default: gemini-1.5-flash (fast, free tier available)
    google_base_model: str = "gemini-1.5-flash"
    
    # Gemini model for guardrail (optional, defaults to google_base_model)
    # Options: gemini-1.5-flash, gemini-2.5-flash
    # Default: gemini-1.5-flash (fast for guardrail checks)
    google_guardrail_model: Optional[str] = "gemini-1.5-flash"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
