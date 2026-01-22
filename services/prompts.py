"""Centralized prompt management for the dental chatbot."""
from typing import Dict


class PromptManager:
    """Manages all prompts used in the system."""
    
    # Language detection prompt
    LANGUAGE_DETECTION = """Determine the language of the following text. Answer ONLY one word: "vi" for Vietnamese, "en" for English.

Text: "{text}"

Answer:"""
    
    # Guardrail prompts
    GUARDRAIL_EN = """You are a question moderation system. Your task is to determine if a question belongs to the DENTAL (dentistry) field.

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

Answer:"""
    
    GUARDRAIL_VI = """Bạn là hệ thống kiểm duyệt câu hỏi. Nhiệm vụ của bạn là xác định xem một câu hỏi có thuộc lĩnh vực NHA KHOA (dentistry) hay không.

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
- Format đẹp với các đoạn văn rõ ràng

QUAN TRỌNG VỀ FORMAT: 
- Mỗi đoạn văn phải được phân tách bằng HAI dấu xuống dòng (\\n\\n)
- Sau mỗi câu kết thúc bằng dấu chấm (.), chấm hỏi (?), hoặc chấm than (!), nếu bắt đầu câu mới thì phải xuống dòng
- Các mục trong danh sách (1., 2., 3., hoặc -, *) phải cách nhau bằng hai dấu xuống dòng
- Mỗi đoạn văn nên là một ý tưởng hoàn chỉnh
- Không cần thêm dẫn chứng nguồn trong phần trả lời chính (sẽ được thêm tự động sau)

VÍ DỤ FORMAT ĐÚNG:
Đoạn văn đầu tiên về chủ đề.

Đoạn văn thứ hai về chủ đề khác.

Đoạn văn thứ ba với thông tin bổ sung.

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
- Well-formatted with clear paragraphs

IMPORTANT FORMATTING:
- Each paragraph MUST be separated by TWO newlines (\\n\\n)
- After each sentence ending with period (.), question mark (?), or exclamation (!), if starting a new sentence, add a line break
- List items (1., 2., 3., or -, *) must be separated by two newlines
- Each paragraph should be a complete idea
- Do not include source citations in the main answer (they will be added automatically)

EXAMPLE OF CORRECT FORMAT:
First paragraph about the topic.

Second paragraph about a different topic.

Third paragraph with additional information.

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
