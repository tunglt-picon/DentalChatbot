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

DENTISTRY includes: teeth, gums, mouth, dental treatment, finding dental clinics/dentists, dental addresses.

Question: "{question}"

Answer ONLY one word: "YES" if dental-related, "NO" if not.

Answer:"""
    
    GUARDRAIL_VI = """Câu hỏi có liên quan đến NHA KHOA không?

NHA KHOA bao gồm: răng, nướu, miệng, điều trị nha khoa, tìm địa chỉ/phòng khám nha khoa, nha sĩ.

Câu hỏi: "{question}"

Trả lời CHỈ một từ: "YES" nếu liên quan nha khoa, "NO" nếu không.

Trả lời:"""
    
    # Chat response prompts
    CHAT_RESPONSE_VI = """Bạn là một chuyên gia tư vấn nha khoa chuyên nghiệp với kiến thức sâu rộng. 
Nhiệm vụ của bạn là trả lời câu hỏi của bệnh nhân dựa trên thông tin tìm kiếm và ngữ cảnh cuộc trò chuyện.

{conversation_summary}

Câu hỏi hiện tại của bệnh nhân: {user_message}

Thông tin tìm kiếm:
{search_results}

Vui lòng trả lời câu hỏi một cách:
- Chính xác và dựa trên thông tin tìm kiếm
- Nhất quán với ngữ cảnh cuộc trò chuyện trước đó (nếu có)
- Dễ hiểu và thân thiện
- Format đẹp với các đoạn văn rõ ràng, dễ đọc

QUAN TRỌNG VỀ FORMAT: 
- Mỗi đoạn văn phải được phân tách bằng HAI dấu xuống dòng (\\n\\n)
- Mỗi đoạn văn nên là một ý tưởng hoàn chỉnh, độc lập
- Sau mỗi câu kết thúc bằng dấu chấm (.), chấm hỏi (?), hoặc chấm than (!), nếu bắt đầu đoạn văn mới thì phải có HAI dấu xuống dòng
- Các mục trong danh sách (1., 2., 3., hoặc -, *) phải cách nhau bằng hai dấu xuống dòng nếu là các ý tưởng riêng biệt
- Không cần thêm dẫn chứng nguồn trong phần trả lời chính (sẽ được thêm tự động sau)

Trả lời:"""
    
    CHAT_RESPONSE_EN = """You are a professional dental consultant with extensive knowledge. 
Your task is to answer the patient's question based on the search information and conversation context.

{conversation_summary}

Current patient's question: {user_message}

Search information:
{search_results}

Please answer the question in a way that is:
- Accurate and based on search information
- Consistent with previous conversation context (if any)
- Easy to understand and friendly
- Well-formatted with clear, readable paragraphs

IMPORTANT FORMATTING:
- Each paragraph MUST be separated by TWO newlines (\\n\\n)
- Each paragraph should be a complete, independent idea
- After each sentence ending with period (.), question mark (?), or exclamation (!), if starting a new paragraph, add TWO newlines
- List items (1., 2., 3., or -, *) must be separated by two newlines if they are separate ideas
- Do not include source citations in the main answer (they will be added automatically)

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

    # Summarization prompts - for summarizing a single response
    SUMMARIZE_RESPONSE_VI = """Hãy tóm tắt câu trả lời sau đây về nha khoa thành một đoạn văn ngắn. Tóm tắt phải:
    - Ngắn gọn, chỉ nêu các điểm chính
    - Giữ lại thông tin quan trọng
    - Không quá 2-3 câu
    - Bằng tiếng Việt

    Câu hỏi: {question}
    Câu trả lời: {response}

    Tóm tắt:"""

    SUMMARIZE_RESPONSE_EN = """Please summarize the following dental response into a short paragraph. Summary must:
    - Be concise, only mention key points
    - Retain important information
    - Not exceed 2-3 sentences
    - Be in English

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
