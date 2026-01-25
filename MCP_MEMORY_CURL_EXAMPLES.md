# MCP Memory Server - CURL Examples

Các lệnh curl để tương tác với Memory Server qua JSON-RPC 2.0 protocol.

**Base URL**: `http://localhost:8001/jsonrpc`

**Method Format**: `memory-server/{method_name}`

---

## 1. Health Check

```bash
curl http://localhost:8001/health
```

---

## 2. List All Servers

```bash
curl http://localhost:8001/servers
```

---

## 3. Get Server Capabilities

```bash
curl http://localhost:8001/servers/memory-server/capabilities
```

---

## 4. List All Conversations (Resources)

```bash
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "memory-server/resources/list",
    "params": {},
    "id": 1
  }'
```

---

## 5. Read Conversation Resource

```bash
# Thay {conversation_id} bằng ID thực tế
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "memory-server/resources/read",
    "params": {
      "uri": "memory://conversation/chat_1234567890_abc123"
    },
    "id": 2
  }'
```

---

## 6. Get or Create Conversation

### Tạo conversation mới (không truyền conversation_id)

```bash
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "memory-server/memory/get_or_create",
    "params": {},
    "id": 3
  }'
```

### Lấy hoặc tạo conversation với ID cụ thể

```bash
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "memory-server/memory/get_or_create",
    "params": {
      "conversation_id": "chat_1234567890_abc123"
    },
    "id": 4
  }'
```

---

## 7. Add Message to Conversation

```bash
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "memory-server/memory/add_message",
    "params": {
      "conversation_id": "chat_1234567890_abc123",
      "role": "user",
      "content": "Tôi muốn biết về sâu răng"
    },
    "id": 5
  }'
```

### Thêm assistant message

```bash
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "memory-server/memory/add_message",
    "params": {
      "conversation_id": "chat_1234567890_abc123",
      "role": "assistant",
      "content": "Sâu răng là tình trạng phá hủy men răng do vi khuẩn..."
    },
    "id": 6
  }'
```

---

## 8. Get Conversation Context

### Lấy tất cả messages

```bash
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "memory-server/memory/get_context",
    "params": {
      "conversation_id": "chat_1234567890_abc123"
    },
    "id": 7
  }'
```

### Lấy N messages gần nhất (ví dụ: 5 messages)

```bash
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "memory-server/memory/get_context",
    "params": {
      "conversation_id": "chat_1234567890_abc123",
      "max_messages": 5
    },
    "id": 8
  }'
```

---

## 9. Get Conversation Summary

```bash
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "memory-server/memory/get_summary",
    "params": {
      "conversation_id": "chat_1234567890_abc123"
    },
    "id": 9
  }'
```

**Response sẽ chứa:**
- `conversation_id`: ID của conversation
- `message_count`: Số lượng messages
- `created_at`: Thời gian tạo
- `updated_at`: Thời gian cập nhật cuối

---

## 10. Clear Conversation (Xóa tất cả messages)

```bash
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "memory-server/memory/clear",
    "params": {
      "conversation_id": "chat_1234567890_abc123"
    },
    "id": 10
  }'
```

---

## 11. Delete Conversation (Xóa hoàn toàn)

```bash
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "memory-server/memory/delete",
    "params": {
      "conversation_id": "chat_1234567890_abc123"
    },
    "id": 11
  }'
```

---

## Example: Complete Workflow

### Bước 1: Tạo conversation mới

```bash
CONV_ID=$(curl -s -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "memory-server/memory/get_or_create",
    "params": {},
    "id": 1
  }' | jq -r '.result.conversation_id')

echo "Conversation ID: $CONV_ID"
```

### Bước 2: Thêm user message

```bash
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"method\": \"memory-server/memory/add_message\",
    \"params\": {
      \"conversation_id\": \"$CONV_ID\",
      \"role\": \"user\",
      \"content\": \"Tôi muốn biết về sâu răng\"
    },
    \"id\": 2
  }"
```

### Bước 3: Thêm assistant message

```bash
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"method\": \"memory-server/memory/add_message\",
    \"params\": {
      \"conversation_id\": \"$CONV_ID\",
      \"role\": \"assistant\",
      \"content\": \"Sâu răng là tình trạng phá hủy men răng do vi khuẩn trong miệng tạo ra axit...\"
    },
    \"id\": 3
  }"
```

### Bước 4: Lấy context

```bash
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"method\": \"memory-server/memory/get_context\",
    \"params\": {
      \"conversation_id\": \"$CONV_ID\"
    },
    \"id\": 4
  }" | jq '.'
```

### Bước 5: Lấy summary

```bash
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"method\": \"memory-server/memory/get_summary\",
    \"params\": {
      \"conversation_id\": \"$CONV_ID\"
    },
    \"id\": 5
  }" | jq '.'
```

---

## Response Format

### Success Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "conversation_id": "chat_1234567890_abc123"
  },
  "id": 1
}
```

### Error Response

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

## Tips

1. **Pretty Print JSON**: Thêm `| jq '.'` vào cuối lệnh curl để format JSON đẹp hơn
2. **Save Response**: Thêm `> response.json` để lưu response vào file
3. **Check Server Status**: Luôn kiểm tra `/health` trước khi test các methods
4. **Conversation ID Format**: Thường có format `chat_{timestamp}_{random_string}`
