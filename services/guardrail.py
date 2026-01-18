"""Guardrail service to check if question is related to dentistry."""
import google.generativeai as genai
import logging
import config

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=config.settings.google_api_key)


class GuardrailService:
    """Service to check if question is related to dentistry."""
    
    def __init__(self):
        """Initialize GuardrailService with Gemini Flash."""
        self.model = genai.GenerativeModel(config.settings.google_base_model)
        self.prompt_template = """
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
    
    async def is_dental_related(self, question: str) -> bool:
        """
        Check if question is related to dentistry.
        
        Args:
            question: Question to check
            
        Returns:
            True if related to dentistry, False otherwise
        """
        try:
            prompt = self.prompt_template.format(question=question)
            response = self.model.generate_content(prompt)
            
            result = response.text.strip().upper()
            
            # Handle response that may have additional text
            if "YES" in result:
                return True
            elif "NO" in result:
                return False
            else:
                # If unclear, default to reject (safe)
                logger.warning(
                    f"Guardrail returned unclear result: {result}. "
                    f"Rejecting question: {question}"
                )
                return False
                
        except Exception as e:
            logger.error(f"Error checking guardrail: {e}")
            # If error occurs, default to reject (safe)
            return False
