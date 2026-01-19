# Dental Chatbot Backend

Backend API for Dental Chatbot using FastAPI, fully compatible with OpenAI API standard for integration with Open WebUI interface.

## Features

- ✅ **OpenAI-Compatible API**: Complies with OpenAI API standard, easy integration with Open WebUI
- ✅ **Dual Search Strategies**: Supports 2 flexible search strategies:
  - `dental-google`: Uses Google ADK google_search tool (Gemini 2.0+ with Google Search grounding)
  - `dental-duckduckgo`: Uses DuckDuckGo (free, unlimited)
- ✅ **Guardrail System**: Automatically checks if questions belong to the dental field
- ✅ **Fallback Mechanism**: Automatically switches from Google Search to DuckDuckGo if config is missing or errors occur
- ✅ **Clean Architecture**: Implements Factory Pattern, separates routers, services, tools

## Technology Stack

- **Framework**: FastAPI
- **LLM**: Google Gemini (default: `gemini-2.5-flash`)
- **Search Tools**:
  - `google-adk`: Google Agent Development Kit with google_search tool
  - `duckduckgo-search`: Python library for DuckDuckGo
- **Configuration**: `python-dotenv`, `pydantic-settings`

## Installation

### 1. Clone repository

```bash
git clone <repository-url>
cd DentalChatbot
```

### 2. Create virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` file with your information:

```env
# Google Gemini API for LLM (Required)
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_BASE_MODEL=gemini-2.5-flash

# Google Search now uses ADK google_search tool (requires Gemini 2.0+ model)
# No additional API keys needed for Google Search - it uses the same GOOGLE_API_KEY
```

### 5. Get API Keys

#### Google Gemini API Key (Required)
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy it to `GOOGLE_API_KEY`

#### Google Search (via ADK)

Google Search is now powered by Google ADK's `google_search` tool, which uses Gemini 2.0+ models with built-in Google Search grounding. 

**Requirements**:
- Gemini 2.0+ model (default: `gemini-2.5-flash`)
- Google ADK package (automatically installed via `requirements.txt`)
- Uses the same `GOOGLE_API_KEY` as the LLM

**Note**: The Google Search tool requires Gemini 2.0+ models. If your model doesn't support it, the system will automatically fallback to DuckDuckGo.

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

### Production mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### 1. GET `/v1/models`

List available models (OpenAI-compatible).

**Response:**
```json
{
  "object": "list",
  "data": [
    {"id": "dental-google", "object": "model", "owned_by": "me"},
    {"id": "dental-duckduckgo", "object": "model", "owned_by": "me"}
  ]
}
```

### 2. POST `/v1/chat/completions`

Handle chat completion request.

**Request Body:**
```json
{
  "model": "dental-google",
  "messages": [
    {"role": "user", "content": "What causes tooth decay?"}
  ],
  "temperature": 0.7
}
```

**Response:**
```json
{
  "id": "chatcmpl-123456",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "dental-google",
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
  }
}
```

### 3. GET `/`

Root endpoint - API information

### 4. GET `/health`

Health check endpoint

## Connecting to Open WebUI

1. Open Open WebUI
2. Go to Settings → Connections → External API
3. Add a new connection with:
   - **API Base URL**: `http://localhost:8000` (or your server URL)
   - **API Type**: OpenAI Compatible
4. In the Model menu, you will see 2 options:
   - `dental-google`
   - `dental-duckduckgo`
5. Select a model and start chatting!

## Processing Workflow

1. **Guardrail Check**: Gemini Flash checks if the question belongs to the dental field
2. **Tool Selection**: Based on model name to select search tool (Factory Pattern)
3. **Search Execution**: Perform search and retrieve results
4. **LLM Summarization**: Gemini reads search results and answers the question

## Project Structure

```
DentalChatbot/
├── main.py                 # FastAPI application entry point
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore file
├── routers/
│   ├── __init__.py
│   └── openai.py          # OpenAI-compatible API routes
├── services/
│   ├── __init__.py
│   ├── guardrail.py       # Guardrail service (domain check)
│   └── chat_service.py    # Chat completion service
└── tools/
    ├── __init__.py
    ├── base.py            # BaseSearchTool interface
    ├── google_search.py   # Google ADK google_search tool implementation
    ├── duckduckgo_search.py  # DuckDuckGo search implementation
    └── factory.py         # Search tool factory
```

## Design Patterns

### Factory Pattern

`SearchToolFactory` uses Factory Pattern to create search tool based on model name:

```python
tool = SearchToolFactory.create_search_tool("dental-google")
results = await tool.search(query)
```

### Fallback Mechanism

If Google Search tool is not available (e.g., ADK not installed) or encounters an error, the system automatically falls back to DuckDuckGo:

```python
if model == "dental-google":
    tool = GoogleSearchTool()
    if not tool.is_configured():
        # Auto fallback to DuckDuckGo
        tool = DuckDuckGoSearchTool()
```

## Troubleshooting

### Error: "Google Search API is not configured"

**Solution**: This is a normal warning. The system will automatically switch to DuckDuckGo. If you want to use Google Search, ensure you're using a Gemini 2.0+ model (e.g., `gemini-2.5-flash`) and that `google-adk` package is installed.

### Error: "User message not found"

**Solution**: Ensure the request body has at least one message with `role: "user"`.

### Error: "Sorry, I can only answer questions related to the dental field"

**Solution**: This is a response from the guardrail. The system can only answer questions related to dentistry.

## Development

### Run tests (if available)

```bash
pytest
```

### Format code

```bash
black .
```

### Lint code

```bash
flake8 .
```

## License

MIT License

## Contributors

- Initial implementation by AI Assistant

## Changelog

### v1.0.0
- Initial release
- OpenAI-compatible API
- Dual search strategies (Google & DuckDuckGo)
- Guardrail system
- Fallback mechanism
