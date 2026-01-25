# Dental Chatbot Backend

Backend API for Dental Chatbot using FastAPI with Ollama LLM (free, no rate limits) and built-in web interface. Implements MCP (Model Context Protocol) architecture with standalone server.

## Features

- ✅ **Built-in Web Interface**: Simple and clean chat interface with configuration page
- ✅ **OpenAI-Compatible API**: Complies with OpenAI API standard
- ✅ **MCP Architecture**: Standalone MCP server with Memory and Tool services
- ✅ **Search Tool**: DuckDuckGo search (free, unlimited) - implemented in MCP server
- ✅ **Guardrail System**: Automatically checks if questions belong to the dental field
- ✅ **LLM Provider**: Ollama (free, no rate limits, runs locally)
- ✅ **Configuration Page**: Web UI to configure models
- ✅ **Code-Driven Tool Selection**: Tools are selected by code logic, not LLM

## Technology Stack

- **Framework**: FastAPI
- **LLM**: Ollama (free, no rate limits, runs locally)
- **Search Tool**: DuckDuckGo (free, unlimited)
- **Architecture**: MCP (Model Context Protocol) with standalone HTTP server
- **Configuration**: `python-dotenv`, `pydantic-settings`

## Architecture

```
┌─────────────────────────────────┐
│   Main Application (Port 8000)   │
│   - FastAPI Backend              │
│   - Web Interface                │
│   - OpenAI-Compatible API        │
└──────────────┬───────────────────┘
               │ HTTP (JSON-RPC)
               ▼
┌─────────────────────────────────┐
│   MCP Server (Port 8001)         │
│   - Memory Server                │
│   - Tool Server                  │
│   - Standalone, Independent      │
└─────────────────────────────────┘
```

### MCP Server Components

- **Memory Server**: Manages conversation history
- **Tool Server**: Provides search tools (DuckDuckGo)
  - Tools are implemented within MCP server
  - Tool selection is code-driven (not LLM-driven)

## Installation

### 1. Clone repository

```bash
git clone <repository-url>
cd DentalChatbot
```

### 2. Install Ollama (Required)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull recommended models
ollama pull phi3:latest        # For guardrail (~2.2GB)
ollama pull qwen2.5:7b-instruct  # For chat responses (~4.7GB, better Vietnamese)
# Alternative lighter models:
ollama pull qwen2.5:3b-instruct  # Lighter chat model (~1.9GB)
ollama pull llama3.2:latest      # Alternative (~2.0GB)
```

### 3. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Create `.env` file:

```env
# Ollama Settings (Default - Recommended)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct
OLLAMA_GUARDRAIL_MODEL=phi3:latest

# MCP Server Settings
MCP_SERVER_URL=http://localhost:8001
```

### 6. Start Ollama (if not running)

```bash
ollama serve
```

## Running the Application

### 1. Start MCP Server (Required - runs on port 8001)

MCP Server is a standalone service providing Memory and Tool services:

```bash
# Option 1: Using Python module
python -m mcp.server

# Option 2: Using run script
python run_mcp_server.py

# Option 3: Using uvicorn directly
uvicorn mcp.server:app --host 0.0.0.0 --port 8001 --reload
```

MCP Server will run at: `http://localhost:8001`

**Endpoints**:
- `POST /jsonrpc`: JSON-RPC endpoint for MCP protocol
- `GET /health`: Health check
- `GET /servers`: List available servers
- `GET /servers/{server_name}/capabilities`: Get server capabilities

**MCP Servers**:
- `memory-server`: Conversation history management
- `tool-server`: Search tools (DuckDuckGo)

### 2. Start Main Application (runs on port 8000)

```bash
python main.py
```

or use uvicorn directly:

```bash
uvicorn main:app --reload
```

Main application will run at: `http://localhost:8000`

**Note**: Main application requires MCP Server to be running.

### Access Web Interface

Open browser: `http://localhost:8000`

- **Chat Interface**: Main page for chatting
- **Configuration**: `/config` - Configure models

## Web Interface

### Chat Page (`/`)

- Chat with the dental assistant
- View chat history
- Continue previous conversations
- Automatic guardrail: Non-dental questions are rejected with friendly message

### Configuration Page (`/config`)

Configure:
- **Chat Model**: Ollama model for generating responses
  - Recommended: `qwen2.5:7b-instruct` (best Vietnamese support)
  - Alternative: `qwen2.5:3b-instruct` (lighter), `llama3.2:latest`
- **Guardrail Model**: Ollama model for checking if questions are dental-related
  - Recommended: `phi3:latest` (fast and efficient)
  - Alternative: `qwen2.5:3b-instruct`, `llama3.2:latest`

## API Endpoints

### 1. GET `/v1/models`

List available models (OpenAI-compatible).

**Response:**
```json
{
  "object": "list",
  "data": [
    {"id": "dental-duckduckgo", "object": "model", "owned_by": "me"}
  ]
}
```

### 2. POST `/v1/chat/completions`

Handle chat completion request.

**Request Body:**
```json
{
  "model": "dental-duckduckgo",
  "messages": [
    {"role": "user", "content": "What causes tooth decay?"}
  ],
  "chat_id": "optional-chat-id",
  "config": {
    "ollama_model": "qwen2.5:7b-instruct",
    "ollama_guardrail_model": "phi3:latest"
  }
}
```

**Response:**
```json
{
  "id": "chatcmpl-123456",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "dental-duckduckgo",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Tooth decay is caused by..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0
  },
  "system_fingerprint": "conversation-id"
}
```

### 3. GET `/config`

Configuration page (web interface).

### 4. GET `/health`

Health check endpoint.

## MCP Protocol

### Memory Server Methods

- `memory/get_or_create`: Get or create conversation
- `memory/get_context`: Get conversation context (messages)
- `memory/add_message`: Add message to conversation
- `memory/get_summary`: Get conversation summary
- `memory/clear`: Clear conversation messages
- `memory/delete`: Delete conversation
- `resources/list`: List conversation resources
- `resources/read`: Read conversation resource

### Tool Server Methods

- `tools/list`: List available tools
- `tools/call`: Execute tool (code-driven selection)

**Available Tools**:
- `duckduckgo_search`: Search using DuckDuckGo

### Example MCP Request

```bash
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tool-server/tools/call",
    "params": {
      "name": "duckduckgo_search",
      "arguments": {"query": "dental health"}
    },
    "id": 1
  }'
```

## LLM Providers

### Ollama (Default - Recommended)

**Advantages:**
- ✅ Completely free
- ✅ No rate limits
- ✅ Runs locally (secure)
- ✅ Good Vietnamese support (qwen2.5:7b-instruct)

**Recommended Models**:

**For Chat Responses**:
- `qwen2.5:7b-instruct` (4.7GB) - Best quality, excellent Vietnamese support
- `qwen2.5:3b-instruct` (1.9GB) - Lighter alternative
- `llama3.2:latest` (2.0GB) - Good alternative

**For Guardrail**:
- `phi3:latest` (2.2GB) - Fast and efficient
- `qwen2.5:3b-instruct` (1.9GB) - Alternative
- `llama3.2:latest` (2.0GB) - Alternative

**Configuration:**
```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:7b-instruct
OLLAMA_GUARDRAIL_MODEL=phi3:latest
```

## Docker Setup

### Using Docker Compose

```bash
docker-compose up -d
```

This will start:
- MCP Server on port 8001
- Main Application on port 8000

**Note**: Ollama needs to run on the host machine or in a separate container. Update `OLLAMA_BASE_URL` in docker-compose.yml if Ollama runs elsewhere.

### Dockerfile

```bash
docker build -t dental-chatbot .
docker run -p 8000:8000 dental-chatbot
```

## Error Handling

- **Guardrail Rejection**: Returns friendly message, question NOT saved to memory
- **Search Tool Errors**: Returns error message (no automatic fallback)
- **LLM Generation Errors**: Returns error message
- **Memory Server Errors**: Returns error message

## Project Structure

```
DentalChatbot/
├── main.py                 # FastAPI application entry point
├── config.py               # Configuration management
├── run_mcp_server.py       # MCP server runner script
├── requirements.txt        # Python dependencies
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile              # Docker configuration
│
├── mcp/                    # MCP (Model Context Protocol) implementation
│   ├── __init__.py
│   ├── __main__.py         # MCP server entry point
│   ├── server.py            # MCP HTTP server (FastAPI)
│   ├── base.py             # MCP base classes (MCPServer, MCPClient, MCPHost)
│   ├── protocol.py         # JSON-RPC 2.0 protocol
│   └── servers/            # MCP servers
│       ├── __init__.py
│       ├── memory_server.py    # Memory/conversation history server
│       ├── tool_server.py      # Tool server
│       └── tools/              # Tools implementation (in MCP server)
│           ├── __init__.py
│           └── duckduckgo_search.py  # DuckDuckGo search tool
│
├── routers/                # API routes
│   └── openai.py          # OpenAI-compatible API routes
│
├── services/               # Business logic services
│   ├── __init__.py
│   ├── chat_service.py    # Chat completion service (orchestrates flow)
│   ├── guardrail.py       # Guardrail service (dental-related check)
│   ├── llm_provider.py    # LLM provider abstraction (Ollama)
│   ├── memory.py          # Memory service (conversation management)
│   └── prompts.py         # Prompt templates
│
├── templates/              # HTML templates
│   ├── index.html         # Chat interface
│   └── config.html        # Configuration page
│
└── static/                 # Static files
    ├── css/
    │   └── style.css      # Styles
    └── js/
        ├── app.js         # Chat interface logic
        └── config.js      # Configuration page logic
```

## Key Design Decisions

1. **MCP Standalone Server**: Tools and memory are in standalone MCP server, not in main app
2. **Code-Driven Tool Selection**: Tools are selected by code logic, not by LLM
3. **Guardrail Before Memory**: Non-dental questions are rejected before saving to memory
4. **Single Source of Truth**: Conversation history is stored in MCP Memory Server
5. **Frontend Sends New Message Only**: Backend retrieves full context from memory

## Troubleshooting

### Ollama Connection Error

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if not running
ollama serve
```

### MCP Server Connection Error

```bash
# Check if MCP server is running
curl http://localhost:8001/health

# Start MCP server
python -m mcp.server
```

### Model Not Found

```bash
# Pull the required models
ollama pull phi3:latest
ollama pull qwen2.5:7b-instruct
```

### Import Errors

If you see import errors related to `tools`, make sure you're using the refactored version where tools are in `mcp/servers/tools/`, not in root `tools/` folder.

## Development

### Running in Development Mode

```bash
# Terminal 1: Start MCP Server
uvicorn mcp.server:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2: Start Main Application
uvicorn main:app --reload
```

### Testing MCP Server

```bash
# Health check
curl http://localhost:8001/health

# List servers
curl http://localhost:8001/servers

# List tools
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tool-server/tools/list", "id": 1}'
```

## License

MIT
