"""LLM Provider abstraction layer for multiple providers."""
import logging
from abc import ABC, abstractmethod
from typing import Optional
import config

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate text from prompt."""
        pass


class GeminiProvider(LLMProvider):
    """Google Gemini provider."""
    
    def __init__(self, model_name: Optional[str] = None, guardrail_model: Optional[str] = None):
        """
        Initialize Gemini provider.
        
        Args:
            model_name: Model name for chat (defaults to google_base_model)
            guardrail_model: Model name for guardrail (defaults to google_guardrail_model or model_name)
        """
        if not config.settings.google_api_key:
            raise ValueError("Google API key is required for Gemini provider")
        
        self.model_name = model_name or config.settings.google_base_model
        self.guardrail_model = guardrail_model or config.settings.google_guardrail_model or self.model_name
        
        logger.info(f"[GEMINI] Initializing with model: {self.model_name}, guardrail model: {self.guardrail_model}")
        import google.generativeai as genai
        genai.configure(api_key=config.settings.google_api_key)
        self.model = genai.GenerativeModel(self.model_name)
        self.guardrail_model_instance = genai.GenerativeModel(self.guardrail_model) if self.guardrail_model != self.model_name else self.model
    
    async def generate(self, prompt: str, use_guardrail_model: bool = False) -> str:
        """Generate using Gemini."""
        model_to_use = self.guardrail_model_instance if use_guardrail_model else self.model
        model_name = self.guardrail_model if use_guardrail_model else self.model_name
        logger.info(f"[GEMINI] Generating response with model: {model_name}, prompt length: {len(prompt)}")
        try:
            response = model_to_use.generate_content(prompt)
            result = response.text
            logger.info(f"[GEMINI] Generation completed. Response length: {len(result)} characters")
            return result
        except Exception as e:
            logger.error(f"[GEMINI] Error: {e}", exc_info=True)
            raise


class OllamaProvider(LLMProvider):
    """Ollama local provider (completely free, no rate limits)."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2", guardrail_model: Optional[str] = None):
        """
        Initialize Ollama provider.
        
        Args:
            base_url: Ollama server URL (default: http://localhost:11434)
            model: Model name (llama3.2, mistral, phi-3, qwen2.5:7b, etc.)
            guardrail_model: Optional separate model for guardrail (lighter model)
        """
        self.base_url = base_url
        self.model = model
        self.guardrail_model = guardrail_model or model
    
    async def generate(self, prompt: str, use_guardrail_model: bool = False) -> str:
        """Generate using Ollama."""
        model_to_use = self.guardrail_model if use_guardrail_model else self.model
        logger.info(f"[OLLAMA] Generating with model: {model_to_use}, prompt length: {len(prompt)}")
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.debug(f"[OLLAMA] Sending request to {self.base_url}/api/generate")
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model_to_use,
                        "prompt": prompt,
                        "stream": False
                    }
                )
                logger.debug(f"[OLLAMA] Response status: {response.status_code}")
                response.raise_for_status()
                data = response.json()
                result = data.get("response", "")
                logger.info(f"[OLLAMA] Generation completed. Response length: {len(result)} characters")
                return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                error_msg = f"Ollama model '{model_to_use}' not found. Please run: ollama pull {model_to_use}"
                logger.error(f"[OLLAMA] {error_msg}")
                raise Exception(error_msg)
            logger.error(f"[OLLAMA] HTTP error {e.response.status_code}: {e}")
            raise Exception(f"Ollama HTTP error: {str(e)}")
        except httpx.ConnectError as e:
            error_msg = f"Cannot connect to Ollama at {self.base_url}. Is Ollama running? Start with: ollama serve"
            logger.error(f"[OLLAMA] Connection error: {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"[OLLAMA] Error: {e}", exc_info=True)
            raise Exception(f"Ollama error: {str(e)}")




def create_llm_provider(provider_type: str = "ollama") -> LLMProvider:
    """
    Factory function to create LLM provider.
    
    Args:
        provider_type: "ollama" or "gemini"
    
    Returns:
        LLMProvider instance
    """
    provider_type = provider_type.lower()
    logger.info(f"Creating LLM provider: {provider_type}")
    
    if provider_type == "ollama":
        base_url = getattr(config.settings, 'ollama_base_url', 'http://localhost:11434')
        model = getattr(config.settings, 'ollama_model', 'llama3.2')
        guardrail_model = getattr(config.settings, 'ollama_guardrail_model', 'llama3.2')
        logger.info(f"Ollama config - Base URL: {base_url}, Model: {model}, Guardrail Model: {guardrail_model}")
        return OllamaProvider(base_url=base_url, model=model, guardrail_model=guardrail_model)
    elif provider_type == "gemini":
        logger.info("Creating Gemini provider")
        model_name = getattr(config.settings, 'google_base_model', 'gemini-2.5-flash')
        guardrail_model = getattr(config.settings, 'google_guardrail_model', None)
        return GeminiProvider(model_name=model_name, guardrail_model=guardrail_model)
    else:
        raise ValueError(f"Unknown provider type: {provider_type}. Supported: 'ollama', 'gemini'")
