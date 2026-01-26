"""Centralized prompt management for the dental chatbot."""
from typing import Dict, List


class PromptManager:
    """Manages all prompts used in the system."""
    
    # Language detection prompt
    LANGUAGE_DETECTION = """Determine the language of the following text. Answer ONLY one word: "vi" for Vietnamese, "en" for English.

Text: "{text}"

Answer:"""
    
    # Guardrail prompts
    GUARDRAIL_EN = """Is this question about DENTISTRY?

DENTISTRY includes: teeth, gums, mouth, dental treatment, orthodontic treatment, braces, aligners, Invisalign, dental implants, finding dental clinics/dentists, dental addresses, oral hygiene, dental procedures.

Question: "{question}"

Answer ONLY one word: "YES" if dental-related, "NO" if not.

Answer:"""
    
    GUARDRAIL_VI = """Câu hỏi có liên quan đến NHA KHOA không?

NHA KHOA bao gồm: răng, nướu, miệng, điều trị nha khoa, chỉnh nha, niềng răng, khay niềng, Invisalign, cấy ghép răng, tìm địa chỉ/phòng khám nha khoa, nha sĩ, vệ sinh răng miệng, thủ thuật nha khoa.

Câu hỏi: "{question}"

Trả lời CHỈ một từ: "YES" nếu liên quan nha khoa, "NO" nếu không.

Trả lời:"""
    
    # Chat response prompts - Optimized for speed and context awareness
    CHAT_RESPONSE_VI = """Bạn là chuyên gia tư vấn nha khoa. Trả lời câu hỏi dựa trên thông tin tìm kiếm VÀ ngữ cảnh cuộc trò chuyện trước đó.

{conversation_summary}

Câu hỏi hiện tại: {user_message}

Thông tin tìm kiếm:
{search_results}

Yêu cầu:
- Trả lời ngắn gọn, chính xác dựa trên thông tin tìm kiếm
- NHẤT QUÁN với ngữ cảnh cuộc trò chuyện trước đó (nếu có summary ở trên)
- Nếu câu hỏi liên quan đến cuộc trò chuyện trước, hãy tham khảo summary để đảm bảo tính nhất quán
- Mỗi đoạn văn cách nhau bằng \\n\\n
- Không thêm nguồn (sẽ tự động thêm)

Trả lời:"""
    
    CHAT_RESPONSE_EN = """You are a dental consultant. Answer the question based on search information AND previous conversation context.

{conversation_summary}

Current question: {user_message}

Search information:
{search_results}

Requirements:
- Answer concisely and accurately based on search information
- BE CONSISTENT with previous conversation context (if summary is provided above)
- If the question relates to previous conversation, reference the summary to ensure consistency
- Separate paragraphs with \\n\\n
- Do not add sources (will be added automatically)

Answer:"""
    
    # Guardrail rejection messages
    REJECTION_VI = """Xin chào! Tôi là trợ lý tư vấn nha khoa. Tôi chỉ có thể trả lời các câu hỏi liên quan đến lĩnh vực nha khoa như:
- Răng, nướu, miệng
- Các bệnh về răng miệng
- Điều trị nha khoa
- Vệ sinh răng miệng
- Các vấn đề nha khoa khác

Vui lòng nhập lại câu hỏi liên quan đến nha khoa để tôi có thể hỗ trợ bạn tốt nhất."""
    
    REJECTION_EN = """Hello! I am a dental consultation assistant. I can only answer questions related to the dental field such as:
- Teeth, gums, mouth
- Dental and oral diseases
- Dental treatments
- Oral hygiene
- Other dental issues

Please re-enter a dental-related question so I can assist you best."""

    # Summarization prompts - Optimized for speed (shorter, more direct)
    SUMMARIZE_RESPONSE_VI = """Tóm tắt ngắn gọn câu trả lời về nha khoa (1-2 câu, chỉ điểm chính):

Câu hỏi: {question}
Câu trả lời: {response}

Tóm tắt:"""

    SUMMARIZE_RESPONSE_EN = """Summarize the dental response briefly (1-2 sentences, key points only):

Question: {question}
Response: {response}

Summary:"""


    @staticmethod
    def get_language_detection_prompt(text: str) -> str:
        """Get language detection prompt."""
        return PromptManager.LANGUAGE_DETECTION.format(text=text)
    
    @staticmethod
    def get_guardrail_prompt(question: str, language: str = "vi") -> str:
        """Get guardrail prompt for the specified language."""
        if language == "vi":
            return PromptManager.GUARDRAIL_VI.format(question=question)
        return PromptManager.GUARDRAIL_EN.format(question=question)
    
    @staticmethod
    def get_chat_response_prompt(
        user_message: str,
        search_results: str,
        conversation_summary: str = "",
        language: str = "vi"
    ) -> str:
        """Get chat response prompt for the specified language."""
        if language == "vi":
            return PromptManager.CHAT_RESPONSE_VI.format(
                user_message=user_message,
                search_results=search_results,
                conversation_summary=conversation_summary
            )
        return PromptManager.CHAT_RESPONSE_EN.format(
            user_message=user_message,
            search_results=search_results,
            conversation_summary=conversation_summary
        )
    
    @staticmethod
    def get_rejection_message(language: str = "vi") -> str:
        """Get guardrail rejection message for the specified language."""
        if language == "vi":
            return PromptManager.REJECTION_VI
        return PromptManager.REJECTION_EN

    @staticmethod
    def get_summarize_response_prompt(question: str, response: str, language: str = "vi") -> str:
        """
        Get prompt to summarize a single response (question + answer pair).
        
        Args:
            question: User question
            response: Assistant response
            language: Language for summary ("vi" or "en")
        """
        if language == "vi":
            return PromptManager.SUMMARIZE_RESPONSE_VI.format(question=question, response=response)
        return PromptManager.SUMMARIZE_RESPONSE_EN.format(question=question, response=response)
