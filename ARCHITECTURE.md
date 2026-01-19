# Backend Architecture & Flow Documentation

## System Overview

The Dental Chatbot Backend is a FastAPI-based service that implements OpenAI-compatible API with Memory Context Protocol (MCP) for conversation management and dual search strategies (Google Search & DuckDuckGo).

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Open WebUI / Client                      │
│                    (OpenAI-Compatible Request)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ POST /v1/chat/completions
                             │ Headers: X-Conversation-ID (optional)
                             │ Body: {model, messages[]}
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Router Layer                        │
│                      (routers/openai.py)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. Validate Request                                      │  │
│  │ 2. Extract conversation_id from header                   │  │
│  │ 3. Convert Pydantic models to dict                       │  │
│  │ 4. Call ChatService.process_chat()                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Chat Service Layer                            │
│                   (services/chat_service.py)                     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 1: MCP - Memory Context Retrieval                   │  │
│  │  - Get or create conversation from MemoryService         │  │
│  │  - Retrieve conversation history (last N messages)       │  │
│  │  - Merge with incoming messages                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 2: Guardrail Check                                  │  │
│  │  - Extract last user message                             │  │
│  │  - Call GuardrailService.is_dental_related()             │  │
│  │  - Use Gemini Flash to validate domain                   │  │
│  │  - Reject if not dental-related                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 3: Search Tool Selection & Execution                │  │
│  │  - Factory Pattern: Create search tool based on model    │  │
│  │    - "dental-google" → GoogleSearchTool                  │  │
│  │    - "dental-duckduckgo" → DuckDuckGoSearchTool          │  │
│  │  - Fallback: Auto switch to DuckDuckGo if Google fails   │  │
│  │  - Execute search and get results                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 4: LLM Response Generation                          │  │
│  │  - Build prompt with:                                    │  │
│  │    - Conversation context (last 5 messages)              │  │
│  │    - Current user question                               │  │
│  │    - Search results                                      │  │
│  │  - Call Gemini to generate response                      │  │
│  │  - Save user message + assistant response to memory      │  │
│  │  - Return (response_text, conversation_id)               │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Response Formatting                         │
│  - Format as OpenAI-compatible JSON                             │
│  - Include conversation_id in system_fingerprint                │
│  - Return to client                                             │
└─────────────────────────────────────────────────────────────────┘
```

## Detailed Flow

### 1. Request Reception (Router Layer)

**Endpoint**: `POST /v1/chat/completions`

**Input**:
```json
{
  "model": "dental-google",
  "messages": [
    {"role": "user", "content": "What causes tooth decay?"}
  ]
}
```

**Headers**:
- `X-Conversation-ID` (optional): Existing conversation ID for context

**Process**:
1. Validate model name (`dental-google` or `dental-duckduckgo`)
2. Extract `X-Conversation-ID` header (if present)
3. Convert Pydantic request models to Python dicts
4. Call `ChatService.process_chat(messages, model, conversation_id)`

---

### 2. Memory Context Protocol (MCP) - Step 1

**Service**: `MemoryService`

**Actions**:
1. **Get or Create Conversation**:
   - If `conversation_id` provided → Retrieve existing conversation
   - If `conversation_id` is `None` → Create new conversation (UUID generated)
   
2. **Retrieve Conversation History**:
   - Get last N messages from memory (default: 20, configurable)
   - Format: `[{"role": "user|assistant", "content": "..."}, ...]`

3. **Merge Context**:
   - Combine memory context with incoming messages
   - Avoid duplicates by checking last message
   - Result: Full conversation context for LLM

**Memory Structure**:
```python
ConversationMemory:
  - conversation_id: str
  - messages: List[Dict] (with timestamps)
  - created_at: datetime
  - updated_at: datetime
```

---

### 3. Guardrail Check - Step 2

**Service**: `GuardrailService`

**Process**:
1. **Extract User Message**:
   - Find last message with `role == "user"` from merged messages
   
2. **Domain Validation**:
   - Build guardrail prompt (English):
     ```
     "Is this question related to DENTAL field? Answer YES or NO."
     ```
   - Call Gemini Flash (`gemini-2.5-flash`)
   - Parse response: `YES` → Allow, `NO` → Reject
   
3. **Rejection Handling**:
   - If not dental-related → Raise `ValueError`
   - Return HTTP 400 to client

**Guardrail Prompt Example**:
```
You are a question moderation system. 
Determine if question belongs to DENTAL field.

DENTAL field includes:
- Teeth, gums, mouth
- Dental diseases
- Dental treatments
- Oral hygiene
...

Question: "{user_question}"
Answer ONLY: YES or NO
```

---

### 4. Search Tool Selection & Execution - Step 3

**Service**: `SearchToolFactory` (Factory Pattern)

**Model Routing**:
- `model == "dental-google"` → `GoogleSearchTool`
- `model == "dental-duckduckgo"` → `DuckDuckGoSearchTool`

**Google Search Flow**:
1. Check configuration (`GOOGLE_SEARCH_API_KEY`, `GOOGLE_CSE_ID`)
2. If not configured → Auto fallback to DuckDuckGo (log warning)
3. If configured:
   - Call Google Custom Search API via `httpx`
   - Endpoint: `https://www.googleapis.com/customsearch/v1`
   - Parameters: `key`, `cx` (CSE ID), `q` (query), `num=5`
   - Parse JSON response
   - Format results: `Title | Content | Link`

**DuckDuckGo Search Flow**:
1. Use `duckduckgo-search` library
2. Query: `DDGS().text(query, max_results=5)`
3. Format results: `Title | Content | Link`

**Error Handling & Fallback**:
```python
try:
    search_tool = SearchToolFactory.create_search_tool(model)
    search_results = await search_tool.search(user_message)
except Exception:
    if model == "dental-google":
        # Fallback to DuckDuckGo
        search_tool = DuckDuckGoSearchTool()
        search_results = await search_tool.search(user_message)
    else:
        raise
```

---

### 5. LLM Response Generation - Step 4

**Service**: `ChatService` → Gemini LLM

**Prompt Construction**:

1. **Conversation Context** (if exists):
   ```
   Previous conversation context:
   Patient: "What is tooth decay?"
   Dentist: "Tooth decay is..."
   Patient: "How to prevent it?"
   ...
   ```

2. **Current Question**: Last user message

3. **Search Results**: Formatted search results

4. **Full Prompt Template**:
   ```
   You are a professional dental consultant.
   Answer based on search information and conversation context.

   [Conversation Context - if exists]

   Current patient's question: {user_message}

   Search information:
   {search_results}

   Please answer:
   - Accurate and based on search
   - Consistent with conversation context
   - Easy to understand and friendly
   - Mention sources if available
   - Suggest dentist consultation if incomplete
   ```

**LLM Processing**:
- Model: Gemini (configurable via `GOOGLE_BASE_MODEL`, default: `gemini-2.5-flash`)
- Method: `model.generate_content(prompt)`
- Output: Response text

**Memory Persistence** (MCP):
- Save user message: `memory_service.add_message(conv_id, "user", user_message)`
- Save assistant response: `memory_service.add_message(conv_id, "assistant", response_text)`
- Update conversation timestamp

**Return**: `(response_text, conversation_id)`

---

### 6. Response Formatting

**OpenAI-Compatible JSON**:
```json
{
  "id": "chatcmpl-{timestamp}",
  "object": "chat.completion",
  "created": {timestamp},
  "model": "dental-google",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Tooth decay is caused by..."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0
  },
  "system_fingerprint": "{conversation_id}"
}
```

**Conversation ID**:
- Included in `system_fingerprint` field
- Client should send `X-Conversation-ID: {conversation_id}` in next request

---

## Memory Context Protocol (MCP) Details

### Memory Storage

**In-Memory Storage** (current):
- `MemoryService` stores conversations in Python dict
- Key: `conversation_id`, Value: `ConversationMemory` object
- Persists during container lifetime

**Future Enhancement**:
- Redis for distributed memory
- Database (PostgreSQL/MongoDB) for persistent storage
- Vector database for semantic search

### Conversation Context Retrieval

**Strategy**: Last N Messages
- Default: 20 messages
- Configurable via `max_context_messages`
- Includes both user and assistant messages
- Maintains conversation flow

**Context Usage**:
- Included in LLM prompt for context awareness
- Allows follow-up questions ("What about prevention?")
- Enables multi-turn conversations

---

## Design Patterns Used

### 1. Factory Pattern
- `SearchToolFactory` creates search tools based on model name
- Encapsulates creation logic
- Easy to add new search providers

### 2. Service Layer Pattern
- Separation of concerns: Router → Service → Tools
- Testable and maintainable
- Clear responsibilities

### 3. Memory Context Protocol (MCP)
- Centralized conversation management
- Conversation lifecycle management
- Context retrieval and merging

---

## Error Handling Flow

```
Request → Router Validation
  ├─ Invalid model → HTTP 400
  └─ Valid → ChatService
      ├─ Memory Error → HTTP 500
      ├─ Guardrail Reject → HTTP 400 (domain not dental)
      ├─ Search Error → Fallback → HTTP 500 (if fallback fails)
      └─ LLM Error → HTTP 500
```

---

## API Endpoints Summary

### Chat Completion
- `POST /v1/chat/completions` - Main chat endpoint
- `GET /v1/models` - List available models

### Memory Management (MCP)
- `GET /v1/conversations/{id}` - Get conversation context
- `DELETE /v1/conversations/{id}` - Delete conversation
- `POST /v1/conversations/{id}/clear` - Clear conversation history

---

## Performance Considerations

1. **Memory Context Limiting**:
   - Default: 20 messages per context
   - Prevents token overflow
   - Configurable per conversation

2. **Search Caching** (Future):
   - Cache search results for common queries
   - Reduce API calls

3. **Async Processing**:
   - All I/O operations are async
   - Non-blocking search and LLM calls

4. **Fallback Mechanism**:
   - Google Search → DuckDuckGo (automatic)
   - No single point of failure

---

## Security Considerations

1. **Guardrail Protection**:
   - Domain validation prevents off-topic queries
   - Reduces abuse and API costs

2. **API Key Management**:
   - Environment variables only
   - Never exposed in code or logs

3. **CORS Configuration**:
   - Configurable allowed origins
   - Production: restrict to known domains

---

## Example Complete Flow

**Request 1** (New Conversation):
```
Client → POST /v1/chat/completions
  model: "dental-google"
  messages: [{"role": "user", "content": "What is tooth decay?"}]
  Headers: (no X-Conversation-ID)

Flow:
  1. Create new conversation_id: "abc-123"
  2. Guardrail: ✓ (dental-related)
  3. Google Search: Get results about tooth decay
  4. LLM: Generate response
  5. Memory: Save [user: "What is tooth decay?", assistant: "Tooth decay is..."]
  6. Response: {..., system_fingerprint: "abc-123"}

Client receives: conversation_id = "abc-123"
```

**Request 2** (Continue Conversation):
```
Client → POST /v1/chat/completions
  model: "dental-google"
  messages: [{"role": "user", "content": "How to prevent it?"}]
  Headers: X-Conversation-ID: "abc-123"

Flow:
  1. Get conversation_id: "abc-123"
  2. Retrieve context: [previous user+assistant messages]
  3. Merge: context + new message
  4. Guardrail: ✓
  5. Google Search: Get results about prevention
  6. LLM: Generate response (with context: "it" refers to tooth decay)
  7. Memory: Append [user: "How to prevent it?", assistant: "To prevent tooth decay..."]
  8. Response: {..., system_fingerprint: "abc-123"}

LLM understands context because of previous conversation in prompt!
```

---

This architecture ensures:
- ✅ Conversation continuity (MCP)
- ✅ Domain safety (Guardrail)
- ✅ Flexible search strategies (Factory Pattern)
- ✅ Reliability (Fallback mechanism)
- ✅ OpenAI compatibility
- ✅ Scalability (Async processing)
