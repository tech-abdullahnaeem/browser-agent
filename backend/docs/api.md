# Browser Agent — API Documentation

## Base URL

```
http://localhost:8000
```

## REST Endpoints

### Health Check

```
GET /health
```

**Response:**
```json
{"status": "ok"}
```

---

### Tasks

#### Submit a Task

```
POST /api/tasks
```

**Request Body:**
```json
{
  "task": "Go to google.com and search for 'AI agents'",
  "context": "Currently on example.com"  // optional
}
```

**Response (201):**
```json
{
  "task_id": "a1b2c3d4e5f6...",
  "status": "pending"
}
```

#### List Tasks

```
GET /api/tasks?limit=50&offset=0
```

**Response:**
```json
{
  "tasks": [
    {
      "task_id": "...",
      "task": "Go to google.com",
      "status": "completed",
      "total_steps": 3,
      "final_result": "The title is Google",
      "error": null,
      "created_at": "2026-03-03T14:00:00Z",
      "duration_seconds": 12.5
    }
  ],
  "total": 1
}
```

#### Get Task Detail

```
GET /api/tasks/{task_id}
```

**Response:**
```json
{
  "task_id": "...",
  "task": "Go to google.com",
  "status": "completed",
  "steps": [
    {
      "step_number": 1,
      "action": "navigate",
      "element": "https://google.com",
      "reasoning": "Navigate to Google",
      "thinking": "I need to go to google.com first",
      "success": true,
      "error": null,
      "timestamp": "2026-03-03T14:00:01Z"
    }
  ],
  "final_result": "The title is Google",
  "error": null,
  "created_at": "2026-03-03T14:00:00Z",
  "updated_at": "2026-03-03T14:00:12Z",
  "duration_seconds": 12.5,
  "total_steps": 3,
  "model_used": "gemini-2.5-pro"
}
```

#### Cancel a Task

```
DELETE /api/tasks/{task_id}
```

**Response:**
```json
{
  "task_id": "...",
  "cancelled": true,
  "message": "Task cancellation requested"
}
```

---

### Configuration

#### Get Current Config

```
GET /api/config
```

**Response:**
```json
{
  "max_steps": 50,
  "max_failures": 5,
  "use_vision": true,
  "headless": false,
  "wait_between_actions": 0.5,
  "max_actions_per_step": 5,
  "enable_planning": true,
  "flash_model": "gemini-2.5-pro",
  "pro_model": "gemini-2.5-pro"
}
```

#### Update Config

```
PUT /api/config
```

**Request Body (partial — only include fields to update):**
```json
{
  "max_steps": 20,
  "headless": true
}
```

**Response:** Updated full config object.

---

## WebSocket Endpoint

### Connect to Task Stream

```
WS /ws/{task_id}
```

Connect to receive real-time events as the agent executes a task.

### Event Types

All events have this structure:
```json
{
  "type": "event_type",
  "task_id": "...",
  "timestamp": "2026-03-03T14:00:00Z",
  ...event-specific fields
}
```

#### `status` — Task status change
```json
{
  "type": "status",
  "task_id": "...",
  "status": "running"
}
```
Statuses: `pending`, `running`, `completed`, `failed`, `cancelled`

#### `step` — Agent step completed
```json
{
  "type": "step",
  "task_id": "...",
  "data": {
    "step_number": 1,
    "action": "click",
    "element": "Search button",
    "reasoning": "Click the search button to submit the query",
    "thinking": "I see the search button, I should click it",
    "success": true,
    "error": null,
    "timestamp": "2026-03-03T14:00:02Z"
  }
}
```

#### `plan` — Planning step generated
```json
{
  "type": "plan",
  "task_id": "...",
  "plan": "1. Navigate to google.com\n2. Type search query\n3. Click search"
}
```

#### `screenshot` — Screenshot captured
```json
{
  "type": "screenshot",
  "task_id": "...",
  "b64": "iVBORw0KGgoAAAANS..."
}
```

#### `done` — Task finished
```json
{
  "type": "done",
  "task_id": "...",
  "data": {
    "task_id": "...",
    "task": "Go to google.com",
    "status": "completed",
    "final_result": "The title is Google",
    "steps": [...],
    "duration_seconds": 12.5,
    "total_steps": 3,
    "model_used": "gemini-2.5-pro"
  }
}
```

#### `error` — Error occurred
```json
{
  "type": "error",
  "task_id": "...",
  "message": "Agent execution failed: ..."
}
```

### Client Keepalive

Send `"ping"` text messages to keep the connection alive. Server responds with:
```json
{"type": "pong"}
```

### Behaviour

- **Task pending/running:** Stream events in real-time. Connection stays open until task completes.
- **Task already completed:** Full history is replayed, then connection closes with code `1000`.
- **Task not found:** Error event sent, connection closes with code `4004`.

---

## Interactive Docs

FastAPI auto-generates interactive API documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
