# 🤖 Browser Agent — AI-Powered Browser Automation & QA Testing

> **Intelligent browser automation meets human oversight.** A production-ready platform combining Google Gemini 2.5 Pro, real browser control (Playwright), persistent memory, and human-in-the-loop safety gates.

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green)](https://fastapi.tiangolo.com/)
[![Chrome Extension](https://img.shields.io/badge/Chrome%20MV3-Extension-orange)](https://developer.chrome.com/docs/extensions/)
[![Tests](https://img.shields.io/badge/Tests-156%20Passing-brightgreen)](#testing)
[![License](https://img.shields.io/badge/License-MIT-blue)](#license)

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage](#-usage)
  - [CLI](#1-command-line-interface)
  - [REST API](#2-rest-api)
  - [Chrome Extension](#3-chrome-extension)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [API Reference](#-api-reference)
- [Testing](#-testing)
- [Advanced Topics](#-advanced-topics)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## ✨ Features

### 🧠 **Intelligent Automation**
- ✅ **Natural language task execution** — Describe what you want, AI does it
- ✅ **Multi-step reasoning** — Plans complex workflows autonomously
- ✅ **Vision-integrated decisions** — Analyzes page screenshots for understanding
- ✅ **Fallback & recovery** — Auto-handles failures gracefully
- ✅ **Real browser control** — Actual Chromium browser, not a simulator

### 🔒 **Safety & Oversight**
- ✅ **Destructive action detection** — Flags risky operations (buy, delete, submit)
- ✅ **Human-in-the-loop (HITL)** — User approval dialogs for sensitive actions
- ✅ **Audit logging** — Complete trail of every action taken
- ✅ **Domain filtering** — Allow/block list for navigation
- ✅ **Auto-approve whitelist** — Trusted domains skip confirmation

### 🧠 **Memory & Learning**
- ✅ **Persistent task history** — SQLite storage of all executions
- ✅ **Semantic search** — Find similar past tasks via ChromaDB embeddings
- ✅ **Context injection** — Agent learns from previous executions
- ✅ **Encrypted vault** — Fernet AES-128 encryption for sensitive data
- ✅ **Auto-fill forms** — Fill forms using stored credentials

### 🧪 **QA & Testing Tools** (12 built-in)
- ✅ **Accessibility auditing** — WCAG compliance checks
- ✅ **Performance metrics** — Load times, Core Web Vitals
- ✅ **SEO validation** — Meta tags, structured data
- ✅ **Error detection** — Console errors, broken links
- ✅ **Form validation** — Input rules, required fields
- ✅ **Site crawling** — Discover and map page topology
- ✅ **Interactive testing** — Button/form/modal checks
- ✅ **Report generation** — Comprehensive audit reports

### 🎯 **Real-Time Monitoring**
- ✅ **WebSocket streaming** — Step-by-step progress via WS events
- ✅ **Live UI updates** — Extension sidepanel updates in real-time
- ✅ **Visual highlighting** — Agent targets elements marked on page
- ✅ **Progress tracking** — Step counter, reasoning, screenshots

### 🌐 **Chrome Extension UI**
- ✅ **Command Palette (CMD+K)** — Floating task input overlay
- ✅ **Sidebar** — Task history & live monitoring
- ✅ **Context extraction** — Page meta, console, a11y analysis
- ✅ **HITL dialogs** — In-place confirmation prompts
- ✅ **Backend status** — Connectivity indicator

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  User Interface Layer                    │
├────────────────────────────┬────────────────────────────┤
│   Chrome Extension (React)  │   Browser (Playwright)     │
│  - Command Palette         │   - Real Chrome instance   │
│  - Sidebar + TaskList      │   - Page interaction       │
│  - Context extractor       │   - Screenshot capture     │
└────────────────────────────┴────────────────────────────┘
           │                           │
           └──────────┬────────────────┘
                      │ (WebSocket / REST)
         ┌────────────▼────────────────┐
         │   FastAPI Backend (Port 8000) │
         ├────────────────────────────┤
         │  • REST API (/api/tasks)   │
         │  • WebSocket (/ws/{id})    │
         │  • Config routes           │
         │  • Vault API               │
         └────────────┬────────────────┘
                      │
         ┌────────────▼──────────────────────┐
         │    Core Orchestration Layer        │
         ├────────────────────────────────────┤
         │  BrowserAgentRunner                │
         │  ├── Task planning (Gemini 2.5P)   │
         │  ├── Safety gate (HITL)            │
         │  ├── Audit logging                 │
         │  └── Memory injection              │
         └────────────┬──────────────────────┘
                      │
         ┌────────────▼──────────────────────┐
         │  browser-use Agent                 │
         ├────────────────────────────────────┤
         │  • LLM: Gemini 2.5 Pro             │
         │  • Tools: 37 builtin + custom      │
         │  • Vision integration              │
         │  • Max 50 steps per task           │
         └────────────┬──────────────────────┘
                      │
         ┌────────────▼──────────────────────┐
         │  Playwright + Chromium             │
         ├────────────────────────────────────┤
         │  • Real browser control            │
         │  • DOM manipulation                │
         │  • Screenshot/video capture        │
         └────────────────────────────────────┘

Data Layer (Persistent):
┌──────────────────────────────────────────────────────┐
│  SQLite (Tasks, Steps, Audit trail)                  │
│  ChromaDB (Semantic embeddings for memory)           │
│  Vault DB (Encrypted personal data)                  │
└──────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. **Prerequisites**
- Python 3.12+
- Node.js 18+ (for extension)
- Google Gemini API key ([get one](https://makersuite.google.com/app/apikey))
- Chrome/Chromium browser

### 2. **Clone & Setup Backend**

```bash
# Clone the repository
git clone https://github.com/tech-abdullahnaeem/browser-agent.git
cd browser-agent

# Install Python dependencies
cd backend
uv sync  # or: pip install -r requirements.txt
uv run playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env and add: GEMINI_API_KEY=your_api_key_here
```

### 3. **Run CLI Task**

```bash
# Simple task
uv run python scripts/run_task.py "Go to google.com and tell me the page title"

# Headless mode
uv run python scripts/run_task.py --headless "Search for 'Python programming' on Wikipedia"

# Custom max steps
uv run python scripts/run_task.py --max-steps 30 "Check if example.com loads correctly"
```

### 4. **Start Backend Server**

```bash
uv run uvicorn src.main:app --reload --port 8000
# API available at: http://localhost:8000
# Docs at: http://localhost:8000/docs
```

### 5. **Load Chrome Extension**

```bash
cd extension
pnpm install
pnpm run build

# In Chrome:
# 1. Open chrome://extensions/
# 2. Enable "Developer mode" (top right)
# 3. Click "Load unpacked"
# 4. Select the extension/dist folder

# Press CMD+K to open command palette
```

---

## 📦 Installation

### Backend Setup

```bash
cd backend

# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt

# Install Playwright browsers
uv run playwright install chromium
```

### Environment Configuration

```bash
# Copy example config
cp .env.example .env

# Edit .env with your settings:
GEMINI_API_KEY=sk-...                    # Required: Google Gemini API key
HEADLESS=false                           # false=see browser, true=headless
CHROME_USER_DATA_DIR=                    # Optional: persistent browser profile
MAX_STEPS=50                             # Max actions per task
MAX_FAILURES=3                           # Failed steps before escalation
USE_VISION=true                          # Enable screenshot analysis
LOG_LEVEL=INFO                           # DEBUG, INFO, WARNING, ERROR
ENABLE_MEMORY=true                       # Enable task history + semantic search
ENABLE_SAFETY=true                       # Enable HITL + audit logging
HITL_TIMEOUT=60                          # User confirmation timeout (seconds)
```

### Dependencies

```
Core:
  • browser-use>=0.12.1 (Browser automation framework)
  • langchain-google-genai>=2.0.0 (Gemini LLM integration)
  • pydantic>=2.0 (Data validation)
  • FastAPI>=0.135.0 (REST API)
  • aiosqlite (Async SQLite)
  • chromadb (Vector embeddings)
  • cryptography (Encryption for vault)

Dev:
  • pytest>=8.0 (Testing)
  • pytest-asyncio>=0.24 (Async test support)
  • ruff>=0.8 (Linting)
```

---

## 🎯 Usage

### 1. Command Line Interface

Run tasks directly from the terminal:

```bash
# Basic task
uv run python scripts/run_task.py "Find the fastest growing startup"

# With options
uv run python scripts/run_task.py \
  --headless \
  --max-steps 40 \
  "Book a flight from NYC to London on Google Flights"

# QA task
uv run python scripts/run_task.py \
  "Run full accessibility audit on https://example.com"

# Multi-step workflow
uv run python scripts/run_task.py \
  "Go to GitHub, search for 'browser-use', and tell me the top result"
```

#### CLI Options

```
--headless              Run browser in headless mode (no UI)
--max-steps N          Maximum action steps (default: 50)
--max-failures N       Consecutive failures before quit (default: 3)
--no-vision            Disable screenshot analysis
--user-data-dir PATH   Custom Chrome profile directory
--log-level LEVEL      DEBUG, INFO, WARNING, ERROR (default: INFO)
```

#### Example Output

```json
{
  "task_id": "abc123def456",
  "status": "completed",
  "steps": [
    {
      "step_number": 1,
      "action": "go_to_url",
      "element": "https://google.com",
      "success": true,
      "thinking": "Navigating to Google to search for browser automation"
    },
    {
      "step_number": 2,
      "action": "input_text",
      "element": "search box",
      "success": true,
      "reasoning": "Typing search query"
    }
  ],
  "final_result": "Google Search Results page loaded with results for browser automation",
  "duration_seconds": 12.45,
  "model_used": "gemini-2.5-pro"
}
```

---

### 2. REST API

Start the backend server and use HTTP endpoints:

#### Create a Task

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Check if example.com is accessible and report any errors",
    "context": "General website audit"
  }'

# Response:
{
  "task_id": "task-uuid-here",
  "status": "pending"
}
```

#### List All Tasks

```bash
curl http://localhost:8000/api/tasks?limit=10&offset=0

# Response:
{
  "tasks": [
    {
      "task_id": "task-1",
      "task": "Check accessibility",
      "status": "completed",
      "total_steps": 15,
      "final_result": "3 accessibility issues found",
      "duration_seconds": 23.4,
      "created_at": "2026-03-04T10:00:00Z"
    }
  ],
  "total": 42
}
```

#### Get Task Detail

```bash
curl http://localhost:8000/api/tasks/task-uuid-here

# Response:
{
  "task_id": "task-uuid",
  "task": "Check accessibility",
  "status": "completed",
  "steps": [
    {
      "step_number": 1,
      "action": "navigate",
      "element": "https://example.com",
      "success": true
    }
  ],
  "final_result": "...",
  "total_steps": 15,
  "duration_seconds": 23.4,
  "model_used": "gemini-2.5-pro"
}
```

#### Get Configuration

```bash
curl http://localhost:8000/api/config

# Response:
{
  "flash_model": "gemini-2.5-pro",
  "pro_model": "gemini-2.5-pro",
  "max_steps": 50,
  "max_failures": 3,
  "use_vision": true,
  "headless": false,
  "enable_memory": true,
  "enable_safety": true,
  "hitl_timeout_seconds": 60
}
```

#### Update Configuration

```bash
curl -X PUT http://localhost:8000/api/config \
  -H "Content-Type: application/json" \
  -d '{
    "max_steps": 75,
    "headless": true
  }'
```

#### Vault Operations (Encrypted personal data)

```bash
# Unlock vault
curl -X POST http://localhost:8000/vault/unlock \
  -H "Content-Type: application/json" \
  -d '{"passphrase": "my-secure-password"}'

# Get all fields (when unlocked)
curl http://localhost:8000/vault/get

# Set a field
curl -X POST http://localhost:8000/vault/set \
  -H "Content-Type: application/json" \
  -d '{
    "field_type": "email",
    "value": "user@example.com"
  }'

# Lock vault (clears key from memory)
curl -X POST http://localhost:8000/vault/lock
```

#### WebSocket (Real-time events)

```bash
# Connect to task stream
wscat -c ws://localhost:8000/ws/task-uuid-here

# Receive events:
{
  "type": "status",
  "task_id": "task-uuid",
  "timestamp": "2026-03-04T10:00:00Z",
  "status": "running"
}

{
  "type": "step",
  "task_id": "task-uuid",
  "timestamp": "2026-03-04T10:00:05Z",
  "data": {
    "step_number": 1,
    "action": "click_element",
    "element": "Login button",
    "success": true
  }
}

{
  "type": "screenshot",
  "task_id": "task-uuid",
  "data": "data:image/png;base64,iVBORw0K...",
  "step_number": 2
}

{
  "type": "hitl_request",
  "action_id": "action-123",
  "action_description": "Submit payment of $99.99",
  "url": "https://shop.com/checkout",
  "timeout_seconds": 60
}

{
  "type": "done",
  "data": {
    "status": "completed",
    "final_result": "Task completed successfully",
    "total_steps": 8,
    "duration_seconds": 45.3
  }
}
```

---

### 3. Chrome Extension

#### Installation

```bash
# Build extension
cd extension
pnpm install
pnpm run build

# Load in Chrome:
# 1. chrome://extensions/
# 2. "Developer mode" toggle (top-right)
# 3. "Load unpacked" → select dist/ folder
```

#### Usage

1. **Open Command Palette**: Press **CMD+K** (Mac) or **Ctrl+K** (Windows/Linux)
2. **Type your task**: "Check if the login form is working"
3. **Watch live progress**: Real-time step updates in sidebar
4. **Approve HITL requests**: Click Allow/Deny when prompted
5. **View task history**: Sidebar shows all past tasks

#### Features in Extension

- **Command Palette**: Natural language task input with context summary
- **Sidebar**: Task history, live monitoring, audit trail
- **Context Extraction**: Auto-scans page for meta, console errors, a11y issues
- **HITL Dialogs**: Inline confirmation with countdown timer
- **Highlight Overlay**: Agent-targeted elements marked on page
- **Status Badges**: Real-time running/completed/failed indicators

---

## 📁 Project Structure

```
browser-agent/
├── README.md                              # This file
├── IMPLEMENTATION_PLAN.md                 # Detailed 6-phase spec
├── .env.example                           # Environment template
│
├── backend/                               # Python FastAPI backend
│   ├── pyproject.toml                     # uv project config
│   ├── .env                               # Configuration (git-ignored)
│   │
│   ├── src/
│   │   ├── __init__.py
│   │   ├── config.py                      # Settings (Pydantic)
│   │   ├── main.py                        # FastAPI app entry
│   │   │
│   │   ├── agent/                         # AI orchestration
│   │   │   ├── core.py                    # BrowserAgentRunner (main)
│   │   │   ├── llm.py                     # LLM factory (Gemini 2.5 Pro)
│   │   │   ├── tools.py                   # 37 custom/builtin tools
│   │   │   ├── planner.py                 # Task decomposition
│   │   │   ├── prompts.py                 # System prompts
│   │   │   └── watchdog.py                # Safety controller
│   │   │
│   │   ├── api/                           # HTTP/WS routes
│   │   │   ├── routes_tasks.py            # POST /tasks, GET /tasks
│   │   │   ├── routes_config.py           # GET/PUT /config
│   │   │   ├── routes_vault.py            # Vault CRUD
│   │   │   ├── routes_ws.py               # WebSocket streaming
│   │   │   └── task_store.py              # In-memory task manager
│   │   │
│   │   ├── models/                        # Pydantic schemas
│   │   │   ├── task.py                    # Task, TaskResult, Step
│   │   │   ├── config.py                  # AgentConfig
│   │   │   ├── agent_event.py             # WS events
│   │   │   └── vault.py                   # Vault schemas
│   │   │
│   │   ├── memory/                        # Persistence layer
│   │   │   ├── sqlite_store.py            # Task history DB
│   │   │   ├── vector_store.py            # ChromaDB embeddings
│   │   │   └── vault.py                   # Encrypted data vault
│   │   │
│   │   ├── safety/                        # Safety & auditing
│   │   │   ├── hitl.py                    # HITL gate logic
│   │   │   ├── audit.py                   # Action audit logger
│   │   │   └── domain_filter.py           # Navigation allow/block
│   │   │
│   │   └── utils/
│   │       ├── logging.py                 # Structured logging (structlog)
│   │       └── (shared utilities)
│   │
│   ├── tests/                             # 156 unit tests
│   │   ├── conftest.py                    # pytest fixtures
│   │   ├── test_agent_core.py
│   │   ├── test_llm.py
│   │   ├── test_api_tasks.py
│   │   ├── test_memory.py
│   │   ├── test_safety.py
│   │   └── ...
│   │
│   ├── scripts/
│   │   ├── run_task.py                    # CLI entry point
│   │   ├── verify_phases.py               # Verify all phases
│   │   └── seed_memory.py                 # Populate vector DB
│   │
│   └── docs/
│       ├── api.md                         # REST/WS API reference
│       └── (architecture docs)
│
├── extension/                             # Chrome MV3 Extension
│   ├── package.json                       # pnpm config
│   ├── vite.config.ts                     # Build config
│   ├── tailwind.config.ts                 # Styling
│   ├── tsconfig.json                      # TypeScript config
│   │
│   ├── public/
│   │   ├── manifest.json                  # MV3 manifest
│   │   └── icons/                         # 16x16, 48x48, 128x128
│   │
│   └── src/
│       ├── background/
│       │   └── service-worker.ts          # WS mgmt, message routing
│       ├── content/
│       │   ├── index.ts                   # Content script entry
│       │   ├── context-extractor.ts       # Page metadata
│       │   └── highlight-overlay.ts       # Visual markers
│       ├── popup/
│       │   ├── index.html
│       │   └── Popup.tsx
│       ├── sidepanel/
│       │   ├── SidePanel.tsx              # Main UI
│       │   ├── TaskList.tsx               # History list
│       │   ├── TaskDetail.tsx             # Live monitor
│       │   └── StatusBadge.tsx
│       ├── command-palette/
│       │   ├── CommandPalette.tsx         # CMD+K overlay
│       │   ├── TaskInput.tsx              # Input field
│       │   └── QuickActions.tsx           # Suggestions
│       ├── components/                    # Shared UI
│       │   ├── Button.tsx
│       │   ├── Spinner.tsx
│       │   └── ConfirmDialog.tsx          # HITL UI
│       ├── hooks/
│       │   ├── useWebSocket.ts
│       │   ├── useTaskApi.ts
│       │   └── useTabContext.ts
│       ├── lib/
│       │   ├── api.ts                     # HTTP client
│       │   ├── ws.ts                      # WS client
│       │   └── storage.ts                 # Chrome storage
│       └── types/
│           ├── task.ts                    # TS interfaces
│           ├── events.ts                  # WS event types
│           └── messages.ts                # Extension messages
```

---

## ⚙️ Configuration

### Backend (.env)

```env
# Required
GEMINI_API_KEY=sk-...

# Browser Settings
HEADLESS=false                      # true = headless mode
CHROME_USER_DATA_DIR=               # Persistent profile (optional)

# Agent Control
MAX_STEPS=50                        # Max actions per task (5-500)
MAX_FAILURES=3                      # Consecutive failures threshold
USE_VISION=true                     # Screenshot analysis

# LLM Models
FLASH_MODEL=gemini-2.5-pro         # Primary execution model
PRO_MODEL=gemini-2.5-pro           # Fallback/planning model

# Memory & Personalization
ENABLE_MEMORY=true
MEMORY_DB_PATH=./browser_agent.db   # SQLite path

# Safety & HITL
ENABLE_SAFETY=true
HITL_TIMEOUT_SECONDS=60             # User approval timeout
ALLOWED_DOMAINS=                    # Comma-separated list
BLOCKED_DOMAINS=                    # Comma-separated list

# Logging
LOG_LEVEL=INFO                      # DEBUG, INFO, WARNING, ERROR

# Server
HOST=127.0.0.1
PORT=8000
```

### Extension (vite.config.ts)

```typescript
// Configure backend URL
const BACKEND_URL = "http://localhost:8000"

// Or for production:
const BACKEND_URL = "https://your-domain.com"
```

---

## 📊 Testing

### Run All Tests

```bash
cd backend

# Full test suite
uv run pytest -v

# Specific test file
uv run pytest tests/test_llm.py -v

# Single test
uv run pytest tests/test_llm.py::TestGetFlashLLM::test_returns_correct_model -v

# With coverage
uv run pytest --cov=src tests/
```

### Test Summary

```
156 tests across 7 files

✅ test_agent_core.py       - Agent orchestration
✅ test_llm.py              - LLM factory & models
✅ test_api_tasks.py        - REST endpoints
✅ test_models.py           - Data schema validation
✅ test_memory.py           - SQLite + ChromaDB + Vault
✅ test_safety.py           - HITL + Audit + Domain filter
✅ test_ws.py               - WebSocket & config routes
```

### Verification Scripts

```bash
# Verify all phases are implemented
uv run python scripts/verify_phases.py

# Seed vector database with sample memories
uv run python scripts/seed_memory.py

# Run live QA tools test (uses real browser)
uv run python scripts/test_qa_tools_live.py
```

---

## 🔌 API Reference

### REST Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/tasks` | Create new task |
| GET | `/api/tasks` | List all tasks |
| GET | `/api/tasks/{id}` | Get task detail |
| DELETE | `/api/tasks/{id}` | Cancel task |
| GET | `/api/config` | Get settings |
| PUT | `/api/config` | Update settings |
| POST | `/vault/unlock` | Unlock encrypted vault |
| POST | `/vault/lock` | Lock vault |
| GET | `/vault/get` | Get vault data |
| POST | `/vault/set` | Set vault field |
| WS | `/ws/{task_id}` | Stream task events |

### Data Models

#### TaskRequest
```python
{
    "task": "Check if login works",
    "context": "Automated testing"  # Optional
}
```

#### TaskResponse
```python
{
    "task_id": "uuid-string",
    "status": "pending|running|completed|failed",
    "steps": [
        {
            "step_number": 1,
            "action": "click_element",
            "element": "Login button",
            "success": true,
            "reasoning": "To enter credentials",
            "thinking": "I should click the login button first"
        }
    ],
    "final_result": "Login successful",
    "error": null,
    "duration_seconds": 23.45,
    "model_used": "gemini-2.5-pro",
    "created_at": "2026-03-04T10:00:00Z"
}
```

#### WebSocket Events

```python
# Status update
{
    "type": "status",
    "task_id": "uuid",
    "timestamp": "ISO-8601",
    "status": "running"
}

# Action completed
{
    "type": "step",
    "task_id": "uuid",
    "timestamp": "ISO-8601",
    "data": {
        "step_number": 1,
        "action": "click_element",
        "element": "button-text",
        "success": true,
        "reasoning": "Click reason"
    }
}

# Screenshot captured
{
    "type": "screenshot",
    "task_id": "uuid",
    "timestamp": "ISO-8601",
    "data": "data:image/png;base64,..."
}

# Task plan
{
    "type": "plan",
    "task_id": "uuid",
    "timestamp": "ISO-8601",
    "plan": "1. Navigate to page\n2. Find element\n3. Click button"
}

# User confirmation needed
{
    "type": "hitl_request",
    "task_id": "uuid",
    "action_id": "uuid",
    "action_description": "Submit payment",
    "url": "https://example.com/checkout",
    "timeout_seconds": 60
}

# Task complete
{
    "type": "done",
    "task_id": "uuid",
    "timestamp": "ISO-8601",
    "data": {
        "status": "completed",
        "final_result": "Task result",
        "total_steps": 8,
        "duration_seconds": 45.3
    }
}

# Error occurred
{
    "type": "error",
    "task_id": "uuid",
    "timestamp": "ISO-8601",
    "message": "Error description"
}
```

---

## 🛠️ Advanced Topics

### Custom Tools

Add your own tools to `backend/src/agent/tools.py`:

```python
@custom_tools.action("Description of what your tool does")
async def my_custom_tool(browser_session: BrowserSession) -> ActionResult:
    """Docstring explaining the tool."""
    page = await browser_session.get_current_page()
    
    # Your logic here
    result = await page.evaluate("() => document.title")
    
    return ActionResult(extracted_content=result)
```

### Memory Injection

Past tasks are automatically injected into prompts:

```python
# In core.py run_task():
similar_tasks = await vector_store.search(task_string, top_k=3)
enhanced_prompt = MEMORY_INJECTION_TEMPLATE.format(
    task=task_string,
    similar_tasks=similar_tasks
)
```

### Safety Gates

Configure HITL behavior in `.env`:

```env
# Destructive keywords trigger confirmation
# E.g., "buy", "delete", "submit payment"

# Destructive URLs trigger confirmation
# E.g., "/checkout", "/billing", "/payment"

# Auto-approve trusted domains
ALLOWED_DOMAINS=shop.mycompany.com,admin.example.com

# Block any navigation to these domains
BLOCKED_DOMAINS=malicious.site,spam.com
```

### Vault Encryption Details

- **Algorithm**: Fernet (AES-128)
- **Key derivation**: PBKDF2 with 480,000 iterations
- **Storage**: Encrypted blobs in SQLite
- **Supported fields**: name, email, phone, address (line1, city, state, zip, country), card (number, exp, cvv, name), username, password, company, custom

---

## 🐛 Troubleshooting

### Cannot connect to Gemini API

```
Error: "Error occurred: 403 Forbidden"
```

**Solution**: Check your `GEMINI_API_KEY` in `.env`
```bash
# Verify key is set
echo $GEMINI_API_KEY

# Get new key from: https://makersuite.google.com/app/apikey
```

### Browser crashes or timeout

```
Error: "Execution timeout / Browser crashed"
```

**Solution**: Reduce `MAX_STEPS` or increase timeout
```env
MAX_STEPS=30              # Lower from 50
WAIT_BETWEEN_ACTIONS=2   # Increase from 1
```

### Extension not connecting to backend

```
Error: "Backend offline" in extension
```

**Solution**: Verify server is running
```bash
# Check if port 8000 is listening
lsof -i :8000

# Start server if needed
uv run uvicorn src.main:app --reload --port 8000
```

### HITL confirmation not showing

```
Error: Confirmation dialog appears but not responding
```

**Solution**: Check WebSocket connection
```bash
# Verify WS is connected
# In DevTools → Application → WebSockets

# Restart extension:
# 1. chrome://extensions/
# 2. Reload extension
# 3. Retry task
```

### Tests failing locally

```
Error: "ModuleNotFoundError" or test failures
```

**Solution**: Reinstall dependencies
```bash
cd backend
rm -rf .venv __pycache__ .pytest_cache
uv sync
uv run pytest -v
```

---

## 📈 Performance Characteristics

| Scenario | Typical Duration |
|----------|------------------|
| Simple navigation | 5-10 seconds |
| Form filling | 10-20 seconds |
| Multi-step workflow | 20-50 seconds |
| Full QA audit | 60-120 seconds |
| With vision analysis | +5-10 seconds per screenshot |

**Factors affecting speed:**:
- Network latency (API, website)
- JavaScript rendering time
- LLM response time (usually 1-3 seconds)
- Screenshot processing (if vision enabled)

---

## 🤝 Contributing

### Code Style

```bash
# Format with ruff
uv run ruff format src/ tests/

# Lint
uv run ruff check src/ tests/
```

### Building & Testing Locally

```bash
# Backend
cd backend
uv sync
uv run pytest -v

# Extension
cd extension
pnpm install
pnpm run build
pnpm run dev  # Watch mode
```

### Before Creating PR

- [ ] All 156 tests pass locally
- [ ] No TypeScript errors in extension
- [ ] Code formatted with ruff
- [ ] New features have tests
- [ ] README updated if needed

---

## 📝 License

MIT License — See LICENSE file for details

---

## 🔗 Links & Resources

- **GitHub Repo**: https://github.com/tech-abdullahnaeem/browser-agent
- **browser-use**: https://github.com/browser-use/browser-use
- **Google Gemini**: https://ai.google.dev/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Playwright**: https://playwright.dev/

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/tech-abdullahnaeem/browser-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/tech-abdullahnaeem/browser-agent/discussions)
- **Email**: [Your contact info]

---

**Made with ❤️ using Gemini 2.5 Pro & browser-use**

*Last updated: March 4, 2026*
