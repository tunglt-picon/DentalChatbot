# Dental Chatbot Backend

Backend API for Dental Chatbot using FastAPI with Ollama LLM (free, no rate limits) and built-in web interface.

## Features

- ✅ **Built-in Web Interface**: Simple and clean chat interface with configuration page
- ✅ **OpenAI-Compatible API**: Complies with OpenAI API standard
- ✅ **Search Tool**: Uses DuckDuckGo (free, unlimited)
- ✅ **Guardrail System**: Automatically checks if questions belong to the dental field
- ✅ **LLM Provider**: Ollama (free, no rate limits, runs locally)
- ✅ **Configuration Page**: Web UI to configure models and search tools
- ✅ **Clean Architecture**: Implements Factory Pattern, MCP architecture

## Technology Stack

- **Framework**: FastAPI
- **LLM**: Ollama (free, no rate limits, runs locally)
- **Search Tool**: DuckDuckGo (free, unlimited)
- **Configuration**: `python-dotenv`, `pydantic-settings`

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
ollama pull llama3.2        # For guardrail and chat (~2GB)
ollama pull qwen2.5:7b      # Better Vietnamese support (~4.5GB, optional)
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

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` file:

```env
# Ollama Settings (Default - Recommended)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_GUARDRAIL_MODEL=llama3.2

```

### 6. Start Ollama (if not running)

```bash
ollama serve
```

## Running the Application

### Development mode

```bash
python main.py
```

or use uvicorn directly:

```bash
uvicorn main:app --reload
```

Server will run at: `http://localhost:8000`

### Access Web Interface

Open browser: `http://localhost:8000`

- **Chat Interface**: Main page for chatting
- **Configuration**: `/config` - Configure models and search tools

## Web Interface

### Chat Page (`/`)

- Chat with the dental assistant
- View chat history
- Continue previous conversations

### Configuration Page (`/config`)

Configure:
- **Chat Model**: Ollama model for generating responses
- **Guardrail Model**: Ollama model for checking if questions are dental-related

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
  "chat_id": "optional-chat-id"
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

## LLM Providers

### Ollama (Default - Recommended)

**Advantages:**
- ✅ Completely free
- ✅ No rate limits
- ✅ Runs locally (secure)
- ✅ Good Vietnamese support (qwen2.5:7b)

**Setup:**
```bash
ollama pull llama3.2
ollama pull qwen2.5:7b  # For better Vietnamese
```

**Configuration:**
```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
OLLAMA_GUARDRAIL_MODEL=llama3.2
```


## Docker Setup

### Using Docker Compose

```bash
docker-compose up -d
```

**Note**: Ollama needs to run on the host machine or in a separate container. Update `OLLAMA_BASE_URL` in docker-compose.yml if Ollama runs elsewhere.

### Dockerfile

```bash
docker build -t dental-chatbot .
docker run -p 8000:8000 dental-chatbot
```

## Error Handling

- **Rate Limit Errors**: Returns error message to user (no automatic fallback)
- **Search Tool Errors**: Returns error message (no automatic fallback)
- **Guardrail Rejection**: Returns friendly error message explaining the limitation

## Project Structure

```
DentalChatbot/
├── main.py                 # FastAPI application entry point
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── templates/              # HTML templates
│   ├── index.html         # Chat interface
│   └── config.html        # Configuration page
├── static/                 # Static files
│   ├── css/
│   │   └── style.css      # Styles
│   └── js/
│       ├── app.js         # Chat interface logic
│       └── config.js      # Configuration page logic
├── routers/
│   └── openai.py          # OpenAI-compatible API routes
├── services/
│   ├── chat_service.py    # Chat completion service
│   ├── guardrail.py       # Guardrail service
│   ├── llm_provider.py    # LLM provider abstraction
│   └── memory.py          # Memory service
└── tools/
    ├── base.py            # BaseSearchTool interface
    ├── duckduckgo_search.py  # DuckDuckGo search
    └── factory.py         # Search tool factory
```

## Troubleshooting

### Ollama Connection Error

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if not running
ollama serve
```

### Model Not Found

```bash
# Pull the required model
ollama pull llama3.2
ollama pull qwen2.5:7b
```

### Rate Limit Errors

- Ollama has no rate limits, check if Ollama is running

## License

MIT
