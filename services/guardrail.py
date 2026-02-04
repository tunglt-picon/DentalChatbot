"""Guardrail service to check if question is related to dentistry."""
import logging
import re
from typing import Optional, Tuple
import config
from services.llm_provider import create_llm_provider
from services.prompts import PromptManager

logger = logging.getLogger(__name__)

VIETNAMESE_PATTERN = re.compile(
    r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]',
    re.IGNORECASE
)


async def detect_language_llm(text: str, llm_provider) -> str:
    logger.debug(f"[GUARDRAIL-LANG] Detecting language using LLM for text: {text[:100]}...")
    
    try:
        from services.phoenix_tracing import phoenix_span
        from openinference.semconv.trace import SpanAttributes
        import json
        import config
        
        prompt = PromptManager.get_language_detection_prompt(text)
        
        with phoenix_span("llm.guardrail.detection_language") as span:
            span.set_attribute(SpanAttributes.LLM_MODEL_NAME, config.settings.ollama_guardrail_model)
            span.set_attribute("language.input.text", text)
            
            input_messages = [{"role": "user", "content": prompt}]
            span.set_attribute(SpanAttributes.LLM_INPUT_MESSAGES, json.dumps(input_messages, ensure_ascii=False))
            span.set_attribute("language.input.prompt", prompt)
            
            response = await llm_provider.generate(prompt, use_guardrail_model=True, max_tokens=10)
            
            output_messages = [{"role": "assistant", "content": response}]
            span.set_attribute(SpanAttributes.LLM_OUTPUT_MESSAGES, json.dumps(output_messages, ensure_ascii=False))
            span.set_attribute("language.output.response", response)
            span.set_attribute("language.output.detected", response.strip().lower())
        result = response.strip().lower()
        
        if "vi" in result or "vietnamese" in result.lower():
            logger.info(f"[GUARDRAIL-LANG] LLM detected: Vietnamese")
            return "vi"
        elif "en" in result or "english" in result.lower():
            logger.info(f"[GUARDRAIL-LANG] LLM detected: English")
            return "en"
        else:
            # Fallback: check for Vietnamese characters
            if VIETNAMESE_PATTERN.search(text):
                logger.warning(f"[GUARDRAIL-LANG] LLM result unclear ({result}), fallback to Vietnamese")
                return "vi"
            logger.warning(f"[GUARDRAIL-LANG] LLM result unclear ({result}), fallback to English")
            return "en"
    except Exception as e:
        logger.error(f"[GUARDRAIL-LANG] Error detecting language with LLM: {e}, using fallback")
        return "vi" if VIETNAMESE_PATTERN.search(text) else "en"


class GuardrailService:
    """Service to check if question is related to dentistry."""
    
    def __init__(self):
        """Initialize GuardrailService with configured LLM provider."""
        guardrail_provider = config.settings.guardrail_provider
        self.llm = create_llm_provider(guardrail_provider)
    
    async def is_dental_related(self, question: str, user_lang: Optional[str] = None) -> Tuple[bool, str]:
        logger.debug(f"[GUARDRAIL] Checking question: {question[:100]}...")
        
        try:
            if user_lang is None:
                user_lang = await detect_language_llm(question, self.llm)
            else:
                logger.debug(f"[GUARDRAIL] Using provided language: {user_lang}")
            
            prompt = PromptManager.get_guardrail_prompt(question, user_lang)
            
            from services.llm_provider import OllamaProvider
            from services.phoenix_tracing import phoenix_span
            from openinference.semconv.trace import SpanAttributes
            import json
            import config
            
            with phoenix_span("llm.guardrail.check_dental") as span:
                span.set_attribute(SpanAttributes.LLM_MODEL_NAME, config.settings.ollama_guardrail_model)
                span.set_attribute("guardrail.input.question", question)
                span.set_attribute("guardrail.input.user_lang", user_lang)
                
                input_messages = [{"role": "user", "content": prompt}]
                span.set_attribute(SpanAttributes.LLM_INPUT_MESSAGES, json.dumps(input_messages, ensure_ascii=False))
                span.set_attribute("guardrail.input.prompt", prompt)
                
                if isinstance(self.llm, OllamaProvider):
                    response = await self.llm.generate(prompt, use_guardrail_model=True)
                else:
                    response = await self.llm.generate(prompt)
                
                output_messages = [{"role": "assistant", "content": response}]
                span.set_attribute(SpanAttributes.LLM_OUTPUT_MESSAGES, json.dumps(output_messages, ensure_ascii=False))
                span.set_attribute("guardrail.output.response", response)
                span.set_attribute("guardrail.output.is_dental_related", str(response.strip().upper().startswith("YES")))
                span.set_attribute("guardrail.output.result", "PASSED" if response.strip().upper().startswith("YES") else "REJECTED")
            
            # Extract first word/line from response and normalize
            first_line = response.strip().split('\n')[0].strip().upper()
            first_word = first_line.split()[0] if first_line.split() else ""
            
            if first_word == "NO" or first_line.startswith("NO"):
                logger.info(f"[GUARDRAIL] Result: NO - Question is NOT dental-related")
                return False, user_lang, response
            elif "NO" in first_line or "KHÔNG" in first_line:
                logger.info(f"[GUARDRAIL] Result: NO/KHÔNG (fallback) - Question is NOT dental-related")
                return False, user_lang, response
            elif first_word == "YES" or first_line.startswith("YES"):
                logger.info(f"[GUARDRAIL] Result: YES - Question is dental-related")
                return True, user_lang, response
            elif "YES" in first_line or "CÓ" in first_line:
                logger.info(f"[GUARDRAIL] Result: YES/CÓ (fallback) - Question is dental-related")
                return True, user_lang, response
            else:
                logger.warning(
                    f"[GUARDRAIL] Unclear result: '{first_line}'. "
                    f"Expected 'YES' or 'NO' but got: '{response[:100]}...'. "
                    f"Rejecting question: {question}"
                )
                return False, user_lang, response
                
        except Exception as e:
            logger.error(f"[GUARDRAIL] Error checking guardrail: {e}", exc_info=True)
            logger.warning(f"[GUARDRAIL] Defaulting to REJECT due to error")
            if user_lang is None:
                try:
                    user_lang = await detect_language_llm(question, self.llm)
                except:
                    user_lang = "vi"
            return False, user_lang, ""
