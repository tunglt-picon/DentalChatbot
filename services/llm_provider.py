"""LLM Provider abstraction layer for Ollama."""
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
    
    async def generate(self, prompt: str, use_guardrail_model: bool = False, max_tokens: Optional[int] = None) -> str:
        """
        Generate using Ollama.
        
        Args:
            prompt: Input prompt
            use_guardrail_model: Use guardrail model (smaller, faster)
            max_tokens: Maximum tokens to generate (None = no limit, for summarization use smaller value)
        """
        model_to_use = self.guardrail_model if use_guardrail_model else self.model
        logger.info(f"[OLLAMA] Generating with model: {model_to_use}, prompt length: {len(prompt)}")
        logger.info(f"[OLLAMA] --- PROMPT START ---\n{prompt}\n[OLLAMA] --- PROMPT END ---")
        
        try:
            import httpx
            # Increase timeout for larger models (qwen2.5:7b-instruct can take longer)
            # For guardrail/summarization (smaller models), use shorter timeout
            if use_guardrail_model or max_tokens:
                timeout_duration = 60.0  # Faster timeout for small tasks
            else:
                timeout_duration = 180.0 if "7b" in model_to_use or "8b" in model_to_use else 120.0
            async with httpx.AsyncClient(timeout=timeout_duration) as client:
                logger.debug(f"[OLLAMA] Sending request to {self.base_url}/api/generate")
                request_payload = {
                    "model": model_to_use,
                    "prompt": prompt,
                    "stream": False
                }
                # Add num_predict to limit tokens for faster generation (especially for summarization)
                if max_tokens:
                    request_payload["options"] = {"num_predict": max_tokens}
                logger.debug(f"[OLLAMA] Request payload (model, stream only): model={model_to_use}, stream=False")
                
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=request_payload
                )
                logger.debug(f"[OLLAMA] Response status: {response.status_code}")
                response.raise_for_status()
                data = response.json()
                result = data.get("response", "")
                logger.info(f"[OLLAMA] Generation completed. Response length: {len(result)} characters")
                logger.info(f"[OLLAMA] --- RESPONSE START ---\n{result}\n[OLLAMA] --- RESPONSE END ---")
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




def create_llm_provider(provider_type: str = "ollama", log_config: bool = True) -> LLMProvider:
    """
    Factory function to create LLM provider.
    
    Args:
        provider_type: "ollama" (only supported provider)
        log_config: Whether to log configuration (default: True)
    
    Returns:
        LLMProvider instance
    """
    provider_type = provider_type.lower()
    if log_config:
        logger.info(f"Creating LLM provider: {provider_type}")
    
    if provider_type == "ollama":
        base_url = getattr(config.settings, 'ollama_base_url', 'http://localhost:11434')
        model = getattr(config.settings, 'ollama_model', 'llama3.2')
        guardrail_model = getattr(config.settings, 'ollama_guardrail_model', 'llama3.2')
        if log_config:
            logger.info(f"Ollama config - Base URL: {base_url}, Model: {model}, Guardrail Model: {guardrail_model}")
        return OllamaProvider(base_url=base_url, model=model, guardrail_model=guardrail_model)
    else:
        raise ValueError(f"Unknown provider type: {provider_type}. Only 'ollama' is supported.")
