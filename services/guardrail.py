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
    """Detect language from text using LLM (Vietnamese or English)."""
    logger.debug(f"[GUARDRAIL-LANG] Detecting language using LLM for text: {text[:100]}...")
    
    try:
        prompt = PromptManager.get_language_detection_prompt(text)
        response = await llm_provider.generate(prompt)
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
        """
        Check if question is related to dentistry.
        
        Args:
            question: Question to check
            user_lang: Optional pre-detected language ("vi" or "en"). If None, will detect.
            
        Returns:
            Tuple of (is_dental_related: bool, user_lang: str)
        """
        logger.debug(f"[GUARDRAIL] Checking question: {question[:100]}...")
        logger.debug(f"[GUARDRAIL] Using provider: {config.settings.guardrail_provider}")
        
        try:
            # Detect language if not provided
            if user_lang is None:
                user_lang = await detect_language_llm(question, self.llm)
                logger.debug(f"[GUARDRAIL] Detected language: {user_lang}")
            else:
                logger.debug(f"[GUARDRAIL] Using provided language: {user_lang}")
            
            prompt = PromptManager.get_guardrail_prompt(question, user_lang)
            logger.debug(f"[GUARDRAIL] Prompt built, length: {len(prompt)} characters")
            
            # Use guardrail model if supported
            from services.llm_provider import OllamaProvider
            if isinstance(self.llm, OllamaProvider):
                logger.debug(f"[GUARDRAIL] Using guardrail-specific model")
                response = await self.llm.generate(prompt, use_guardrail_model=True)
            else:
                logger.debug(f"[GUARDRAIL] Using standard model")
                response = await self.llm.generate(prompt)
            
            # Note: Prompt and response are already logged by llm_provider.generate()
            # No need to log again here to avoid duplicate logs
            logger.debug(f"[GUARDRAIL] Raw response: {response}")
            logger.debug(f"[GUARDRAIL] Full response length: {len(response)} characters")
            
            # Extract first word/line from response and normalize
            first_line = response.strip().split('\n')[0].strip().upper()
            first_word = first_line.split()[0] if first_line.split() else ""
            
            # Check for NO first (more restrictive, safer)
            if first_word == "NO" or first_line.startswith("NO"):
                logger.info(f"[GUARDRAIL] Result: NO - Question is NOT dental-related")
                return False, user_lang
            elif "NO" in first_line or "KHÔNG" in first_line:
                logger.info(f"[GUARDRAIL] Result: NO/KHÔNG (fallback) - Question is NOT dental-related")
                return False, user_lang
            # Then check for YES
            elif first_word == "YES" or first_line.startswith("YES"):
                logger.info(f"[GUARDRAIL] Result: YES - Question is dental-related")
                return True, user_lang
            elif "YES" in first_line or "CÓ" in first_line:
                logger.info(f"[GUARDRAIL] Result: YES/CÓ (fallback) - Question is dental-related")
                return True, user_lang
            else:
                # If unclear, default to reject (safe)
                logger.warning(
                    f"[GUARDRAIL] Unclear result: '{first_line}'. "
                    f"Expected 'YES' or 'NO' but got: '{response[:100]}...'. "
                    f"Rejecting question: {question}"
                )
                return False, user_lang
                
        except Exception as e:
            logger.error(f"[GUARDRAIL] Error checking guardrail: {e}", exc_info=True)
            # If error occurs, default to reject (safe)
            logger.warning(f"[GUARDRAIL] Defaulting to REJECT due to error")
            # Try to detect language for fallback
            if user_lang is None:
                try:
                    user_lang = await detect_language_llm(question, self.llm)
                except:
                    user_lang = "vi"  # Default fallback
            return False, user_lang
