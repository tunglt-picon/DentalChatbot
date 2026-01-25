# MCP Server Documentation

## Tổng quan

MCP (Model Context Protocol) Server là một standalone HTTP server cung cấp Memory và Tool services cho Dental Chatbot application. Server sử dụng JSON-RPC 2.0 protocol để giao tiếp.

## Kiến trúc

```
┌─────────────────────────────────┐
│   MCP HTTP Server (Port 8001)    │
│   - FastAPI Application           │
│   - JSON-RPC 2.0 Protocol        │
└──────────────┬───────────────────┘
               │
       ┌───────┴────────┐
       │                 │
       ▼                 ▼
┌──────────────┐  ┌──────────────┐
│ Memory Server│  │ Tool Server  │
│ - Conversations│  │ - DuckDuckGo │
│ - Messages    │  │   Search     │
│ - Summary     │  │              │
└──────────────┘  └──────────────┘
```

## Đặc điểm

- **Standalone**: Hoàn toàn độc lập, không phụ thuộc main application code
- **Tools trong MCP**: Tools được implement trong MCP server, không phải main app
- **Code-Driven**: Tool selection do code quyết định, không phải LLM
- **Memory Compression**: Tự động summarize và compress old messages để giảm storage

## Endpoints

### Health & Info

#### GET `/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "servers": ["memory-server", "tool-server"]
}
```

#### GET `/servers`
List all available MCP servers.

**Response:**
```json
{
  "servers": [
    {
      "name": "memory-server",
      "capabilities": {
        "tools": [],
        "resources": [...],
        "prompts": []
      }
    },
    {
      "name": "tool-server",
      "capabilities": {
        "tools": [...],
        "resources": [],
        "prompts": []
      }
    }
  ]
}
```

#### GET `/servers/{server_name}/capabilities`
Get capabilities of a specific server.

**Response:**
```json
{
  "server_name": "memory-server",
  "capabilities": {
    "tools": [],
    "resources": [...],
    "prompts": []
  }
}
```

### JSON-RPC Endpoint

#### POST `/jsonrpc`
Main JSON-RPC 2.0 endpoint for all MCP operations.

**Request Format:**
```json
{
  "jsonrpc": "2.0",
  "method": "{server_name}/{method_name}",
  "params": {...},
  "id": 1
}
```

**Response Format:**
```json
{
  "jsonrpc": "2.0",
  "result": {...},
  "id": 1
}
```

**Error Response:**
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

---

## Memory Server Methods

### `memory/get_or_create`
Get existing conversation or create new one.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "memory-server/memory/get_or_create",
  "params": {
    "conversation_id": "chat_xxx"  // Optional
  },
  "id": 1
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "conversation_id": "chat_xxx"
  },
  "id": 1
}
```

### `memory/get_context`
Get conversation context (only recent messages for LLM context, old ones are summarized).

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "memory-server/memory/get_context",
  "params": {
    "conversation_id": "chat_xxx",
    "max_messages": 20  // Optional
  },
  "id": 2
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "messages": [
      {"role": "user", "content": "..."},
      {"role": "assistant", "content": "..."}
    ]
  },
  "id": 2
}
```

**Note**: Chỉ trả về 6 messages gần nhất (KEEP_RECENT_MESSAGES) để giảm context size cho LLM. Old messages đã được summarize. Full history vẫn được lưu và có thể lấy qua `memory/get_all_messages`.

### `memory/get_all_messages`
Get ALL messages in conversation (full history for display).

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "memory-server/memory/get_all_messages",
  "params": {
    "conversation_id": "chat_xxx"
  },
  "id": 2
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "messages": [
      {"role": "user", "content": "..."},
      {"role": "assistant", "content": "..."}
    ]
  },
  "id": 2
}
```

**Note**: Trả về TẤT CẢ messages (full history) để hiển thị. Full history luôn được lưu, không bị xóa khi compress.

### `memory/get_old_messages`
Get old messages that should be summarized (excludes recent messages).

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "memory-server/memory/get_old_messages",
  "params": {
    "conversation_id": "chat_xxx"
  },
  "id": 3
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "messages": [
      {"role": "user", "content": "..."},
      {"role": "assistant", "content": "..."}
    ],
    "total_count": 10
  },
  "id": 3
}
```

**Note**: Chỉ trả về old messages (trước 6 messages gần nhất). Nếu đã compress, sẽ trả về empty.

### `memory/get_or_create_summary`
Get existing summary or indicate that summary needs to be created.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "memory-server/memory/get_or_create_summary",
  "params": {
    "conversation_id": "chat_xxx",
    "old_messages": [...],
    "language": "vi"  // "vi" or "en"
  },
  "id": 4
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "summary": "Tóm tắt cuộc trò chuyện..."  // Empty if needs to be created
  },
  "id": 4
}
```

**Note**: Nếu summary chưa tồn tại, trả về empty string. Chat service sẽ tạo summary và gọi `memory/set_summary`.

### `memory/set_summary`
Set summary for conversation. This is a single summary variable that accumulates all previous responses.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "memory-server/memory/set_summary",
  "params": {
    "conversation_id": "chat_xxx",
    "summary": "Tóm tắt câu trả lời 1\n\nTóm tắt câu trả lời 2",
    "compress": false  // Not used anymore, kept for compatibility
  },
  "id": 5
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "status": "success",
    "conversation_id": "chat_xxx"
  },
  "id": 5
}
```

**Note**: 
- Summary là một biến duy nhất, được update sau mỗi response
- Summary chứa tất cả các câu trả lời trước đó đã được summarize
- Summary được dùng làm context cho câu hỏi tiếp theo
- Full history luôn được lưu (không bị xóa) để hiển thị

### `memory/add_message`
Add message to conversation.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "memory-server/memory/add_message",
  "params": {
    "conversation_id": "chat_xxx",
    "role": "user",  // "user", "assistant", or "system"
    "content": "Message content"
  },
  "id": 6
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "status": "success",
    "conversation_id": "chat_xxx"
  },
  "id": 6
}
```

### `memory/get_summary`
Get conversation summary text (if exists).

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "memory-server/memory/get_summary",
  "params": {
    "conversation_id": "chat_xxx"
  },
  "id": 7
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "summary": "Tóm tắt cuộc trò chuyện..."  // Empty if no summary
  },
  "id": 7
}
```

### `memory/clear`
Clear all messages from conversation (keeps conversation, deletes messages).

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "memory-server/memory/clear",
  "params": {
    "conversation_id": "chat_xxx"
  },
  "id": 8
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "status": "cleared",
    "conversation_id": "chat_xxx"
  },
  "id": 8
}
```

### `memory/delete`
Delete conversation completely.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "memory-server/memory/delete",
  "params": {
    "conversation_id": "chat_xxx"
  },
  "id": 9
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "status": "deleted",
    "conversation_id": "chat_xxx"
  },
  "id": 9
}
```

### `resources/list`
List all conversation resources.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "memory-server/resources/list",
  "params": {},
  "id": 10
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "resources": [
      {
        "uri": "memory://conversation/chat_xxx",
        "name": "Conversation chat_xxx",
        "description": "Conversation history for chat_xxx",
        "mimeType": "application/json"
      }
    ]
  },
  "id": 10
}
```

### `resources/read`
Read conversation resource by URI.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "memory-server/resources/read",
  "params": {
    "uri": "memory://conversation/chat_xxx"
  },
  "id": 11
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "contents": [
      {
        "uri": "memory://conversation/chat_xxx",
        "mimeType": "application/json",
        "text": "{'messages': [...], 'summary': {...}}"
      }
    ]
  },
  "id": 11
}
```

---

## Tool Server Methods

### `tools/list`
List available tools.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tool-server/tools/list",
  "params": {},
  "id": 12
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "tools": [
      {
        "name": "duckduckgo_search",
        "description": "Search using DuckDuckGo (free, unlimited, privacy-focused). Returns up to 5 relevant search results with titles, content snippets, and links.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "query": {
              "type": "string",
              "description": "Search query - should be specific and descriptive for best results"
            }
          },
          "required": ["query"]
        }
      }
    ]
  },
  "id": 12
}
```

### `tools/call`
Execute a tool (code-driven selection).

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tool-server/tools/call",
  "params": {
    "name": "duckduckgo_search",
    "arguments": {
      "query": "sâu răng nguyên nhân"
    }
  },
  "id": 13
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Title: ...\nContent: ...\nLink: ...\n---\n..."
      }
    ]
  },
  "id": 13
}
```

---

## Summary Accumulation

### Cơ chế hoạt động

**Single Summary Variable**: Một biến summary duy nhất được dùng để lưu tất cả các câu trả lời đã được summarize.

### Flow

```
Câu hỏi 1:
  - Get summary: "" (empty)
  - Response 1
  - Summarize Response 1 → "Summary 1"
  - Save summary = "Summary 1"

Câu hỏi 2:
  - Get summary: "Summary 1"
  - Use summary as context
  - Response 2
  - Summarize Response 2 → "Summary 2"
  - Update summary = "Summary 1\n\nSummary 2"
  - Save summary

Câu hỏi 3:
  - Get summary: "Summary 1\n\nSummary 2"
  - Use summary as context
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
- **Full history**: Full history luôn được lưu để hiển thị (via `get_all_messages()`)

---

## Error Codes

| Code | Meaning |
|------|---------|
| -32700 | Parse error |
| -32600 | Invalid request |
| -32601 | Method not found |
| -32602 | Invalid params |
| -32603 | Internal error |
| -32001 | Resource not found |
| -32002 | Tool execution error |

---

## Architecture Details

### Standalone Design

- **MCP Server**: Hoàn toàn độc lập, có thể deploy riêng
- **Tools trong MCP**: Tools được implement trong `mcp/servers/tools/`
- **Main App Client**: Sử dụng `clients/mcp_client.py` để giao tiếp (HTTP only)
- **No Code Dependency**: Main app không import từ `mcp/` folder

### Code-Driven Tool Selection

- Tools được chọn bởi code logic, không phải LLM
- Main app quyết định tool nào được gọi
- Predictable và reliable

### Memory Compression

- Tự động summarize old messages
- Xóa old messages sau khi summarize
- Chỉ giữ summary + recent messages
- Giảm storage và context size

---

## Running MCP Server

### Development

```bash
# Option 1: Python module
python -m mcp.server

# Option 2: Run script
python run_mcp_server.py

# Option 3: Uvicorn directly
uvicorn mcp.server:app --host 0.0.0.0 --port 8001 --reload
```

### Production

```bash
uvicorn mcp.server:app --host 0.0.0.0 --port 8001 --workers 4
```

### Docker

```bash
docker-compose up mcp-server
```

---

## Configuration

### Environment Variables

- `MCP_SERVER_URL`: Base URL của MCP server (default: `http://localhost:8001`)

### Memory Compression Settings

Trong `services/memory.py`:
- `KEEP_RECENT_MESSAGES = 6`: Số messages gần nhất giữ lại (full)
- `SUMMARIZE_THRESHOLD = 10`: Ngưỡng bắt đầu summarize
- `COMPRESS_AFTER_SUMMARY = True`: Xóa old messages sau summarize

---

## Testing

### Health Check

```bash
curl http://localhost:8001/health
```

### List Servers

```bash
curl http://localhost:8001/servers
```

### Test Memory Server

```bash
# Create conversation
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "memory-server/memory/get_or_create",
    "params": {},
    "id": 1
  }'
```

### Test Tool Server

```bash
# List tools
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tool-server/tools/list",
    "params": {},
    "id": 1
  }'
```

---

## Troubleshooting

### Server không start

```bash
# Check port 8001 đã được sử dụng chưa
lsof -i :8001

# Check logs
python -m mcp.server
```

### Connection errors

```bash
# Check MCP server đang chạy
curl http://localhost:8001/health

# Check main app config
echo $MCP_SERVER_URL
```

### Memory compression issues

- Check `KEEP_RECENT_MESSAGES` setting
- Check logs để xem summary có được tạo không
- Verify old messages đã bị xóa sau summarize
