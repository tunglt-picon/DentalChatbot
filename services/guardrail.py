"""Guardrail service to check if question is related to dentistry."""
import logging
import re
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
        # Use guardrail_provider
        guardrail_provider = config.settings.guardrail_provider
        self.llm = create_llm_provider(guardrail_provider)
        
        # Prompt templates for different languages
        self.prompt_template_en = """
You are a question moderation system. Your task is to determine if a question belongs to the DENTAL (dentistry) field.

The DENTAL field includes:
- Teeth, gums, mouth
- Dental and oral diseases
- Dental treatments (fillings, extractions, braces, dental implants...)
- Oral hygiene
- Orthodontics
- Dental surgery
- Cosmetic dentistry
- Issues like cavities, gingivitis, bad breath...
- Addresses and dental examination facilities, dental clinics, dentists
- Finding dentists, dental clinic addresses, dental offices

Question: "{question}"

IMPORTANT: Answer ONLY one word: "YES" if the question is related to dentistry, "NO" if not.

Answer:
"""
        
        self.prompt_template_vi = """
Bạn là hệ thống kiểm duyệt câu hỏi. Nhiệm vụ của bạn là xác định xem một câu hỏi có thuộc lĩnh vực NHA KHOA (dentistry) hay không.

Lĩnh vực NHA KHOA bao gồm:
- Răng, nướu, miệng
- Các bệnh về răng miệng
- Điều trị nha khoa (trám răng, nhổ răng, niềng răng, cấy ghép răng...)
- Vệ sinh răng miệng
- Chỉnh nha
- Phẫu thuật nha khoa
- Thẩm mỹ nha khoa
- Các vấn đề như sâu răng, viêm nướu, hôi miệng...
- Các địa chỉ, cơ sở khám răng, phòng khám nha khoa, nha sĩ
- Tìm kiếm nha sĩ, địa chỉ nha khoa, phòng khám răng

Câu hỏi: "{question}"

QUAN TRỌNG: Trả lời CHỈ một từ bằng tiếng Anh: "YES" nếu câu hỏi liên quan đến nha khoa, "NO" nếu không.
KHÔNG trả lời bằng tiếng Việt (CÓ/KHÔNG). CHỈ trả lời "YES" hoặc "NO".

Trả lời:
"""
    
    async def is_dental_related(self, question: str) -> bool:
        """
        Check if question is related to dentistry.
        
        Args:
            question: Question to check
            
        Returns:
            True if related to dentistry, False otherwise
        """
        logger.debug(f"[GUARDRAIL] Checking question: {question[:100]}...")
        logger.debug(f"[GUARDRAIL] Using provider: {config.settings.guardrail_provider}")
        
        try:
            # Detect language and get prompt from PromptManager
            user_lang = await detect_language_llm(question, self.llm)
            logger.debug(f"[GUARDRAIL] Detected language: {user_lang}")
            
            prompt = PromptManager.get_guardrail_prompt(question, user_lang)
            logger.debug(f"[GUARDRAIL] Prompt built, length: {len(prompt)} characters")
            
            # Use guardrail model if supported
            from services.llm_provider import OllamaProvider, GeminiProvider
            if isinstance(self.llm, (OllamaProvider, GeminiProvider)):
                logger.debug(f"[GUARDRAIL] Using guardrail-specific model")
                response = await self.llm.generate(prompt, use_guardrail_model=True)
            else:
                logger.debug(f"[GUARDRAIL] Using standard model")
                response = await self.llm.generate(prompt)
            
            logger.debug(f"[GUARDRAIL] Raw response: {response}")
            logger.debug(f"[GUARDRAIL] Full response length: {len(response)} characters")
            logger.info(f"[GUARDRAIL] Full prompt sent to LLM:\n{prompt}")
            logger.info(f"[GUARDRAIL] Full response from LLM:\n{response}")
            
            result = response.strip().upper()
            
            # Handle response that may have additional text
            # Check for YES/NO in English, or CÓ/KHÔNG in Vietnamese (fallback)
            if "YES" in result or "CÓ" in result:
                logger.info(f"[GUARDRAIL] Result: YES/CÓ - Question is dental-related")
                return True
            elif "NO" in result or "KHÔNG" in result:
                logger.info(f"[GUARDRAIL] Result: NO/KHÔNG - Question is NOT dental-related")
                return False
            else:
                # If unclear, default to reject (safe)
                logger.warning(
                    f"[GUARDRAIL] Unclear result: '{result}'. "
                    f"Expected 'YES' or 'NO' but got: '{response}'. "
                    f"Rejecting question: {question}"
                )
                return False
                
        except Exception as e:
            logger.error(f"[GUARDRAIL] Error checking guardrail: {e}", exc_info=True)
            # If error occurs, default to reject (safe)
            logger.warning(f"[GUARDRAIL] Defaulting to REJECT due to error")
            return False
