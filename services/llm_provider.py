"""LLM Provider abstraction layer for Ollama."""
import logging
from abc import ABC, abstractmethod
from typing import Optional
import config

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        pass


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2", guardrail_model: Optional[str] = None):
        self.base_url = base_url
        self.model = model
        self.guardrail_model = guardrail_model or model
    
    async def generate(self, prompt: str, use_guardrail_model: bool = False, max_tokens: Optional[int] = None) -> str:
        model_to_use = self.guardrail_model if use_guardrail_model else self.model
        logger.info(f"[OLLAMA] Generating with model: {model_to_use}, prompt length: {len(prompt)}")
        logger.info(f"[OLLAMA] --- PROMPT START ---\n{prompt}\n[OLLAMA] --- PROMPT END ---")
        
        try:
            import httpx
            import json
            from services.phoenix_tracing import phoenix_span
            from openinference.semconv.trace import SpanAttributes
            
            if use_guardrail_model or max_tokens:
                timeout_duration = 60.0
            else:
                timeout_duration = 180.0 if "7b" in model_to_use or "8b" in model_to_use else 120.0
            
            request_payload = {
                "model": model_to_use,
                "prompt": prompt,
                "stream": False
            }
            if max_tokens:
                request_payload["options"] = {"num_predict": max_tokens}
            
            if not use_guardrail_model:
                with phoenix_span("llm.generate", {
                    SpanAttributes.LLM_MODEL_NAME: model_to_use,
                    "custom.use_guardrail_model": str(use_guardrail_model),
                    "custom.max_tokens": str(max_tokens) if max_tokens else "None",
                    "custom.base_url": self.base_url
                }) as span:
                    input_messages = [{"role": "user", "content": prompt}]
                    span.set_attribute(SpanAttributes.LLM_INPUT_MESSAGES, json.dumps(input_messages, ensure_ascii=False))
                    span.set_attribute("llm.input.prompt", prompt)
                    span.set_attribute("llm.input.request", json.dumps(request_payload, ensure_ascii=False))
                    
                    async with httpx.AsyncClient(timeout=timeout_duration) as client:
                        response = await client.post(
                            f"{self.base_url}/api/generate",
                            json=request_payload
                        )
                        response.raise_for_status()
                        data = response.json()
                        result = data.get("response", "")
                        
                        logger.info(f"[OLLAMA] Generation completed. Response length: {len(result)} characters")
                        logger.info(f"[OLLAMA] --- RESPONSE START ---\n{result}\n[OLLAMA] --- RESPONSE END ---")
                        
                        output_messages = [{"role": "assistant", "content": result}]
                        span.set_attribute(SpanAttributes.LLM_OUTPUT_MESSAGES, json.dumps(output_messages, ensure_ascii=False))
                        span.set_attribute("llm.output.response", result)
                        span.set_attribute("llm.output.full", json.dumps(data, ensure_ascii=False))
                        
                        return result
            else:
                async with httpx.AsyncClient(timeout=timeout_duration) as client:
                    response = await client.post(
                        f"{self.base_url}/api/generate",
                        json=request_payload
                    )
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


def create_llm_provider(provider_type: str = "ollama", log_config: bool = True) -> LLMProvider:
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
