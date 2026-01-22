# MCP Data Flow Documentation
## Chi tiết Flow Hoạt Động của Dữ Liệu trong Dental Chatbot

---

## 1. Tổng Quan Kiến Trúc MCP

### 1.1. Đối Chiếu với Mô Hình MCP Chuẩn

Dựa trên mô hình MCP trong hình ảnh, hệ thống của chúng ta được triển khai như sau:

```
┌─────────────────────────────────────────────────────────────┐
│                    Application (Host)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  UX Layer: FastAPI Router (routers/openai.py)        │  │
│  │  Orchestration: ChatService (services/chat_service.py)│  │
│  │  Security Policies: Guardrail Service                │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  MCP Client (mcp/base.py - MCPClient)                │  │
│  │  - Maintain connection                               │  │
│  │  - Session lifecycle                                 │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             │ JSON-RPC 2.0 (in-process)
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Tools: ToolMCPServer (google_search, duckduckgo)   │  │
│  │  Resources: MemoryMCPServer (conversation history)  │  │
│  │  Prompts: (not implemented yet)                      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 1.2. Các Thành Phần Chính

#### **MCPHost** (`mcp/base.py`)
- **Vai trò**: Orchestrator, quản lý tất cả clients và servers
- **Chức năng**:
  - Đăng ký servers và tạo clients
  - Quản lý lifecycle của connections
  - Lưu trữ conversation context (optional)

#### **MCPClient** (`mcp/base.py`)
- **Vai trò**: Interface để giao tiếp với MCP Server
- **Chức năng**:
  - Gửi JSON-RPC requests đến server
  - Nhận JSON-RPC responses từ server
  - Quản lý session lifecycle

#### **MCPServer** (`mcp/base.py`)
- **Vai trò**: Base class cho tất cả MCP servers
- **Chức năng**:
  - Đăng ký methods (tools, resources, prompts)
  - Xử lý JSON-RPC requests
  - Trả về JSON-RPC responses

#### **MemoryMCPServer** (`mcp/servers/memory_server.py`)
- **Vai trò**: Expose memory/conversation history như Resources
- **Methods**:
  - `resources/list`: Liệt kê tất cả conversations
  - `resources/read`: Đọc conversation theo URI
  - `memory/get_context`: Lấy context của conversation
  - `memory/add_message`: Thêm message vào conversation
  - `memory/get_or_create`: Tạo hoặc lấy conversation ID

#### **ToolMCPServer** (`mcp/servers/tool_server.py`)
- **Vai trò**: Expose search tools như Tools
- **Methods**:
  - `tools/list`: Liệt kê available tools
  - `tools/call`: Gọi tool với arguments

---

## 2. Chi Tiết Data Flow

### 2.1. Khởi Tạo Hệ Thống (Initialization)

**File**: `routers/openai.py` (lines 12-22)

```python
# Step 1: Tạo MCP Host
mcp_host = MCPHost()
# → Tạo dictionary rỗng: clients = {}, conversation_history = {}

# Step 2: Tạo MCP Servers
memory_server = MemoryMCPServer()
# → Khởi tạo MemoryService, đăng ký methods
tool_server = ToolMCPServer()
# → Đăng ký tool methods

# Step 3: Đăng ký servers vào Host
mcp_host.register_server(memory_server)
# → Tạo MCPClient cho memory_server
# → Lưu vào mcp_host.clients["memory-server"] = client

mcp_host.register_server(tool_server)
# → Tạo MCPClient cho tool_server
# → Lưu vào mcp_host.clients["tool-server"] = client

# Step 4: Tạo ChatService với MCP Host
chat_service = ChatService(mcp_host=mcp_host)
# → Lưu references: self.memory_client, self.tool_client
```

**Data Flow**:
```
MCPHost.__init__()
  → clients = {}
  → conversation_history = {}

MemoryMCPServer.__init__()
  → server_name = "memory-server"
  → memory_service = MemoryService()
  → _register_methods() → Đăng ký 6 methods

ToolMCPServer.__init__()
  → server_name = "tool-server"
  → _register_methods() → Đăng ký 2 methods

MCPHost.register_server(memory_server)
  → MCPClient(server=memory_server)
  → clients["memory-server"] = client

MCPHost.register_server(tool_server)
  → MCPClient(server=tool_server)
  → clients["tool-server"] = client
```

---

### 2.2. Request Flow: Từ HTTP Request đến Response

**File**: `routers/openai.py` → `services/chat_service.py`

#### **Step 1: HTTP Request Nhận Được**

```
POST /v1/chat/completions
{
  "model": "dental-duckduckgo",
  "messages": [{"role": "user", "content": "Một ngày nên đánh răng bao nhiêu lần?"}],
  "chat_id": "chat_123456"
}
```

**Data Flow**:
```
FastAPI Router (routers/openai.py)
  → ChatCompletionRequest.parse()
  → messages = [{"role": "user", "content": "..."}]
  → conversation_id = "chat_123456"
```

#### **Step 2: Extract User Message**

**File**: `services/chat_service.py` (lines 63-74)

```python
# Tìm message cuối cùng có role="user"
for msg in reversed(messages):
    if msg.get("role") == "user":
        user_message = msg.get("content", "")
        break
```

**Data Flow**:
```
messages = [{"role": "user", "content": "Một ngày nên đánh răng bao nhiêu lần?"}]
  → reversed(messages)
  → msg.get("role") == "user" → True
  → user_message = "Một ngày nên đánh răng bao nhiêu lần?"
```

#### **Step 3: Guardrail Check**

**File**: `services/chat_service.py` (lines 76-79)

```python
is_dental = await self.guardrail.is_dental_related(user_message)
```

**Data Flow**:
```
GuardrailService.is_dental_related()
  → Detect language using LLM
  → Build prompt (Vietnamese or English)
  → Call LLM provider (Ollama/Gemini)
  → Parse response: "YES" or "NO"
  → Return True/False
```

**Chi tiết Guardrail Flow**:
```
user_message = "Một ngày nên đánh răng bao nhiêu lần?"

1. Detect Language:
   detect_language_llm(user_message, guardrail.llm)
     → LLM prompt: "Determine language: vi or en"
     → LLM response: "vi"
     → user_lang = "vi"

2. Build Guardrail Prompt (Vietnamese):
   prompt = "Bạn là hệ thống kiểm duyệt... Câu hỏi: {question}... Trả lời: YES/NO"

3. Call LLM:
   guardrail.llm.generate(prompt, use_guardrail_model=True)
     → Ollama API: POST /api/generate
     → Response: "YES"

4. Parse Result:
   "YES" in result → return True
```

#### **Step 4: Get or Create Conversation (MCP Call)**

**File**: `services/chat_service.py` (lines 113-120)

```python
memory_result = await self.memory_client.call_method(
    "memory/get_or_create",
    {"conversation_id": conversation_id}
)
conv_id = memory_result["conversation_id"]
```

**Data Flow Chi Tiết**:

```
ChatService.memory_client.call_method("memory/get_or_create", {...})
  │
  ├─> MCPClient.call_method()
  │     → JSONRPCRequest(
  │         method="memory/get_or_create",
  │         params={"conversation_id": "chat_123456"},
  │         request_id=None
  │       )
  │
  ├─> MemoryMCPServer.handle_request(request)
  │     → method_name = "memory/get_or_create"
  │     → handler = self.methods["memory/get_or_create"]
  │     → handler = _get_or_create
  │
  ├─> MemoryMCPServer._get_or_create(conversation_id="chat_123456")
  │     → self.memory_service.get_or_create_conversation("chat_123456")
  │     → MemoryService.get_or_create_conversation()
  │         → if conversation_id exists:
  │             return conversation_id
  │         → else:
  │             new_id = str(uuid.uuid4())
  │             self.conversations[new_id] = ConversationMemory()
  │             return new_id
  │
  ├─> Return: {"conversation_id": "chat_123456"}
  │
  └─> JSONRPCResponse.success(result={"conversation_id": "chat_123456"})
        → response.result = {"conversation_id": "chat_123456"}
        → return response

ChatService nhận được:
  memory_result = {"conversation_id": "chat_123456"}
  conv_id = "chat_123456"
```

**JSON-RPC Request/Response Format**:

```json
// Request (internal, không serialize thành JSON vì in-process)
{
  "jsonrpc": "2.0",
  "method": "memory/get_or_create",
  "params": {"conversation_id": "chat_123456"},
  "id": null
}

// Response
{
  "jsonrpc": "2.0",
  "result": {"conversation_id": "chat_123456"},
  "id": null
}
```

#### **Step 5: Get Conversation Context (MCP Call)**

**File**: `services/chat_service.py` (lines 122-129)

```python
context_result = await self.memory_client.call_method(
    "memory/get_context",
    {"conversation_id": conv_id, "max_messages": 20}
)
memory_context = context_result.get("messages", [])
```

**Data Flow Chi Tiết**:

```
ChatService.memory_client.call_method("memory/get_context", {...})
  │
  ├─> MCPClient.call_method()
  │     → JSONRPCRequest(
  │         method="memory/get_context",
  │         params={"conversation_id": "chat_123456", "max_messages": 20}
  │       )
  │
  ├─> MemoryMCPServer.handle_request(request)
  │     → handler = _get_context
  │
  ├─> MemoryMCPServer._get_context(conversation_id="chat_123456", max_messages=20)
  │     → self.memory_service.get_conversation_context("chat_123456", 20)
  │     → MemoryService.get_conversation_context()
  │         → conv = self.conversations.get("chat_123456")
  │         → if conv:
  │             messages = conv.messages[-20:]  # Last 20 messages
  │             return [{"role": "user", "content": "..."}, ...]
  │         → else:
  │             return []
  │
  └─> Return: {"messages": [...]}

ChatService nhận được:
  context_result = {"messages": [previous_messages]}
  memory_context = [previous_messages]
```

#### **Step 6: Merge Messages**

**File**: `services/chat_service.py` (lines 131-140)

```python
all_messages = memory_context.copy()
if not all_messages or all_messages[-1].get("content") != user_message:
    all_messages.append({"role": "user", "content": user_message})
```

**Data Flow**:
```
memory_context = [
  {"role": "user", "content": "Câu hỏi trước"},
  {"role": "assistant", "content": "Trả lời trước"}
]

all_messages = memory_context.copy()
  → all_messages = [
      {"role": "user", "content": "Câu hỏi trước"},
      {"role": "assistant", "content": "Trả lời trước"}
    ]

all_messages.append({"role": "user", "content": user_message})
  → all_messages = [
      {"role": "user", "content": "Câu hỏi trước"},
      {"role": "assistant", "content": "Trả lời trước"},
      {"role": "user", "content": "Một ngày nên đánh răng bao nhiêu lần?"}
    ]
```

#### **Step 7: Call Search Tool (MCP Call)**

**File**: `services/chat_service.py` (lines 142-160)

```python
tool_name = "google_search" if model == "dental-google" else "duckduckgo_search"

tool_result = await self.tool_client.call_method(
    "tools/call",
    {
        "name": tool_name,
        "arguments": {"query": user_message}
    }
)
search_results = tool_result["content"][0]["text"]
```

**Data Flow Chi Tiết**:

```
ChatService.tool_client.call_method("tools/call", {...})
  │
  ├─> MCPClient.call_method()
  │     → JSONRPCRequest(
  │         method="tools/call",
  │         params={
  │           "name": "duckduckgo_search",
  │           "arguments": {"query": "Một ngày nên đánh răng bao nhiêu lần?"}
  │         }
  │       )
  │
  ├─> ToolMCPServer.handle_request(request)
  │     → handler = _call_tool_handler
  │
  ├─> ToolMCPServer._call_tool_handler(
  │       name="duckduckgo_search",
  │       arguments={"query": "..."}
  │     )
  │     → query = arguments.get("query")
  │     → model_mapping = {"duckduckgo_search": "dental-duckduckgo"}
  │     → model = "dental-duckduckgo"
  │     → SearchToolFactory.create_search_tool("dental-duckduckgo")
  │         → return DuckDuckGoSearchTool()
  │     → search_tool.search(query)
  │         → DuckDuckGoSearchTool.search()
  │             → DDGS().text(query, max_results=5)
  │             → Format results
  │             → return formatted_text
  │
  └─> Return: {
        "content": [
          {
            "type": "text",
            "text": "Title: ...\nContent: ...\nLink: ...\n---\n..."
          }
        ]
      }

ChatService nhận được:
  tool_result = {"content": [{"type": "text", "text": "..."}]}
  search_results = "Title: ...\nContent: ...\nLink: ..."
```

**Chi Tiết Search Tool Execution**:

```
ToolMCPServer._call_tool_handler()
  │
  ├─> Parse arguments:
  │     name = "duckduckgo_search"
  │     query = "Một ngày nên đánh răng bao nhiêu lần?"
  │
  ├─> Map tool to model:
  │     model = "dental-duckduckgo"
  │
  ├─> Create search tool:
  │     SearchToolFactory.create_search_tool("dental-duckduckgo")
  │       → return DuckDuckGoSearchTool()
  │
  ├─> Execute search:
  │     DuckDuckGoSearchTool.search(query)
  │       → with DDGS() as ddgs:
  │       → results = list(ddgs.text(query, max_results=5))
  │       → results = [
  │           {"title": "...", "body": "...", "href": "..."},
  │           ...
  │         ]
  │       → Format results:
  │         formatted = []
  │         for result in results:
  │           formatted.append(f"Title: {title}\nContent: {body}\nLink: {href}")
  │       → return "\n---\n".join(formatted)
  │
  └─> Return formatted results
```

#### **Step 8: Detect Language và Build Prompt**

**File**: `services/chat_service.py` (lines 185-220)

```python
user_lang = await detect_language_llm(user_message, self.guardrail.llm)

if user_lang == "vi":
    prompt = f"""Bạn là một chuyên gia tư vấn nha khoa...
    {conversation_summary}
    Câu hỏi hiện tại: {user_message}
    Thông tin tìm kiếm: {search_results}
    Trả lời:"""
else:
    prompt = f"""You are a professional dental consultant...
    {conversation_summary}
    Current question: {user_message}
    Search information: {search_results}
    Answer:"""
```

**Data Flow**:
```
detect_language_llm(user_message, guardrail.llm)
  → LLM prompt: "Determine language: vi or en"
  → LLM response: "vi"
  → user_lang = "vi"

Build prompt (Vietnamese):
  prompt = """
    Bạn là một chuyên gia tư vấn nha khoa...
    
    Previous conversation context:
    Patient: Câu hỏi trước
    Dentist: Trả lời trước
    
    Câu hỏi hiện tại của bệnh nhân: Một ngày nên đánh răng bao nhiêu lần?
    
    Thông tin tìm kiếm:
    Title: ...
    Content: ...
    Link: ...
    ---
    ...
    
    Trả lời:
  """
```

#### **Step 9: Generate Response với LLM**

**File**: `services/chat_service.py` (lines 222-228)

```python
response_text = await self.llm.generate(prompt)
```

**Data Flow**:
```
ChatService.llm.generate(prompt)
  │
  ├─> OllamaProvider.generate(prompt)
  │     → model_to_use = "llama3.2"
  │     → httpx.AsyncClient.post(
  │         url="http://localhost:11434/api/generate",
  │         json={
  │           "model": "llama3.2",
  │           "prompt": prompt,
  │           "stream": False
  │         }
  │       )
  │
  ├─> Ollama API Response:
  │     {
  │       "response": "Theo khuyến nghị từ các tổ chức y tế...",
  │       "done": true
  │     }
  │
  └─> Return: "Theo khuyến nghị từ các tổ chức y tế..."

ChatService nhận được:
  response_text = "Theo khuyến nghị từ các tổ chức y tế..."
```

#### **Step 10: Save Messages to Memory (2 MCP Calls)**

**File**: `services/chat_service.py` (lines 230-240)

```python
await self.memory_client.call_method(
    "memory/add_message",
    {"conversation_id": conv_id, "role": "user", "content": user_message}
)

await self.memory_client.call_method(
    "memory/add_message",
    {"conversation_id": conv_id, "role": "assistant", "content": response_text}
)
```

**Data Flow Chi Tiết**:

```
Call 1: Save user message
  │
  ├─> MCPClient.call_method("memory/add_message", {
  │       "conversation_id": "chat_123456",
  │       "role": "user",
  │       "content": "Một ngày nên đánh răng bao nhiêu lần?"
  │     })
  │
  ├─> MemoryMCPServer._add_message(...)
  │     → self.memory_service.add_message(...)
  │     → MemoryService.add_message()
  │         → conv = self.conversations.get("chat_123456")
  │         → conv.messages.append({
  │             "role": "user",
  │             "content": "Một ngày nên đánh răng bao nhiêu lần?",
  │             "timestamp": datetime.now()
  │           })
  │
  └─> Return: {"status": "success", "conversation_id": "chat_123456"}

Call 2: Save assistant message
  │
  ├─> MCPClient.call_method("memory/add_message", {
  │       "conversation_id": "chat_123456",
  │       "role": "assistant",
  │       "content": "Theo khuyến nghị từ các tổ chức y tế..."
  │     })
  │
  ├─> MemoryMCPServer._add_message(...)
  │     → self.memory_service.add_message(...)
  │     → conv.messages.append({
  │         "role": "assistant",
  │         "content": "Theo khuyến nghị từ các tổ chức y tế...",
  │         "timestamp": datetime.now()
  │       })
  │
  └─> Return: {"status": "success", "conversation_id": "chat_123456"}
```

**Memory State After Save**:
```
MemoryService.conversations["chat_123456"].messages = [
  {"role": "user", "content": "Câu hỏi trước", "timestamp": "..."},
  {"role": "assistant", "content": "Trả lời trước", "timestamp": "..."},
  {"role": "user", "content": "Một ngày nên đánh răng bao nhiêu lần?", "timestamp": "..."},
  {"role": "assistant", "content": "Theo khuyến nghị từ các tổ chức y tế...", "timestamp": "..."}
]
```

#### **Step 11: Return Response**

**File**: `services/chat_service.py` (line 242)

```python
return response_text, conv_id
```

**Data Flow**:
```
ChatService.process_chat() returns:
  → ("Theo khuyến nghị từ các tổ chức y tế...", "chat_123456")

Router (routers/openai.py) formats response:
  → {
      "id": "chatcmpl-123456",
      "object": "chat.completion",
      "created": 1234567890,
      "model": "dental-duckduckgo",
      "choices": [{
        "index": 0,
        "message": {
          "role": "assistant",
          "content": "Theo khuyến nghị từ các tổ chức y tế..."
        },
        "finish_reason": "stop"
      }],
      "usage": {...},
      "system_fingerprint": "chat_123456"
    }
```

---

## 3. JSON-RPC 2.0 Protocol Flow

### 3.1. Request Format

```python
# Trong MCPClient.call_method()
request = JSONRPCRequest(
    method="memory/get_context",
    params={"conversation_id": "chat_123456", "max_messages": 20},
    request_id=None
)

# Serialized (nếu cần):
{
  "jsonrpc": "2.0",
  "method": "memory/get_context",
  "params": {
    "conversation_id": "chat_123456",
    "max_messages": 20
  },
  "id": null
}
```

### 3.2. Response Format

```python
# Trong MCPServer.handle_request()
response = JSONRPCResponse.success(
    result={"messages": [...]},
    request_id=None
)

# Serialized (nếu cần):
{
  "jsonrpc": "2.0",
  "result": {
    "messages": [
      {"role": "user", "content": "..."},
      {"role": "assistant", "content": "..."}
    ]
  },
  "id": null
}
```

### 3.3. Error Format

```python
# Nếu method không tồn tại:
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32601,
    "message": "Method 'unknown/method' not found on server 'memory-server'"
  },
  "id": null
}

# Nếu có lỗi internal:
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32603,
    "message": "Internal server error: ..."
  },
  "id": null
}
```

---

## 4. Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    HTTP Request (FastAPI)                        │
│  POST /v1/chat/completions                                       │
│  {model, messages, chat_id}                                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ChatService.process_chat()                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 1: Extract user message                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 2: Guardrail Check                                  │  │
│  │   → GuardrailService.is_dental_related()                 │  │
│  │   → LLM: Detect language + Check domain                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 3: Get/Create Conversation (MCP Call)              │  │
│  │   memory_client.call_method("memory/get_or_create")      │  │
│  │   └─> JSON-RPC → MemoryMCPServer                        │  │
│  │       └─> MemoryService.get_or_create_conversation()     │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 4: Get Context (MCP Call)                          │  │
│  │   memory_client.call_method("memory/get_context")        │  │
│  │   └─> JSON-RPC → MemoryMCPServer                        │  │
│  │       └─> MemoryService.get_conversation_context()       │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 5: Merge Messages                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 6: Call Search Tool (MCP Call)                     │  │
│  │   tool_client.call_method("tools/call")                 │  │
│  │   └─> JSON-RPC → ToolMCPServer                          │  │
│  │       └─> SearchToolFactory.create_search_tool()        │  │
│  │           └─> DuckDuckGoSearchTool.search()             │  │
│  │               └─> DDGS().text() → Search results         │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 7: Detect Language + Build Prompt                   │  │
│  │   → detect_language_llm()                                │  │
│  │   → Build prompt (Vietnamese/English)                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 8: Generate Response (LLM)                          │  │
│  │   → OllamaProvider.generate(prompt)                      │  │
│  │   → Ollama API: POST /api/generate                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 9: Save Messages (2 MCP Calls)                     │  │
│  │   memory_client.call_method("memory/add_message") x2     │  │
│  │   └─> JSON-RPC → MemoryMCPServer                         │  │
│  │       └─> MemoryService.add_message()                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    HTTP Response (FastAPI)                      │
│  {id, object, created, model, choices, usage}                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. MCP Server Capabilities

### 5.1. MemoryMCPServer Capabilities

**Tools**: `[]` (không có tools)

**Resources**: 
```json
[
  {
    "uri": "memory://conversation/chat_123456",
    "name": "Conversation chat_123",
    "description": "Conversation history for chat_123456",
    "mimeType": "application/json"
  }
]
```

**Prompts**: `[]` (không có prompts)

**Methods**:
- `resources/list` → List all conversation resources
- `resources/read` → Read conversation by URI
- `memory/get_context` → Get conversation context
- `memory/add_message` → Add message to conversation
- `memory/get_or_create` → Get or create conversation ID
- `memory/clear` → Clear conversation
- `memory/delete` → Delete conversation

### 5.2. ToolMCPServer Capabilities

**Tools**:
```json
[
  {
    "name": "google_search",
    "description": "Search using Google ADK google_search tool",
    "inputSchema": {
      "type": "object",
      "properties": {
        "query": {"type": "string", "description": "Search query"}
      },
      "required": ["query"]
    }
  },
  {
    "name": "duckduckgo_search",
    "description": "Search using DuckDuckGo",
    "inputSchema": {
      "type": "object",
      "properties": {
        "query": {"type": "string", "description": "Search query"}
      },
      "required": ["query"]
    }
  }
]
```

**Resources**: `[]` (không có resources)

**Prompts**: `[]` (không có prompts)

**Methods**:
- `tools/list` → List available tools
- `tools/call` → Execute tool with arguments

---

## 6. Workflow: Discover → Select → Call → Return

Theo mô hình MCP trong hình ảnh:

### 6.1. Discover Tools

```python
# Client có thể discover tools
tools = await tool_client.list_tools()
# → [
#     {"name": "google_search", "description": "...", "inputSchema": {...}},
#     {"name": "duckduckgo_search", "description": "...", "inputSchema": {...}}
#   ]
```

**Data Flow**:
```
tool_client.list_tools()
  → tool_client.server.get_capabilities()
  → ToolMCPServer.get_capabilities()
  → ToolMCPServer._list_tools()
  → Return: [tool_definitions]
```

### 6.2. Select Tool

```python
# Trong ChatService, tool được chọn dựa trên model
tool_name = "google_search" if model == "dental-google" else "duckduckgo_search"
```

### 6.3. Call Tool (JSON-RPC)

```python
# Gọi tool qua JSON-RPC
tool_result = await tool_client.call_method(
    "tools/call",
    {
        "name": tool_name,
        "arguments": {"query": user_message}
    }
)
```

**JSON-RPC Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "duckduckgo_search",
    "arguments": {
      "query": "Một ngày nên đánh răng bao nhiêu lần?"
    }
  },
  "id": null
}
```

### 6.4. Return Result

**JSON-RPC Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Title: ...\nContent: ...\nLink: ..."
      }
    ]
  },
  "id": null
}
```

---

## 7. So Sánh với Mô Hình MCP Chuẩn

| Mô Hình MCP Chuẩn | Implementation của Chúng Ta | Ghi Chú |
|-------------------|----------------------------|---------|
| **Application (Host)** | `ChatService` + `FastAPI Router` | ✅ Đúng |
| **UX Layer** | `routers/openai.py` | ✅ Đúng |
| **Orchestration** | `ChatService.process_chat()` | ✅ Đúng |
| **Security Policies** | `GuardrailService` | ✅ Đúng |
| **MCP Client** | `MCPClient` class | ✅ Đúng |
| **Connection Management** | In-process (không cần network) | ⚠️ Simplified |
| **Session Lifecycle** | Managed by `MCPHost` | ✅ Đúng |
| **Communication Channel** | JSON-RPC 2.0 (in-process) | ✅ Đúng |
| **MCP Server** | `MCPServer` base class | ✅ Đúng |
| **Tools** | `ToolMCPServer` | ✅ Đúng |
| **Resources** | `MemoryMCPServer` | ✅ Đúng |
| **Prompts** | Chưa implement | ⚠️ TODO |

---

## 8. Kết Luận

Hệ thống của chúng ta tuân thủ đúng kiến trúc MCP với các điểm chính:

1. ✅ **MCP Host**: Quản lý clients và servers
2. ✅ **MCP Client**: Interface để giao tiếp với servers
3. ✅ **MCP Server**: Expose capabilities (Tools, Resources)
4. ✅ **JSON-RPC 2.0**: Protocol giao tiếp giữa client và server
5. ✅ **Workflow**: Discover → Select → Call → Return

**Điểm khác biệt**:
- Communication channel là in-process (không qua network) vì tất cả chạy trong cùng process
- Không có Prompts server (có thể thêm sau nếu cần)

**Data Flow** rõ ràng và tuân thủ đúng MCP protocol, đảm bảo tính modular và dễ mở rộng.
