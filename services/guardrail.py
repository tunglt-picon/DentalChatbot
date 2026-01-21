"""Guardrail service to check if question is related to dentistry."""
import logging
import re
import config
from services.llm_provider import create_llm_provider

logger = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    """
    Detect language from text (Vietnamese or English).
    
    Args:
        text: Input text
        
    Returns:
        "vi" for Vietnamese, "en" for English
    """
    # Vietnamese characters (with diacritics)
    vietnamese_pattern = re.compile(
        r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]',
        re.IGNORECASE
    )
    
    # Common Vietnamese words
    vietnamese_words = [
        'là', 'và', 'của', 'cho', 'với', 'từ', 'được', 'trong', 'này', 'đó',
        'có', 'không', 'một', 'như', 'về', 'nếu', 'khi', 'sẽ', 'đã', 'đang',
        'tôi', 'bạn', 'chúng', 'họ', 'nó', 'các', 'những', 'nhiều', 'ít',
        'răng', 'nướu', 'miệng', 'nha khoa', 'điều trị', 'bệnh', 'sức khỏe'
    ]
    
    # Check for Vietnamese characters
    if vietnamese_pattern.search(text):
        return "vi"
    
    # Check for Vietnamese words (case insensitive)
    text_lower = text.lower()
    vietnamese_word_count = sum(1 for word in vietnamese_words if word in text_lower)
    
    # If more than 2 Vietnamese words found, likely Vietnamese
    if vietnamese_word_count >= 2:
        return "vi"
    
    # Check text length - if very short and no Vietnamese indicators, might be English
    # But if longer and has Vietnamese words, it's Vietnamese
    if vietnamese_word_count > 0:
        return "vi"
    
    # Default to English
    return "en"


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

Question: "{question}"

Answer ONLY one word: "YES" if the question is related to dentistry, "NO" if not.

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

Câu hỏi: "{question}"

Trả lời CHỈ một từ: "YES" nếu câu hỏi liên quan đến nha khoa, "NO" nếu không.

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
            # Detect language and use appropriate prompt template
            user_lang = detect_language(question)
            logger.debug(f"[GUARDRAIL] Detected language: {user_lang}")
            
            if user_lang == "vi":
                prompt = self.prompt_template_vi.format(question=question)
            else:
                prompt = self.prompt_template_en.format(question=question)
            logger.debug(f"[GUARDRAIL] Prompt built, length: {len(prompt)} characters")
            
            # Use guardrail model if supported
            from services.llm_provider import OllamaProvider, GeminiProvider
            if isinstance(self.llm, (OllamaProvider, GeminiProvider)):
                logger.debug(f"[GUARDRAIL] Using guardrail-specific model")
                response = await self.llm.generate(prompt, use_guardrail_model=True)
            else:
                logger.debug(f"[GUARDRAIL] Using standard model")
                response = await self.llm.generate(prompt)
            
            logger.debug(f"[GUARDRAIL] Raw response: {response[:100]}...")
            result = response.strip().upper()
            
            # Handle response that may have additional text
            if "YES" in result:
                logger.info(f"[GUARDRAIL] Result: YES - Question is dental-related")
                return True
            elif "NO" in result:
                logger.info(f"[GUARDRAIL] Result: NO - Question is NOT dental-related")
                return False
            else:
                # If unclear, default to reject (safe)
                logger.warning(
                    f"[GUARDRAIL] Unclear result: {result}. "
                    f"Rejecting question: {question}"
                )
                return False
                
        except Exception as e:
            logger.error(f"[GUARDRAIL] Error checking guardrail: {e}", exc_info=True)
            # If error occurs, default to reject (safe)
            logger.warning(f"[GUARDRAIL] Defaulting to REJECT due to error")
            return False
