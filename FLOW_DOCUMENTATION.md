# Flow Documentation - Dental Chatbot System

## Tổng quan

Dental Chatbot là một hệ thống AI tư vấn nha khoa sử dụng:
- **Ollama LLMs**: Cho guardrail và chat generation
- **DuckDuckGo Search**: Tìm kiếm thông tin nha khoa
- **MCP (Model Context Protocol)**: Standalone server cho Memory và Tools
- **Memory Compression**: Tự động summarize và compress old messages

## Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Browser)                        │
│  - index.html (Chat UI)                                     │
│  - config.html (Configuration)                              │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/WebSocket
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Main Application (FastAPI)                       │
│  Port: 8000                                                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  routers/openai.py                                    │  │
│  │  - /v1/chat/completions (OpenAI-compatible API)      │  │
│  │  - /v1/conversations/{id} (Get conversation)          │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────────┐  │
│  │  services/chat_service.py                            │  │
│  │  - Orchestrates entire chat flow                      │  │
│  │  - Guardrail → Memory → Search → LLM → Response      │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────────┐  │
│  │  services/guardrail.py                               │  │
│  │  - Checks if question is dental-related              │  │
│  │  - Uses Ollama LLM (small model)                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  services/llm_provider.py                            │  │
│  │  - OllamaProvider (only)                             │  │
│  │  - Handles LLM API calls                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  clients/mcp_client.py                               │  │
│  │  - MCPHost: HTTP client to MCP server               │  │
│  │  - Independent from mcp/ folder                      │  │
│  └──────────────────┬───────────────────────────────────┘  │
└─────────────────────┼───────────────────────────────────────┘
                      │ HTTP (JSON-RPC 2.0)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              MCP Server (Standalone)                        │
│  Port: 8001                                                 │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  mcp/server.py                                       │  │
│  │  - FastAPI application                               │  │
│  │  - JSON-RPC 2.0 endpoint: /jsonrpc                  │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│       ┌─────────────┴─────────────┐                         │
│       ▼                           ▼                         │
│  ┌──────────────┐          ┌──────────────┐                │
│  │ Memory Server│          │ Tool Server  │                │
│  │              │          │              │                │
│  │ - Conversations│         │ - DuckDuckGo │                │
│  │ - Messages    │         │   Search     │                │
│  │ - Summary     │         │              │                │
│  │ - Compression │         │              │                │
│  └──────────────┘          └──────────────┘                │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              External Services                               │
│                                                              │
│  - Ollama (localhost:11434) - LLM inference                 │
│  - DuckDuckGo API - Web search                              │
└─────────────────────────────────────────────────────────────┘
```

## Flow chi tiết khi user nhập câu hỏi

### Step 1: User Input → Frontend

**File**: `static/js/app.js`

1. User nhập câu hỏi vào chat interface
2. Frontend gửi request đến `/v1/chat/completions` với:
   - `model`: `"dental-duckduckgo"`
   - `messages`: `[{"role": "user", "content": "..."}]` (chỉ message mới)
   - `chat_id`: Conversation ID (tạo mới hoặc dùng existing)

**Note**: Frontend chỉ gửi message mới, không gửi full history.

---

### Step 2: API Route Handler

**File**: `routers/openai.py`

1. Nhận request tại `/v1/chat/completions`
2. Extract:
   - `model`: Phải là `"dental-duckduckgo"`
   - `messages`: Array of messages
   - `chat_id`: Conversation ID từ payload
3. Apply user config (nếu có):
   - `ollama_model`: Model cho chat generation
   - `ollama_guardrail_model`: Model cho guardrail
4. Tạo `ChatService` instance với user config
5. Gọi `chat_service.process_chat_completion()`

---

### Step 3: Chat Service - Extract User Message

**File**: `services/chat_service.py` - Step 1

1. Extract user message từ `messages` array (lấy message cuối cùng có `role="user"`)
2. **Detect language** (Step 1.5):
   - Sử dụng `detect_language_llm()` với guardrail LLM
   - Detect "vi" hoặc "en"
   - Reuse language cho guardrail và prompt building

**Log**: `[STEP 1.2] Extracted user message: ...`

---

### Step 4: Guardrail Check

**File**: `services/chat_service.py` - Step 2  
**File**: `services/guardrail.py`

1. **Guardrail check FIRST** (trước khi get context để save resources):
   - Gọi `guardrail.is_dental_related(user_message, user_lang)`
   - Sử dụng Ollama LLM (small model, e.g., `qwen2.5:3b-instruct`)
   - Prompt: "Câu hỏi có liên quan đến NHA KHOA không? Trả lời CHỈ một từ: YES hoặc NO"
   - Parse response: Check "NO" trước "YES" (prioritize rejection)

2. **Nếu REJECTED** (không liên quan nha khoa):
   - Return friendly rejection message (tiếng Việt hoặc tiếng Anh)
   - **KHÔNG lưu vào memory** (chỉ get conversation_id cho response consistency)
   - Log: `[STEP 2.3] Question rejected - NOT saved to memory`
   - **Flow kết thúc tại đây**

3. **Nếu PASSED** (liên quan nha khoa):
   - Continue to Step 5

**Log**: `[STEP 2.1] Guardrail result: PASSED/REJECTED`

---

### Step 5: Get or Create Conversation

**File**: `services/chat_service.py` - Step 3  
**MCP Method**: `memory/get_or_create`

1. Gọi MCP Memory Server:
   ```json
   {
     "method": "memory-server/memory/get_or_create",
     "params": {"conversation_id": "chat_xxx"}
   }
   ```
2. Memory Server:
   - Nếu conversation_id tồn tại → return existing
   - Nếu không → tạo mới conversation_id
3. Return `conversation_id`

**Log**: `[STEP 3.1] Conversation ID: ...`

---

### Step 6: Get Conversation Context

**File**: `services/chat_service.py` - Step 4  
**MCP Method**: `memory/get_context`

1. Gọi MCP Memory Server để get recent messages (cho LLM context):
   ```json
   {
     "method": "memory-server/memory/get_context",
     "params": {"conversation_id": "chat_xxx", "max_messages": 20}
   }
   ```
2. Memory Server:
   - Chỉ trả về **6 messages gần nhất** (KEEP_RECENT_MESSAGES = 6)
   - Old messages đã được summarize (nhưng full history vẫn được lưu)
   - Full history có thể lấy qua `memory/get_all_messages` (cho display)
3. Return `messages` array (chỉ recent messages, không phải full history)

**Log**: `[STEP 4.1] Retrieved {n} messages from memory`

**Note**: Full history luôn được lưu để hiển thị. `get_context()` chỉ trả về recent messages để giảm context size cho LLM.

---

### Step 7: Get Old Messages for Summary

**File**: `services/chat_service.py` - Step 4.2  
**MCP Method**: `memory/get_old_messages`

1. Gọi MCP Memory Server để get old messages:
   ```json
   {
     "method": "memory-server/memory/get_old_messages",
     "params": {"conversation_id": "chat_xxx"}
   }
   ```
2. Memory Server:
   - Trả về messages **trước 6 messages gần nhất**
   - Nếu đã compress → trả về empty array
   - Return `total_count`: Tổng số messages (bao gồm cả old và recent)
3. Return `old_messages` và `total_count`

**Note**: Old messages chỉ tồn tại nếu chưa được summarize/compress.

---

### Step 8: Build Context

**File**: `services/chat_service.py` - Step 5

1. Combine:
   - `memory_context`: 6 recent messages từ Step 6
   - `user_message`: Message mới từ user
2. Build `all_messages` array:
   ```python
   all_messages = memory_context.copy()
   all_messages.append({"role": "user", "content": user_message})
   ```

**Log**: `[STEP 5.1] Context built. Total messages in context: {n}`

---

### Step 9: Call Search Tool

**File**: `services/chat_service.py` - Step 6  
**MCP Method**: `tools/call`  
**Tool**: `duckduckgo_search`

1. **Code-driven tool selection**: Tool được chọn bởi code, không phải LLM
   ```python
   tool_name = "duckduckgo_search"  # Always DuckDuckGo
   ```

2. Gọi MCP Tool Server:
   ```json
   {
     "method": "tool-server/tools/call",
     "params": {
       "name": "duckduckgo_search",
       "arguments": {"query": user_message}
     }
   }
   ```

3. Tool Server:
   - Execute `DuckDuckGoSearchTool.search(query)`
   - Search DuckDuckGo API
   - Format results: Title, Content, Link (up to 5 results)
   - Return formatted text

4. Return `search_results` (formatted text)

**Log**: `[STEP 6.1] Search completed. Results length: {n} characters`

---

### Step 10: Get and Use Conversation Summary

**File**: `services/chat_service.py` - Step 4, Step 7.2

#### Step 10.1: Get Existing Summary

**MCP Method**: `memory/get_summary`

1. Gọi MCP Memory Server để lấy summary hiện có:
   ```json
   {
     "method": "memory-server/memory/get_summary",
     "params": {
       "conversation_id": "chat_xxx"
     }
   }
   ```
2. Memory Server:
   - Trả về summary nếu tồn tại (accumulated summary của tất cả previous responses)
   - Trả về empty string nếu chưa có (first question)

**Log**: `[STEP 4.1] Found existing summary: ...` hoặc `[STEP 4.1] No existing summary (first question in conversation)`

#### Step 10.2: Build Summary Text for Prompt

1. **Nếu có summary**:
   - Format: `"\n\nTóm tắt cuộc trò chuyện trước:\n{summary}\n"`
   - Summary này chứa tất cả các câu trả lời trước đó đã được summarize

2. **Nếu không có summary**:
   - `conversation_summary = ""` (empty, first question)

3. Result: `conversation_summary` string (chỉ summary, không có recent messages)

**Log**: `[STEP 7.2] Using existing summary as context. Summary length: {n} characters`

**Note**: 
- Summary là một biến duy nhất, được update sau mỗi response
- Summary chứa tất cả các câu trả lời trước đó đã được summarize
- Prompt chỉ dùng summary (không dùng recent messages)

---

### Step 11: Build Prompt

**File**: `services/chat_service.py` - Step 7  
**File**: `services/prompts.py`

1. Build prompt với:
   - **System prompt**: Role definition (chuyên gia tư vấn nha khoa)
   - **Conversation summary**: Summary + recent messages (từ Step 10)
   - **Current question**: User message
   - **Search results**: Results từ Step 9
   - **Format instructions**: Hướng dẫn format response (paragraphs, spacing, etc.)

2. Language-aware:
   - Tiếng Việt: `PromptManager.get_chat_prompt_vi(...)`
   - Tiếng Anh: `PromptManager.get_chat_prompt_en(...)`

3. Result: Full prompt string

**Log**: `[STEP 7.4] Prompt built. Length: {n} characters`

---

### Step 12: Generate Response with LLM

**File**: `services/chat_service.py` - Step 8  
**File**: `services/llm_provider.py`

1. Gọi Ollama LLM:
   ```python
   raw_response = await self.llm.generate(prompt)
   ```
   - Model: `qwen2.5:7b-instruct` (hoặc user config)
   - Timeout: 180 seconds (for larger models)

2. LLM Provider:
   - POST to `http://localhost:11434/api/generate`
   - Stream response
   - Return full text

3. Log prompt và response với separators:
   - `--- PROMPT START ---` / `--- PROMPT END ---`
   - `--- RESPONSE START ---` / `--- RESPONSE END ---`

**Log**: `[STEP 8] Generating response with LLM provider: ollama`

---

### Step 13: Format Response

**File**: `services/chat_service.py` - Step 8.1

1. Extract sources từ search results:
   - Parse "Link: ..." patterns
   - Clean markdown link formats
   - Build sources list

2. Format response:
   - Add sources section: `"\n\nNguồn tham khảo:\n\n1. Title\n2. Title\n..."`
   - Clean formatting

3. Log formatted response:
   - `--- FORMATTED RESPONSE START ---` / `--- FORMATTED RESPONSE END ---`

**Log**: `[STEP 8.2] Formatted response. Sources: {n}`

---

### Step 14: Save to Memory and Update Summary

**File**: `services/chat_service.py` - Step 9  
**MCP Method**: `memory/add_message`, `memory/set_summary`

1. **Save user message**:
   ```json
   {
     "method": "memory-server/memory/add_message",
     "params": {
       "conversation_id": "chat_xxx",
       "role": "user",
       "content": user_message
     }
   }
   ```

2. **Save assistant response**:
   ```json
   {
     "method": "memory-server/memory/add_message",
     "params": {
       "conversation_id": "chat_xxx",
       "role": "assistant",
       "content": formatted_response
     }
   }
   ```

3. **Summarize new response and update summary**:
   - Tạo summarize prompt: `PromptManager.get_summarize_response_prompt(question, response, language)`
   - Gọi LLM để summarize response mới
   - Update summary: `updated_summary = existing_summary + "\n\n" + new_response_summary`
   - Save updated summary:
     ```json
     {
       "method": "memory-server/memory/set_summary",
       "params": {
         "conversation_id": "chat_xxx",
         "summary": updated_summary,
         "compress": false
       }
     }
     ```

4. Memory Server:
   - Add messages to conversation (full history)
   - Update summary (accumulated summary of all responses)

**Log**: `[STEP 9.4] Summary updated. New summary length: {n} characters`

**Note**: 
- Summary được update sau mỗi response
- Summary là accumulated summary của tất cả previous responses
- Summary này sẽ được dùng làm context cho câu hỏi tiếp theo

---

### Step 15: Return Response

**File**: `services/chat_service.py` - Return

1. Return:
   - `formatted_response`: Response text với sources
   - `conversation_id`: Conversation ID

2. API Route:
   - Format OpenAI-compatible response
   - Return to frontend

3. Frontend:
   - Display response
   - Update chat UI

---

## Summary Accumulation Flow

### Strategy

**Single Summary Variable**: Một biến summary duy nhất được dùng để lưu tất cả các câu trả lời đã được summarize.

### Flow

```
Câu hỏi 1:
  - Get summary: "" (empty, first question)
  - Prompt: không có summary
  - Response 1
  - Summarize Response 1 → "Summary 1"
  - Save summary = "Summary 1"

Câu hỏi 2:
  - Get summary: "Summary 1"
  - Prompt: dùng "Summary 1" làm context
  - Response 2
  - Summarize Response 2 → "Summary 2"
  - Update summary = "Summary 1\n\nSummary 2"
  - Save summary

Câu hỏi 3:
  - Get summary: "Summary 1\n\nSummary 2"
  - Prompt: dùng summary trên làm context
  - Response 3
  - Summarize Response 3 → "Summary 3"
  - Update summary = "Summary 1\n\nSummary 2\n\nSummary 3"
  - Save summary
```

### Lợi ích

- **Giảm context size**: Chỉ dùng summary (ngắn gọn) thay vì full history
- **Giữ ngữ cảnh**: Summary chứa thông tin quan trọng từ tất cả previous responses
- **Tự động**: Summary được update sau mỗi response
- **Đơn giản**: Chỉ 1 biến summary duy nhất, không cần compression logic phức tạp
- **Full history**: Full history vẫn được lưu để hiển thị (via `get_all_messages()`)

### Configuration

**File**: `services/memory.py`

```python
KEEP_RECENT_MESSAGES = 6  # Số messages gần nhất giữ lại (full)
SUMMARIZE_THRESHOLD = 10  # Ngưỡng bắt đầu summarize
COMPRESS_AFTER_SUMMARY = True  # Xóa old messages sau summarize
```

---

## MCP Communication

### Protocol

- **Protocol**: JSON-RPC 2.0
- **Transport**: HTTP
- **Endpoint**: `POST /jsonrpc`

### Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "{server_name}/{method_name}",
  "params": {...},
  "id": 1
}
```

### Response Format

```json
{
  "jsonrpc": "2.0",
  "result": {...},
  "id": 1
}
```

### Error Format

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32602,
    "message": "Invalid params"
  },
  "id": 1
}
```

### Client Implementation

**File**: `clients/mcp_client.py`

- `MCPHost`: HTTP client để giao tiếp với MCP server
- `call_method()`: Gọi MCP method qua HTTP
- **Independent**: Không import từ `mcp/` folder

---

## Tool Selection (Code-Driven)

### Current Implementation

- **Tool selection**: Do code quyết định, không phải LLM
- **Always DuckDuckGo**: `tool_name = "duckduckgo_search"`
- **Predictable**: Tool luôn được chọn trước khi gọi

### Future Extension

Có thể mở rộng để LLM chọn tool, nhưng hiện tại là code-driven để đảm bảo:
- Reliability
- Predictability
- Performance

---

## Error Handling

### Guardrail Rejection

- **Action**: Return friendly message, không lưu vào memory
- **Flow**: Kết thúc tại Step 4

### Search Tool Error

- **Action**: Raise exception, không có fallback
- **Flow**: Error được propagate lên API route

### LLM Error

- **Action**: Raise exception
- **Flow**: Error được propagate lên API route

### Memory Error

- **Action**: Log error, continue without memory (nếu có thể)
- **Flow**: Continue với empty context

---

## Logging

### Log Levels

- **INFO**: Flow steps, important events
- **DEBUG**: Detailed context information
- **WARNING**: Non-critical issues
- **ERROR**: Errors with stack traces

### Log Format

```
[STEP X] Description
[STEP X.Y] Sub-step description
```

### Separators

- Prompt/Response logs có separators để dễ đọc:
  - `--- PROMPT START ---` / `--- PROMPT END ---`
  - `--- RESPONSE START ---` / `--- RESPONSE END ---`
  - `--- FORMATTED RESPONSE START ---` / `--- FORMATTED RESPONSE END ---`

---

## Configuration

### User Config (Frontend)

- `ollama_model`: Model cho chat generation
- `ollama_guardrail_model`: Model cho guardrail
- Stored in `localStorage`
- Applied per request

### Environment Variables

- `OLLAMA_BASE_URL`: Ollama server URL (default: `http://localhost:11434`)
- `MCP_SERVER_URL`: MCP server URL (default: `http://localhost:8001`)

---

## Performance Considerations

### Memory Compression

- **Reduces context size**: Chỉ 6 messages + summary thay vì tất cả
- **Faster LLM inference**: Smaller prompts = faster generation
- **Less storage**: Old messages được xóa sau summarize

### Guardrail First

- **Save resources**: Check guardrail trước khi get context
- **Early rejection**: Reject non-dental questions immediately

### Language Detection

- **Reuse**: Detect language một lần, reuse cho guardrail và prompt
- **Efficient**: Không detect nhiều lần

---

## Testing Flow

### Test Guardrail

1. Send non-dental question → Should reject
2. Send dental question → Should pass

### Test Memory Compression

1. Create conversation
2. Add 8 messages (4 user + 4 assistant)
3. Get context → Should return only 6 recent
4. Get old messages → Should return 2 old messages
5. Create summary → Old messages should be deleted
6. Get context again → Should return only 6 recent (old ones deleted)

### Test Search Tool

1. Send dental question
2. Verify search results in logs
3. Verify sources in response

### Test Full Flow

1. Send dental question
2. Verify all steps in logs
3. Verify response format
4. Verify memory saved

---

## Summary

Flow chính khi user nhập câu hỏi:

1. **Frontend** → Send request với user message
2. **API Route** → Handle request, apply config
3. **Chat Service** → Extract message, detect language
4. **Guardrail** → Check dental-related (reject nếu không)
5. **Memory** → Get/create conversation, get context
6. **Search** → Call DuckDuckGo tool (code-driven)
7. **Compression** → Get/create summary, compress old messages
8. **Prompt** → Build prompt với context + search results
9. **LLM** → Generate response
10. **Format** → Format response với sources
11. **Memory** → Save user message + assistant response
12. **Return** → Return formatted response

**Key Features**:
- Guardrail first (save resources)
- Memory compression (reduce storage & context)
- Code-driven tool selection (reliable)
- Standalone MCP server (independent)
- Language-aware (vi/en)
