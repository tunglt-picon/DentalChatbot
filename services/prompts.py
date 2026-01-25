"""Centralized prompt management for the dental chatbot."""
from typing import Dict


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

VÍ DỤ FORMAT ĐÚNG (về nha khoa):
Sâu răng là một vấn đề phổ biến ở mọi lứa tuổi. Nguyên nhân chính là do vi khuẩn trong miệng tạo ra axit từ đường và tinh bột, làm mòn men răng theo thời gian.

Để phòng ngừa sâu răng, bạn nên đánh răng ít nhất 2 lần mỗi ngày với kem đánh răng có fluoride. Ngoài ra, hạn chế ăn đồ ngọt và uống nhiều nước cũng rất quan trọng để giữ cho miệng sạch sẽ.

Nếu bạn đã bị sâu răng, nha sĩ sẽ tiến hành trám răng để ngăn chặn sâu răng lan rộng. Quá trình này thường không đau và có thể hoàn thành trong một lần hẹn.

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

EXAMPLE OF CORRECT FORMAT (dental-related):
Tooth decay is a common problem at all ages. The main cause is bacteria in the mouth producing acid from sugar and starch, which erodes tooth enamel over time.

To prevent tooth decay, you should brush your teeth at least twice daily with fluoride toothpaste. Additionally, limiting sugary foods and drinking plenty of water is also very important to keep your mouth clean.

If you already have tooth decay, your dentist will perform a filling to prevent the decay from spreading. This process is usually painless and can be completed in one appointment.

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
