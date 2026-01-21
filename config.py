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
    
    # Ollama model for chat responses (main model)
    # Popular models: llama3.2, qwen2.5:7b, mistral, phi-3
    # Default: llama3.2 (~2GB, good quality)
    ollama_model: str = "llama3.2"
    
    # Ollama model for guardrail (can use lighter model)
    # Default: llama3.2 (same as main model)
    # You can use lighter model like phi-3 for faster guardrail checks
    ollama_guardrail_model: str = "llama3.2"
    
    # ============================================
    # Google Gemini Configuration
    # ============================================
    # Google Gemini API Key (required only if using Gemini)
    # Get from: https://makersuite.google.com/app/apikey
    google_api_key: Optional[str] = None
    
    # Gemini model for chat responses
    # Options: gemini-2.5-flash, gemini-2.0-flash, gemini-1.5-pro
    # Default: gemini-2.5-flash (fast, free tier available)
    google_base_model: str = "gemini-2.5-flash"
    
    # Gemini model for guardrail (optional, defaults to google_base_model)
    # You can use gemini-2.0-flash for guardrail if different from main model
    google_guardrail_model: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
