# Architecture Documentation - Dental Chatbot

## Tổng quan

Dental Chatbot là một ứng dụng AI chatbot chuyên về lĩnh vực nha khoa, được xây dựng với kiến trúc microservices sử dụng MCP (Model Context Protocol) và tích hợp Phoenix Observability để theo dõi và phân tích hiệu suất.

## Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────────┐
│                    Client Layer (Web Browser)                    │
│  - Chat Interface (index.html)                                  │
│  - Configuration Page (config.html)                             │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/REST
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Main Application (FastAPI - Port 8000)             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Routers Layer                                            │  │
│  │  - /v1/chat/completions (OpenAI-compatible)               │  │
│  │  - /v1/models                                             │  │
│  └────────────────────┬─────────────────────────────────────┘  │
│                       │                                         │
│  ┌────────────────────▼─────────────────────────────────────┐  │
│  │  Services Layer                                           │  │
│  │  - ChatService (orchestrates flow)                        │  │
│  │  - GuardrailService (dental check)                        │  │
│  │  - LLMProvider (Ollama abstraction)                        │  │
│  │  - PhoenixTracing (observability) ◄─── Traces tất cả     │  │
│  └───────┬───────────────────────────────┬───────────────────┘  │
│          │                               │                       │
│          │                               │                       │
│  ┌───────▼───────────┐         ┌────────▼───────────────────┐  │
│  │  MCP Client Layer  │         │  Direct HTTP Calls         │  │
│  │  - MCPHost         │         │  - Ollama API              │  │
│  │  - MCPClient       │         │                            │  │
│  └───────┬────────────┘         └────────┬───────────────────┘  │
│          │                               │                       │
└──────────┼───────────────────────────────┼───────────────────────┘
           │                               │
           │ HTTP JSON-RPC 2.0             │ HTTP
           │                               │
           ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────────┐
│  MCP Server              │    │  External Services           │
│  (FastAPI - Port 8001)   │    │  ┌────────────────────┐      │
│  ┌────────────────────┐  │    │  │ Ollama LLM         │      │
│  │ MCP Protocol       │  │    │  │ (Port 11434)       │      │
│  │ Handler            │  │    │  └────────────────────┘      │
│  └────────┬───────────┘  │    └──────────────────────────────┘
│           │               │
│  ┌────────▼────────────┐  │
│  │  MCP Servers        │  │
│  │  ┌──────────────┐   │  │
│  │  │ Memory       │   │  │
│  │  │ Server       │   │  │
│  │  └──────────────┘   │  │
│  │  ┌──────────────┐   │  │
│  │  │ Tool Server  │───┼──┼──► HTTP ──┐
│  │  │              │   │  │           │
│  │  └──────────────┘   │  │           │
│  └─────────────────────┘  │           │
└──────────────────────────┘           │
                                       │
                                       ▼
                            ┌──────────────────────────┐
                            │ DuckDuckGo API           │
                            │ (Internet)               │
                            └──────────────────────────┘

           ┌───────────────────────────────────────────┐
           │                                           │
           │  OTLP gRPC (Traces)                       │
           │  (Port 4317)                              │
           │                                           │
           ▼                                           │
┌──────────────────────────────────────────────────────┐
│  Phoenix Observability (Docker)                     │
│  ┌────────────────────┐  ┌──────────────────────┐  │
│  │ Phoenix Server     │  │ PostgreSQL Database  │  │
│  │ (Port 6006 UI)     │  │ (Port 5433)          │  │
│  │ (Port 4317 OTLP)   │  │                      │  │
│  └────────────────────┘  └──────────────────────┘  │
└──────────────────────────────────────────────────────┘

Lưu ý: Phoenix chỉ nhận traces từ Main Application.
Main Application trace tất cả operations bao gồm:
- Internal operations (chat flow, guardrail, etc.)
- Calls đến MCP Server (memory, tools)
- Calls đến Ollama (LLM generation)
- Calls gián tiếp đến DuckDuckGo (qua MCP Server)
```

## Các thành phần chính

### 1. Main Application (FastAPI)

**Vị trí**: `main.py`, `routers/`, `services/`

**Chức năng**:
- Cung cấp API endpoints (OpenAI-compatible)
- Web interface (HTML/CSS/JS)
- Orchestration logic cho chat flow
- Kết nối với MCP Server và Ollama

**Port**: 8000

**Endpoints chính**:
- `POST /v1/chat/completions` - Chat completion endpoint
- `GET /v1/models` - List models
- `GET /` - Chat interface
- `GET /config` - Configuration page
- `GET /health` - Health check

### 2. MCP Server (Standalone)

**Vị trí**: `mcp/server.py`, `mcp/servers/`

**Chức năng**:
- Cung cấp Memory và Tool services qua JSON-RPC 2.0
- Quản lý conversation history
- Thực thi tools (DuckDuckGo search)

**Port**: 8001

**Protocol**: JSON-RPC 2.0 over HTTP

**MCP Servers**:
- `memory-server`: Quản lý conversations, summaries, messages
- `tool-server`: Cung cấp search tools

### 3. Services Layer

#### ChatService (`services/chat_service.py`)
**Chức năng**: Orchestrates toàn bộ chat flow

**Flow xử lý**:
1. Extract user message
2. Language detection (`llm.guardrail.detection_language`)
3. Guardrail check (`llm.guardrail.check_dental`)
4. Get/create conversation (`memory.get_or_create_conversation`)
5. Get conversation summary (`memory.get_conversation_summary`)
6. Search tool (`tool.duckduckgo_search`)
7. Extract sources (`tool.extract_sources`)
8. Generate response (`llm.generate`)
9. Save messages (`memory.save_messages`)
10. Generate summary (background) (`llm.generate.summary` → `memory.update_summary`)

#### GuardrailService (`services/guardrail.py`)
**Chức năng**: Kiểm tra câu hỏi có liên quan đến nha khoa không

**Methods**:
- `is_dental_related()`: Check với LLM guardrail model
- `detect_language_llm()`: Detect language (Vietnamese/English)

#### LLMProvider (`services/llm_provider.py`)
**Chức năng**: Abstraction layer cho LLM providers

**Implementation**: OllamaProvider
- Kết nối đến Ollama API
- Hỗ trợ guardrail model và main model
- Tracing với Phoenix

#### PhoenixTracing (`services/phoenix_tracing.py`)
**Chức năng**: Centralized tracing với Phoenix

**Features**:
- Automatic span creation
- Input/output logging
- Timing tracking
- Context management

### 4. MCP Client Layer

**Vị trí**: `clients/mcp_client.py`

**Chức năng**:
- HTTP client cho MCP Server
- JSON-RPC 2.0 protocol implementation
- Client management (MCPHost)

**Classes**:
- `MCPClient`: Single server client
- `MCPHost`: Manages multiple clients

### 5. Phoenix Observability

**Vị trí**: `docker-compose.phoenix.yml`

**Components**:
- Phoenix Server: UI (port 6006) + OTLP receiver (port 4317)
- PostgreSQL: Database cho traces

**Tracing**:
- OpenTelemetry protocol (OTLP gRPC)
- Automatic span creation
- Full input/output logging
- Performance monitoring

## Data Flow - Chat Request

```
1. User Request
   └─> POST /v1/chat/completions
       └─> routers/openai.py::chat_completions()
           └─> Span: chat.completion.request

2. Chat Processing
   └─> services/chat_service.py::process_chat()
       │
       ├─> Step 1: Language Detection
       │   └─> Span: llm.guardrail.detection_language
       │       └─> Ollama API (guardrail model)
       │
       ├─> Step 2: Guardrail Check
       │   └─> Span: llm.guardrail.check_dental
       │       └─> Ollama API (guardrail model)
       │       └─> If rejected → Span: guardrail.reject
       │
       ├─> Step 3: Memory Operations
       │   ├─> Span: memory.get_or_create_conversation
       │   │   └─> MCP Server: memory/get_or_create
       │   └─> Span: memory.get_conversation_summary
       │       └─> MCP Server: memory/get_summary
       │
       ├─> Step 4: Search Tool
       │   └─> Span: tool.duckduckgo_search
       │       └─> MCP Server: tools/call
       │           └─> DuckDuckGo API
       │
       ├─> Step 5: Extract Sources
       │   └─> Span: tool.extract_sources
       │
       ├─> Step 6: Generate Response
       │   └─> Span: llm.generate
       │       └─> Ollama API (main model)
       │
       └─> Step 7: Save & Summarize
           ├─> Span: memory.save_messages
           │   └─> MCP Server: memory/add_message (x2)
           └─> Background: llm.generate.summary
               ├─> Span: llm.generate.summary
               │   └─> Ollama API (guardrail model)
               └─> Span: memory.update_summary
                   └─> MCP Server: memory/set_summary

3. Response
   └─> Return to client (OpenAI format)
```

## Tracing Architecture

### Span Hierarchy

```
chat.completion.request (parent)
├── llm.guardrail.detection_language
├── llm.guardrail.check_dental
├── guardrail.reject (nếu reject)
├── memory.get_or_create_conversation
├── memory.get_conversation_summary
├── tool.duckduckgo_search
├── tool.extract_sources
├── llm.generate
├── memory.save_messages
└── llm.generate.summary (background)
    └── memory.update_summary
```

### Span Naming Convention

- `llm.*` - LLM operations
- `tool.*` - Tool executions
- `memory.*` - Memory operations
- `guardrail.*` - Guardrail operations

### Tracing Attributes

Mỗi span có đầy đủ:
- **Input**: Request data, parameters, prompts
- **Output**: Response data, results
- **Metadata**: Model names, conversation IDs, timing

## Technology Stack

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.12+
- **LLM**: Ollama (local)
- **Protocol**: JSON-RPC 2.0 (MCP)
- **HTTP Client**: httpx

### Observability
- **Platform**: Arize Phoenix
- **Protocol**: OpenTelemetry (OTLP gRPC)
- **Database**: PostgreSQL 15
- **Tracing**: OpenInference semantic conventions

### Infrastructure
- **Containerization**: Docker, Docker Compose
- **Database**: PostgreSQL (Phoenix)
- **Web Server**: Uvicorn

## Configuration

### Environment Variables

```env
# LLM Provider
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct
OLLAMA_GUARDRAIL_MODEL=qwen2.5:3b-instruct

# MCP Server
MCP_SERVER_URL=http://localhost:8001

# Phoenix Observability
PHOENIX_ENABLED=true
PHOENIX_ENDPOINT=http://localhost:4317
PHOENIX_PROJECT_NAME=dental-chatbot
```

## Deployment Architecture

### Local Development

```
┌─────────────┐
│   Ollama    │ (Port 11434)
└──────┬──────┘
       │
┌──────▼──────┐
│ Main App    │ (Port 8000)
└──────┬──────┘
       │
┌──────▼──────┐
│ MCP Server  │ (Port 8001)
└──────┬──────┘
       │
┌──────▼──────┐
│  Phoenix    │ (Port 6006 UI, 4317 OTLP)
└──────┬──────┘
       │
┌──────▼──────┐
│ PostgreSQL  │ (Port 5433)
└─────────────┘
```

### Docker Deployment

- **Main App**: Có thể containerize hoặc chạy local
- **MCP Server**: Có thể containerize hoặc chạy local
- **Phoenix**: Docker Compose (`docker-compose.phoenix.yml`)
- **Ollama**: Chạy trên host hoặc container riêng

## Key Design Decisions

### 1. MCP Standalone Server
- **Lý do**: Tách biệt concerns, dễ scale, có thể reuse cho nhiều ứng dụng
- **Lợi ích**: Memory và Tools có thể được dùng bởi nhiều AI applications

### 2. Code-Driven Tool Selection
- **Lý do**: Đảm bảo reliability, không phụ thuộc vào LLM decision
- **Implementation**: Tool được gọi tự động trong code flow

### 3. Guardrail Before Memory
- **Lý do**: Chỉ lưu câu hỏi liên quan đến nha khoa
- **Lợi ích**: Giảm storage, tăng chất lượng data

### 4. Background Summarization
- **Lý do**: Không block response, tăng performance
- **Implementation**: `asyncio.create_task()` cho summary generation

### 5. Phoenix Observability
- **Lý do**: Monitor và debug LLM applications
- **Features**: Full tracing, input/output logging, performance metrics

## Security Considerations

- **Local LLM**: Ollama chạy local, không gửi data ra ngoài
- **MCP Server**: Internal network, không expose ra internet
- **Phoenix**: Internal network, chỉ dùng cho monitoring

## Scalability

### Horizontal Scaling
- **Main App**: Có thể scale multiple instances
- **MCP Server**: Có thể scale multiple instances
- **Phoenix**: Single instance (có thể cluster)

### Vertical Scaling
- **Ollama**: Có thể dùng GPU để tăng tốc
- **Database**: Có thể tăng resources cho PostgreSQL

## Monitoring & Observability

### Phoenix Dashboard
- **URL**: http://localhost:6006
- **Features**:
  - Trace visualization
  - Performance metrics
  - Input/output inspection
  - Error tracking

### Logging
- **Format**: Structured logging với timestamps
- **Levels**: INFO, DEBUG, ERROR
- **Output**: Console + có thể config file logging

## Future Enhancements

1. **Multi-tenant Support**: Support nhiều users/organizations
2. **Advanced Tools**: Thêm tools khác (web scraping, database queries)
3. **Streaming Responses**: Support streaming cho real-time responses
4. **Caching**: Cache frequent queries để giảm LLM calls
5. **Analytics**: Advanced analytics trên Phoenix data
