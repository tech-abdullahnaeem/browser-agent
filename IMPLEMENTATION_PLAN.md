# Browser Agent — Comprehensive Implementation Plan

> A Comet-like AI browser agent: Chrome Extension + Python backend powered by `browser-use` and Google Gemini.

---

## Table of Contents

1. [Full Project Directory Structure](#1-full-project-directory-structure)
2. [Phase 1: Backend Core (MVP — The Automation Loop)](#2-phase-1-backend-core)
3. [Phase 2: API & Real-time Streaming](#3-phase-2-api--real-time-streaming)
4. [Phase 3: Chrome Extension Shell](#4-phase-3-chrome-extension-shell)
5. [Phase 4: Context Awareness](#5-phase-4-context-awareness)
6. [Phase 5: Memory & Personalization](#6-phase-5-memory--personalization)
7. [Phase 6: Safety & HITL](#7-phase-6-safety--hitl)
8. [Cross-Cutting Concerns](#8-cross-cutting-concerns)

---

## 1. Full Project Directory Structure

This is the **final-state** tree. Each phase incrementally builds toward it. Files are annotated with the phase they are introduced in.

```
browser-agent/
├── README.md                              # P1
├── .gitignore                             # P1
├── .env.example                           # P1
├── .env                                   # (git-ignored, user creates)
├── IMPLEMENTATION_PLAN.md                 # This file
│
├── backend/                               # Python backend (all phases)
│   ├── pyproject.toml                     # P1 — uv project config, all Python deps
│   ├── uv.lock                            # P1 — auto-generated lockfile
│   ├── alembic.ini                        # P5 — DB migration config
│   │
│   ├── src/
│   │   ├── __init__.py                    # P1
│   │   ├── config.py                      # P1 — Pydantic Settings (env vars, defaults)
│   │   ├── main.py                        # P2 — FastAPI app entrypoint (uvicorn)
│   │   │
│   │   ├── agent/                         # Core agent orchestration
│   │   │   ├── __init__.py                # P1
│   │   │   ├── core.py                    # P1 — BrowserAgent wrapper class
│   │   │   ├── llm.py                     # P1 — LLM factory (Gemini 2.5 Pro)
│   │   │   ├── tools.py                   # P1 — Custom @tools.action() definitions
│   │   │   ├── watchdog.py                # P6 — HITL watchdog (BaseWatchdog subclass)
│   │   │   ├── planner.py                 # P1 — Multi-model planning router
│   │   │   └── prompts.py                 # P1 — System prompt templates
│   │   │
│   │   ├── api/                           # FastAPI routes
│   │   │   ├── __init__.py                # P2
│   │   │   ├── routes_tasks.py            # P2 — POST /tasks, GET /tasks, GET /tasks/{id}
│   │   │   ├── routes_config.py           # P2 — GET/PUT /config
│   │   │   ├── routes_vault.py            # P5 — Personal data vault CRUD
│   │   │   └── ws.py                      # P2 — WebSocket endpoint /ws/{task_id}
│   │   │
│   │   ├── models/                        # Pydantic models / DB schemas
│   │   │   ├── __init__.py                # P1
│   │   │   ├── task.py                    # P1 — TaskRequest, TaskResponse, TaskStatus enum
│   │   │   ├── agent_event.py             # P2 — WebSocket event schemas (StepEvent, ActionEvent, etc.)
│   │   │   ├── config.py                  # P2 — AgentConfig model
│   │   │   └── vault.py                   # P5 — VaultEntry model
│   │   │
│   │   ├── memory/                        # Memory subsystem
│   │   │   ├── __init__.py                # P5
│   │   │   ├── sqlite_store.py            # P5 — aiosqlite task history & preferences
│   │   │   ├── vector_store.py            # P5 — ChromaDB semantic memory
│   │   │   └── vault.py                   # P5 — Encrypted personal data vault
│   │   │
│   │   ├── safety/                        # Safety layer
│   │   │   ├── __init__.py                # P6
│   │   │   ├── hitl.py                    # P6 — HITL confirmation gate logic
│   │   │   ├── audit.py                   # P6 — Action audit logger
│   │   │   └── domain_filter.py           # P6 — Allowed/blocked domain enforcement
│   │   │
│   │   └── utils/                         # Shared utilities
│   │       ├── __init__.py                # P1
│   │       └── logging.py                 # P1 — Structured logging setup (structlog)
│   │
│   ├── tests/                             # Backend tests
│   │   ├── __init__.py                    # P1
│   │   ├── conftest.py                    # P1 — Shared pytest fixtures
│   │   ├── test_agent_core.py             # P1
│   │   ├── test_llm.py                    # P1
│   │   ├── test_api_tasks.py              # P2
│   │   ├── test_ws.py                     # P2
│   │   ├── test_memory.py                 # P5
│   │   └── test_safety.py                 # P6
│   │
│   ├── migrations/                        # Alembic migrations
│   │   ├── env.py                         # P5
│   │   └── versions/                      # P5
│   │       └── 001_initial.py             # P5
│   │
│   └── scripts/
│       ├── run_task.py                    # P1 — CLI script: `python scripts/run_task.py "book a flight"`
│       └── seed_memory.py                 # P5 — Seed ChromaDB with sample memories
│
├── extension/                             # Chrome Extension (P3+)
│   ├── package.json                       # P3
│   ├── pnpm-lock.yaml                     # P3
│   ├── tsconfig.json                      # P3
│   ├── vite.config.ts                     # P3
│   ├── tailwind.config.ts                 # P3
│   ├── postcss.config.js                  # P3
│   │
│   ├── public/
│   │   ├── manifest.json                  # P3 — MV3 manifest
│   │   └── icons/                         # P3 — Extension icons (16, 48, 128)
│   │       ├── icon16.png
│   │       ├── icon48.png
│   │       └── icon128.png
│   │
│   └── src/
│       ├── background/
│       │   └── service-worker.ts          # P3 — Background SW: WebSocket mgmt, message routing
│       │
│       ├── content/
│       │   ├── index.ts                   # P3 — Content script entry: injects overlay root
│       │   ├── context-extractor.ts       # P4 — Reads tab URL, visible text, meta, summarizes
│       │   └── highlight-overlay.ts       # P4 — Visual markers on agent-targeted elements
│       │
│       ├── popup/                         # (Minimal — redirects to sidebar)
│       │   ├── index.html                 # P3
│       │   └── Popup.tsx                  # P3
│       │
│       ├── sidepanel/
│       │   ├── index.html                 # P3
│       │   ├── SidePanel.tsx              # P3 — Main sidebar component
│       │   ├── TaskList.tsx               # P3 — Task history list
│       │   ├── TaskDetail.tsx             # P3 — Live step-by-step status for a task
│       │   └── StatusBadge.tsx            # P3 — Running/Done/Failed badge
│       │
│       ├── command-palette/
│       │   ├── CommandPalette.tsx          # P3 — Floating CMD+K overlay
│       │   ├── TaskInput.tsx              # P3 — Natural language task input field
│       │   └── QuickActions.tsx           # P3 — Suggested actions
│       │
│       ├── components/                    # Shared UI components
│       │   ├── Button.tsx                 # P3
│       │   ├── Spinner.tsx                # P3
│       │   └── ConfirmDialog.tsx          # P6 — HITL confirmation UI
│       │
│       ├── hooks/
│       │   ├── useWebSocket.ts            # P3 — WS connection hook
│       │   ├── useTaskApi.ts              # P3 — REST API hook
│       │   └── useTabContext.ts           # P4 — Hook to get current tab context
│       │
│       ├── lib/
│       │   ├── api.ts                     # P3 — Axios/fetch wrapper for backend REST
│       │   ├── ws.ts                      # P3 — WebSocket client class
│       │   └── storage.ts                 # P5 — chrome.storage wrapper for vault data
│       │
│       └── types/
│           ├── task.ts                    # P3 — TypeScript types mirroring backend models
│           └── events.ts                  # P3 — WebSocket event types
│
└── docs/                                  # Documentation
    ├── architecture.md                    # P1 — High-level architecture diagram (Mermaid)
    └── api.md                             # P2 — REST + WS API reference
```

---

## 2. Phase 1: Backend Core

**Goal:** A working Python CLI that takes a task string, launches a real browser, and completes the task end-to-end using Gemini via `browser-use`.

### 2.1 Directory Structure to Create

```
backend/
├── pyproject.toml
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── core.py
│   │   ├── llm.py
│   │   ├── tools.py
│   │   ├── planner.py
│   │   └── prompts.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── task.py
│   └── utils/
│       ├── __init__.py
│       └── logging.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_agent_core.py
│   └── test_llm.py
├── scripts/
│   └── run_task.py
.env.example
.env
.gitignore
README.md
docs/
└── architecture.md
```

### 2.2 Files and Their Purpose

| File | Purpose |
|------|---------|
| `pyproject.toml` | uv project definition: name, python version (3.12), dependencies, dev-dependencies, scripts |
| `.env.example` | Template: `GEMINI_API_KEY=`, `BROWSER_USER_DATA_DIR=`, `HEADLESS=false`, `LOG_LEVEL=INFO` |
| `.gitignore` | Ignore `.env`, `__pycache__`, `.venv`, `uv.lock`, `*.db`, `node_modules`, `dist/` |
| `src/config.py` | Pydantic `BaseSettings` class loading from `.env`: `gemini_api_key`, `browser_user_data_dir` (optional, defaults to None for fresh profile), `headless` (bool, default False), `max_steps` (int, default 50), `max_failures` (int, default 3), `use_vision` (bool, default True), `wait_between_actions` (float, default 1.0), `log_level` (str) |
| `src/agent/llm.py` | **LLM factory module.** Creates two `ChatGoogleGenerativeAI` instances: (1) `get_flash_llm()` → `gemini-2.5-pro` with `temperature=0.1`, `max_output_tokens=2048`; (2) `get_pro_llm()` → `gemini-2.5-pro` with `temperature=0.2`, `max_output_tokens=4096`. Both use the `GEMINI_API_KEY` from config. Exposes a `get_default_llm()` that returns Pro (used as the primary agent LLM). |
| `src/agent/prompts.py` | System prompt string constants: `SYSTEM_PROMPT` (core identity, behavioral instructions: "You are a browser automation agent..."), `PLANNING_PROMPT` (for Gemini Pro planning calls), `CONTEXT_INJECTION_TEMPLATE` (f-string for injecting tab context in P4). |
| `src/agent/planner.py` | **Multi-model planner.** Contains `TaskPlanner` class: takes a task string → calls Gemini Pro to decompose into a list of `PlanItem` sub-goals → returns structured plan. Uses browser-use's built-in planning mechanism if available, or wraps the Pro LLM call manually. The Agent will use Flash for step execution and only call Pro via the planner for initial decomposition or when stuck (>3 consecutive failures). |
| `src/agent/tools.py` | **Custom tools module.** Uses browser-use `Tools` class + `@tools.action()` decorator. Initial custom tools: (1) `extract_page_text` — returns cleaned visible text of current page (for context); (2) `wait_for_user` — placeholder for P6 HITL; (3) `take_screenshot` — captures current viewport and returns base64 (useful for vision model calls). All tools receive `browser_session` automatically from browser-use. |
| `src/agent/core.py` | **Central orchestration.** `BrowserAgentRunner` class: (1) `__init__(config)` — stores config, initializes LLMs via `llm.py`; (2) `async run_task(task: str, context: str = None) -> TaskResult` — creates `BrowserProfile` (headless, user_data_dir from config), creates `BrowserSession`, creates custom `Tools` instance, creates browser-use `Agent(task=task, llm=flash_llm, browser_session=session, tools=tools, use_vision=config.use_vision, max_steps=config.max_steps, max_failures=config.max_failures)`, calls `agent.run()`, collects `AgentHistoryList`, returns structured `TaskResult`; (3) Integrates planner: if task is complex (heuristic: >15 words or contains "and then"), call Planner first with Pro, then feed sub-goals to Agent. (4) Cleanup: ensures browser session is closed in `finally` block. |
| `src/models/task.py` | Pydantic models: `TaskRequest(task: str, context: str = None)`, `TaskStatus` enum (`pending`, `running`, `completed`, `failed`), `TaskResult(task_id: str, status: TaskStatus, steps: list[StepSummary], result: str, error: str = None, duration_seconds: float)`, `StepSummary(step_number: int, action: str, element: str = None, reasoning: str = None, screenshot_b64: str = None)` |
| `src/utils/logging.py` | Configure `structlog` with JSON output for production, console colored output for dev (based on `LOG_LEVEL`). Bind `task_id` to log context when running a task. |
| `scripts/run_task.py` | CLI entry point: `python scripts/run_task.py "Search for flights from NYC to London on Google Flights"`. Uses `argparse`. Loads config, creates `BrowserAgentRunner`, calls `asyncio.run(runner.run_task(args.task))`, prints `TaskResult` as formatted JSON. Accepts optional `--headless` flag. |
| `tests/conftest.py` | Shared fixtures: mock config with test API key, mock LLM that returns predefined responses (for unit tests without real API calls). |
| `tests/test_agent_core.py` | Tests: (1) `BrowserAgentRunner` initializes without error; (2) `run_task` with mocked LLM returns a valid `TaskResult`; (3) Config values propagate correctly to `BrowserProfile`. |
| `tests/test_llm.py` | Tests: (1) `get_flash_llm()` returns a `ChatGoogleGenerativeAI` with correct model name; (2) `get_pro_llm()` returns correct model; (3) API key is set from config. |
| `docs/architecture.md` | Mermaid diagram showing: User → CLI/Extension → FastAPI → BrowserAgentRunner → browser-use Agent → Playwright → Browser. Also shows LLM calls (Flash and Pro) and Memory layers. |

### 2.3 Dependencies

**pyproject.toml dependencies (Phase 1):**

```
[project]
name = "browser-agent-backend"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
    "browser-use>=0.2.0",
    "langchain-google-genai>=2.0.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "structlog>=24.0",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.8",
]
```

**Install commands:**
```bash
cd backend
uv init
uv add browser-use langchain-google-genai pydantic pydantic-settings structlog python-dotenv
uv add --dev pytest pytest-asyncio ruff
uv run playwright install chromium   # browser-use needs Playwright browsers
```

### 2.4 Core Implementation Details

#### LLM Configuration
- `ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=config.gemini_api_key, temperature=0.1)`
- `ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=config.gemini_api_key, temperature=0.2)`
- Both are LangChain `BaseChatModel` compatible, so browser-use accepts them directly as the `llm` parameter.

#### BrowserProfile Configuration
```python
BrowserProfile(
    headless=config.headless,
    user_data_dir=config.browser_user_data_dir,  # None = fresh temp profile
    wait_between_actions=config.wait_between_actions,
    # allowed_domains left open in P1, restricted in P6
)
```

#### Agent Creation Pattern
```python
agent = Agent(
    task=task_string,
    llm=pro_llm,  # Using Gemini 2.5 Pro for all execution
    browser_session=session,
    tools=custom_tools,
    use_vision=config.use_vision,
    max_steps=config.max_steps,
    max_failures=config.max_failures,
    # planner_llm=pro_llm,  # if browser-use supports separate planner LLM
)
history: AgentHistoryList = await agent.run()
```

#### Multi-Model Routing Strategy (P1 Simplified)
- **Default path:** All agent steps use Gemini 2.5 Pro (capable, consistent reasoning)
- **Planning path:** Before starting, if task is complex, call Gemini Pro once to decompose into sub-tasks. Pass the plan as augmented instructions to the Pro-based agent.
- **Complexity heuristic:** word count > 15, contains conjunctions like "and then", "after that", "first...then", or multiple verbs.
- **Fallback:** If the Pro agent fails 3 times consecutively on a step, re-run with increased context and retry logic.

#### TaskResult Construction
- Iterate over `AgentHistoryList` entries after `agent.run()` completes
- Extract: action name, target element (if any), model reasoning/thought, screenshot data
- Map each entry to a `StepSummary`
- Compute total `duration_seconds` from start to finish timestamps
- Set `status` to `completed` if agent finished successfully, `failed` if max_steps/max_failures exceeded

### 2.5 Verification

| Check | How |
|-------|-----|
| **Dependencies install** | `cd backend && uv sync` completes without error |
| **Playwright browsers** | `uv run playwright install chromium` succeeds |
| **Config loads** | `uv run python -c "from src.config import Settings; print(Settings())"` shows defaults |
| **LLM connects** | `uv run python -c "from src.agent.llm import get_flash_llm; llm = get_flash_llm(); print(llm.invoke('Say hello'))"` returns a response |
| **End-to-end task** | `uv run python scripts/run_task.py "Go to google.com and search for 'browser automation'"` — Chrome opens, navigates, types, searches, agent completes, JSON result printed |
| **Unit tests** | `uv run pytest tests/ -v` — all pass |

---

## 3. Phase 2: API & Real-time Streaming

**Goal:** Wrap the P1 agent in FastAPI with REST endpoints and WebSocket streaming.

### 3.1 New/Modified Files

| File | Purpose |
|------|---------|
| `src/main.py` | FastAPI app: creates app instance, includes routers, configures CORS (allow `chrome-extension://*` origin + `localhost`), lifespan handler for startup/shutdown, runs with `uvicorn` |
| `src/api/__init__.py` | Package init |
| `src/api/routes_tasks.py` | REST routes: `POST /api/tasks` (accepts `TaskRequest`, generates UUID `task_id`, queues task, returns `{task_id, status: pending}`), `GET /api/tasks` (list all tasks with status), `GET /api/tasks/{task_id}` (get task detail + step history), `DELETE /api/tasks/{task_id}` (cancel running task) |
| `src/api/routes_config.py` | REST routes: `GET /api/config` (returns current `AgentConfig`), `PUT /api/config` (updates runtime config like `max_steps`, `use_vision`, `headless`) |
| `src/api/ws.py` | WebSocket endpoint: `WS /ws/{task_id}` — client connects, receives JSON events as the agent runs. Events: `{"type": "step", "data": StepSummary}`, `{"type": "status", "data": {"status": "running"}}`, `{"type": "plan", "data": [PlanItem]}`, `{"type": "screenshot", "data": {"b64": "..."}}`, `{"type": "done", "data": TaskResult}`, `{"type": "error", "data": {"message": "..."}}`. On connect, if task already completed, sends full history then closes. |
| `src/models/agent_event.py` | Pydantic models for WS events: `AgentEvent(type: str, data: dict)`, `StepEvent`, `StatusEvent`, `PlanEvent`, `ScreenshotEvent`, `DoneEvent`, `ErrorEvent` |
| `src/models/config.py` | `AgentConfig` Pydantic model: `max_steps`, `max_failures`, `use_vision`, `headless`, `wait_between_actions` — all with defaults |
| `docs/api.md` | REST and WebSocket API documentation |

### 3.2 Additional Dependencies

```
uv add fastapi uvicorn[standard] websockets
uv add --dev httpx  # for test client
```

### 3.3 Core Implementation Details

#### Task Lifecycle & In-Memory Store (Pre-SQLite)
- Use an in-memory `dict[str, TaskState]` to track tasks (replaced by SQLite in P5)
- `TaskState`: holds `task_id`, `status`, `request`, `result`, `created_at`, `updated_at`, list of `StepSummary` accumulated so far
- A background `asyncio.Task` runs the agent for each submitted task

#### Task Submission Flow
1. `POST /api/tasks` → validate `TaskRequest` → generate UUID → store `TaskState(status=pending)` → create `asyncio.Task` that calls `BrowserAgentRunner.run_task()` → return `{task_id}`
2. The background task updates `TaskState.status` to `running`, then on each agent step, appends a `StepSummary` to the state and broadcasts via WS

#### WebSocket Broadcasting Architecture
- Global `dict[str, set[WebSocket]]` maps `task_id` → connected WS clients
- When a step completes, the agent callback pushes a `StepEvent` to all connected clients for that `task_id`
- Use browser-use's `register_new_step_callback` or custom hook (inspect `AgentHistoryList` growth in a polling loop) to detect new steps
- **Agent step callback approach:** Subclass or monkey-patch the agent to emit events. Preferred: use browser-use's built-in callback support if available. Fallback: wrap `agent.run()` in a coroutine that polls `agent.history` every 0.5s and emits new entries.

#### CORS Configuration
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://*", "http://localhost:*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Concurrency Considerations
- Only one agent task can run at a time (single browser instance). Use an `asyncio.Lock` or `asyncio.Semaphore(1)` to serialize task execution.
- Queued tasks wait until the lock is released. Future: support parallel browser sessions.

### 3.4 Verification

| Check | How |
|-------|-----|
| **Server starts** | `uv run uvicorn src.main:app --reload --port 8000` — no errors |
| **Submit task via REST** | `curl -X POST http://localhost:8000/api/tasks -H "Content-Type: application/json" -d '{"task": "Go to wikipedia.org"}'` → returns `{"task_id": "...", "status": "pending"}` |
| **WebSocket stream** | Use `websocat ws://localhost:8000/ws/{task_id}` — receives step events in real-time as agent runs |
| **Task history** | `curl http://localhost:8000/api/tasks/{task_id}` → returns full result after completion |
| **Config API** | `curl http://localhost:8000/api/config` → returns current config JSON |
| **Tests** | `uv run pytest tests/test_api_tasks.py tests/test_ws.py -v` |

---

## 4. Phase 3: Chrome Extension Shell

**Goal:** Working MV3 extension with CMD+K command palette that submits tasks to the backend and shows live status in a sidebar.

### 4.1 New Files

All under `extension/`. See directory structure above for complete listing.

### 4.2 Key Files Explained

| File | Purpose |
|------|---------|
| `manifest.json` | MV3 manifest: `permissions: ["activeTab", "sidePanel", "storage", "tabs"]`, `host_permissions: ["http://localhost:8000/*"]`, `background.service_worker: "src/background/service-worker.ts"`, `content_scripts: [{matches: ["<all_urls>"], js: ["src/content/index.ts"]}]`, `side_panel: {default_path: "src/sidepanel/index.html"}`, `commands: {"toggle-palette": {suggested_key: {"default": "Ctrl+K", "mac": "Command+K"}, description: "Open command palette"}}` |
| `service-worker.ts` | Listens for `chrome.commands.onCommand` → sends message to content script to toggle palette. Manages a single WebSocket connection to backend. Routes messages between content script / sidepanel and backend. Stores `backend_url` in `chrome.storage.local`. |
| `content/index.ts` | Injects a Shadow DOM root into the page (`<div id="browser-agent-root">`). Mounts the React `CommandPalette` component into the shadow root. Listens for messages from service worker to toggle visibility. Shadow DOM prevents style conflicts. |
| `CommandPalette.tsx` | Floating overlay (centered, `position: fixed`, `z-index: 2147483647`). Input field with placeholder "What should I do?". On Enter: sends task to service worker → service worker POSTs to `/api/tasks` → receives `task_id` → opens WebSocket → palette shows mini-status ("Running step 3/50..."). Escape key closes. Click-outside closes. Animated with CSS transitions (fade + scale). |
| `SidePanel.tsx` | List of past tasks (fetched from `GET /api/tasks` on mount). Click a task → shows `TaskDetail` with live step-by-step updates streamed via WebSocket. Shows task status badges. Has a "New Task" button that focuses the command palette. |
| `TaskDetail.tsx` | Shows: task text, status badge, scrollable list of steps (each with action, element, reasoning). If task is running, auto-scrolls and shows a pulsing indicator. If completed, shows final result. If failed, shows error. |
| `hooks/useWebSocket.ts` | React hook: connects to `ws://localhost:8000/ws/{taskId}`, returns `{events, isConnected, error}`. Auto-reconnects on disconnect. Uses `useEffect` cleanup to close connection. |
| `hooks/useTaskApi.ts` | React hook wrapping fetch calls: `submitTask(task)`, `getTasks()`, `getTask(id)`, `cancelTask(id)`. Returns loading/error state. |
| `lib/api.ts` | `fetch` wrapper with base URL (`http://localhost:8000`), JSON headers, error handling. Configurable via `chrome.storage.local`. |
| `lib/ws.ts` | WebSocket client class: `connect(taskId)`, `disconnect()`, `onEvent(callback)`. Handles reconnection with exponential backoff. Sends heartbeat pings every 30s. |
| `types/task.ts` | TypeScript interfaces mirroring backend Pydantic models: `Task`, `TaskRequest`, `TaskResult`, `StepSummary`, `TaskStatus` |
| `types/events.ts` | TypeScript types for WS events: `AgentEvent`, `StepEvent`, `StatusEvent`, etc. |

### 4.3 Dependencies

```bash
cd extension
pnpm init
pnpm add react react-dom
pnpm add -D typescript @types/react @types/react-dom @types/chrome
pnpm add -D vite @vitejs/plugin-react tailwindcss @tailwindcss/vite
pnpm add -D postcss autoprefixer
```

### 4.4 Build Configuration

#### `vite.config.ts`
- Multiple entry points: `service-worker`, `content/index`, `sidepanel/index`, `popup/index`
- Output to `dist/` with proper structure matching manifest paths
- Use `@crxjs/vite-plugin` OR manual multi-entry config:
  ```
  build.rollupOptions.input = {
    'service-worker': 'src/background/service-worker.ts',
    'content': 'src/content/index.ts',
    'sidepanel': 'src/sidepanel/index.html',
    'popup': 'src/popup/index.html',
  }
  ```
- Consider using `vite-plugin-web-extension` for simpler MV3 setup

#### `tailwind.config.ts`
- Content paths: `["./src/**/*.{ts,tsx}"]`
- Custom theme colors for brand

#### `tsconfig.json`
- `target: "ES2022"`, `module: "ESNext"`, `jsx: "react-jsx"`, `strict: true`
- `types: ["chrome"]`

### 4.5 Shadow DOM Strategy for Content Script

The command palette must render inside a Shadow DOM to avoid CSS conflicts with the host page:

1. Content script creates `<div id="browser-agent-root">` and appends to `document.body`
2. Attaches shadow root: `element.attachShadow({mode: 'open'})`
3. Injects Tailwind styles into shadow root (import compiled CSS)
4. Mounts React app into shadow root
5. Command palette renders inside shadow DOM — fully isolated from page styles

### 4.6 Message Flow

```
User presses CMD+K
  → chrome.commands.onCommand fires in service worker
  → service worker sends message to content script
  → content script toggles CommandPalette visibility

User types task and presses Enter
  → CommandPalette sends message to service worker
  → service worker POSTs to http://localhost:8000/api/tasks
  → service worker opens WebSocket to ws://localhost:8000/ws/{task_id}
  → service worker forwards WS events to content script + sidepanel
  → CommandPalette shows mini-status
  → SidePanel shows live task detail
```

### 4.7 Verification

| Check | How |
|-------|-----|
| **Extension builds** | `cd extension && pnpm build` — `dist/` folder created with all entry points |
| **Extension loads** | Chrome → `chrome://extensions` → "Load unpacked" → select `dist/` → no errors |
| **CMD+K opens palette** | Press CMD+K on any page → floating input appears |
| **Task submission** | Type task, press Enter → backend receives POST, agent starts, palette shows "Running..." |
| **Sidebar shows status** | Open side panel → task appears in list → click → live step updates stream in |
| **Style isolation** | Palette renders correctly on complex pages (Gmail, Twitter) without style conflicts |

---

## 5. Phase 4: Context Awareness

**Goal:** Extension reads active tab context and injects it into agent tasks.

### 5.1 New/Modified Files

| File | Status | Purpose |
|------|--------|---------|
| `extension/src/content/context-extractor.ts` | **New** | Extracts: current URL, page title, meta description, visible text (innerText of body, truncated to 2000 chars), any selected text, form field values on the page. Returns a `TabContext` object. |
| `extension/src/content/highlight-overlay.ts` | **New** | Receives element selectors from the agent (via WS events) and draws colored overlays/outlines on those elements. Uses `position: absolute` overlays positioned via `getBoundingClientRect()`. Shows a tooltip ("Agent is clicking this"). Removes overlays after the action completes. |
| `extension/src/hooks/useTabContext.ts` | **New** | React hook that calls `chrome.tabs.sendMessage()` to content script to get context. Returns `TabContext`. |
| `extension/src/content/index.ts` | **Modified** | Adds message listener for `GET_TAB_CONTEXT` → calls `context-extractor.ts` → returns result. Adds listener for `HIGHLIGHT_ELEMENT` → calls `highlight-overlay.ts`. |
| `extension/src/background/service-worker.ts` | **Modified** | Before submitting task, queries active tab for context → includes `context` field in `POST /api/tasks` body. |
| `extension/src/command-palette/CommandPalette.tsx` | **Modified** | Shows extracted context below input ("Context: browsing amazon.com — Product page for..."). User can toggle context injection on/off. |
| `backend/src/agent/core.py` | **Modified** | `run_task(task, context)` → if context is provided, prepend it to the task string using `CONTEXT_INJECTION_TEMPLATE` from `prompts.py`. Format: "The user is currently on {url} viewing: {page_title}. {visible_text_summary}. Their request: {task}". |
| `backend/src/models/agent_event.py` | **Modified** | Add `HighlightEvent(type="highlight", data={"selector": str, "action": str})` to the event types. Agent emits this before each DOM interaction. |

### 5.2 Context Extraction Details

The **`context-extractor.ts`** module extracts:

| Field | Source | Max Length |
|-------|--------|------------|
| `url` | `window.location.href` | Full |
| `title` | `document.title` | 200 chars |
| `description` | `<meta name="description">` content | 500 chars |
| `visibleText` | `document.body.innerText` | 2000 chars (first N chars) |
| `selectedText` | `window.getSelection().toString()` | 1000 chars |
| `formFields` | Iterate `input`, `select`, `textarea` — collect `{name, type, value, placeholder}` | 20 fields max |
| `headings` | All `h1`-`h3` text content | 500 chars total |

This context is serialized as JSON and sent to the backend with the task.

### 5.3 Element Highlighting Flow

1. Agent runs a step (e.g., "click on Search button")
2. Backend extracts the target element's CSS selector from browser-use's action data
3. Backend emits `HighlightEvent` via WebSocket
4. Service worker forwards to content script
5. Content script draws a blue pulsing outline on the element (2px border, `rgba(59, 130, 246, 0.5)` with CSS animation)
6. After the action completes (next `StepEvent`), the highlight is removed
7. A small tooltip label appears next to the element: "Clicking..." / "Typing..." / "Scrolling..."

### 5.4 Verification

| Check | How |
|-------|-----|
| **Context extraction** | Navigate to any page → open DevTools console → send message `GET_TAB_CONTEXT` → verify returned context object contains URL, title, text |
| **Context in task** | Submit task from palette on Amazon product page → check backend logs → task string includes context prefix |
| **Element highlighting** | Run a task that clicks elements → observe blue outlines appearing on target elements before clicks |
| **Toggle context** | Toggling context off in palette → task submitted without context prefix |

---

## 6. Phase 5: Memory & Personalization

**Goal:** Persistent task history (SQLite), semantic memory for learning from past tasks (ChromaDB), and encrypted personal data vault.

### 6.1 New/Modified Files

| File | Status | Purpose |
|------|--------|---------|
| `backend/src/memory/__init__.py` | **New** | Package init, exports `SQLiteStore`, `VectorStore`, `Vault` |
| `backend/src/memory/sqlite_store.py` | **New** | `SQLiteStore` class: async CRUD via `aiosqlite`. Tables: `tasks` (id, task_text, context, status, result_json, created_at, completed_at, duration_seconds), `steps` (id, task_id, step_number, action, element, reasoning, screenshot_path, created_at), `preferences` (key, value, updated_at). Methods: `save_task()`, `get_task()`, `list_tasks(limit, offset)`, `save_step()`, `get_steps(task_id)`, `set_preference()`, `get_preference()`. DB file location: `backend/data/browser_agent.db` |
| `backend/src/memory/vector_store.py` | **New** | `VectorStore` class wrapping ChromaDB. Collection: `task_memory`. Each entry: `{id, document (task + result summary), metadata (task_id, status, created_at, domain)}`. Methods: `add_task_memory(task_id, task_text, result_summary, metadata)`, `search_similar(query, n=5) → list[MemoryResult]`. Used to inject "you've done similar tasks before" context into agent prompts. |
| `backend/src/memory/vault.py` | **New** | `PersonalVault` class: encrypted storage for PII. Uses `cryptography.fernet` with a key derived from a user passphrase (PBKDF2). Stores entries in SQLite `vault` table (key, encrypted_value, field_type). Field types: `name`, `email`, `phone`, `address_line1`, `address_city`, `address_state`, `address_zip`, `address_country`, `card_number`, `card_exp`, `card_cvv`, `card_name`. Methods: `unlock(passphrase)`, `lock()`, `set_field(key, value)`, `get_field(key)`, `get_all_decrypted()`, `is_unlocked()`. Agent can access vault via a custom tool (added to `tools.py`). |
| `backend/src/models/vault.py` | **New** | Pydantic models: `VaultEntry(field_type: str, value: str)`, `VaultUnlockRequest(passphrase: str)`, `VaultFieldUpdate(field_type: str, value: str)` |
| `backend/src/api/routes_vault.py` | **New** | REST routes: `POST /api/vault/unlock`, `POST /api/vault/lock`, `GET /api/vault/fields` (requires unlocked), `PUT /api/vault/fields/{field_type}`, `DELETE /api/vault/fields/{field_type}` |
| `backend/src/agent/tools.py` | **Modified** | Add `fill_form_from_vault` tool: when agent needs to fill a form (checkout, registration), it calls this tool which reads from the unlocked vault and fills the appropriate fields. Only works when vault is unlocked. |
| `backend/src/agent/core.py` | **Modified** | After task completion: save task + steps to SQLite via `SQLiteStore`, add to ChromaDB via `VectorStore`. Before task start: query VectorStore for similar past tasks and include summaries in the prompt as "relevant past experience". |
| `backend/src/agent/prompts.py` | **Modified** | Add `MEMORY_INJECTION_TEMPLATE` for injecting similar task summaries: "You have completed similar tasks before: {memory_summaries}. Use this experience to be more efficient." |
| `backend/src/main.py` | **Modified** | Initialize `SQLiteStore`, `VectorStore`, `PersonalVault` on startup. Inject into API routes via dependency injection. Replace in-memory task dict with SQLite queries. |
| `backend/alembic.ini` | **New** | Alembic config pointing to `backend/data/browser_agent.db` |
| `backend/migrations/env.py` | **New** | Alembic migration env |
| `backend/migrations/versions/001_initial.py` | **New** | Creates `tasks`, `steps`, `preferences`, `vault` tables |
| `backend/scripts/seed_memory.py` | **New** | Seeds ChromaDB with a few sample task memories for testing similarity search |
| `extension/src/lib/storage.ts` | **New** | `chrome.storage.local` wrapper for caching vault unlock state (not the actual secrets — just `isUnlocked` boolean) |

### 6.2 Additional Dependencies

```bash
uv add aiosqlite chromadb cryptography alembic
```

### 6.3 Database Schema

#### `tasks` table
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | UUID |
| task_text | TEXT | Original task string |
| context | TEXT | Injected context (nullable) |
| status | TEXT | pending/running/completed/failed |
| result_json | TEXT | JSON-serialized TaskResult |
| created_at | TEXT | ISO 8601 |
| completed_at | TEXT | ISO 8601 (nullable) |
| duration_seconds | REAL | (nullable) |

#### `steps` table
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | UUID |
| task_id | TEXT FK | References tasks.id |
| step_number | INTEGER | |
| action | TEXT | |
| element | TEXT | (nullable) |
| reasoning | TEXT | (nullable) |
| screenshot_path | TEXT | File path to saved screenshot (nullable) |
| created_at | TEXT | ISO 8601 |

#### `preferences` table
| Column | Type | Notes |
|--------|------|-------|
| key | TEXT PK | e.g., "default_search_engine", "preferred_language" |
| value | TEXT | |
| updated_at | TEXT | ISO 8601 |

#### `vault` table
| Column | Type | Notes |
|--------|------|-------|
| field_type | TEXT PK | e.g., "name", "email", "card_number" |
| encrypted_value | BLOB | Fernet-encrypted |
| created_at | TEXT | ISO 8601 |
| updated_at | TEXT | ISO 8601 |

### 6.4 Vector Memory Details

- **ChromaDB** runs embedded (no separate server needed for MVP)
- **Collection**: `task_memory`
- **Document**: `"{task_text} → {result_summary}"` (concatenation for better semantic matching)
- **Metadata**: `{task_id, status, domain, created_at, step_count}`
- **Embedding**: ChromaDB's default `all-MiniLM-L6-v2` (or override with `sentence-transformers` if needed)
- **Query**: Before each task, search for top-3 similar past task memories. If similarity > 0.7, inject summaries into the agent prompt.
- **Persistence**: ChromaDB `persist_directory` = `backend/data/chromadb/`

### 6.5 Verification

| Check | How |
|-------|-----|
| **SQLite created** | After first task run, `backend/data/browser_agent.db` exists with correct tables |
| **Task persists** | Submit task → restart server → `GET /api/tasks` still returns past tasks |
| **Vector search** | Run 3+ tasks → submit a similar task → check backend logs for "relevant past experience" injection |
| **Vault unlock** | `POST /api/vault/unlock` with passphrase → `PUT /api/vault/fields/name` → `GET /api/vault/fields` returns decrypted data |
| **Vault locked** | `POST /api/vault/lock` → `GET /api/vault/fields` returns 403 |
| **Form fill from vault** | Unlock vault, set name/email → run task "sign up for a newsletter" → agent uses vault data to fill form fields |
| **Tests** | `uv run pytest tests/test_memory.py -v` |

---

## 7. Phase 6: Safety & HITL

**Goal:** Agent pauses before destructive actions, sends confirmation to extension, and maintains an audit log.

### 7.1 New/Modified Files

| File | Status | Purpose |
|------|--------|---------|
| `backend/src/safety/__init__.py` | **New** | Package init |
| `backend/src/safety/hitl.py` | **New** | `HITLGate` class: maintains a list of destructive action patterns (configurable). Patterns: keywords in action target text (`"buy"`, `"purchase"`, `"submit order"`, `"delete"`, `"remove"`, `"unsubscribe"`, `"payment"`, `"confirm purchase"`, `"place order"`, `"send money"`) + URL patterns (checkout pages, payment pages). Methods: `requires_confirmation(action, url, element_text) → bool`, `async request_confirmation(task_id, action_description) → bool` (sends WS event, waits for response with timeout), `set_auto_approve(domain)` (whitelist). |
| `backend/src/safety/audit.py` | **New** | `AuditLogger` class: logs every agent action to SQLite `audit_log` table and to a structured log file. Fields: `task_id`, `timestamp`, `action_type`, `target_element`, `url`, `was_blocked`, `user_confirmed`, `model_used`. Methods: `log_action()`, `get_audit_trail(task_id)`, `get_audit_trail_by_date(start, end)`. |
| `backend/src/safety/domain_filter.py` | **New** | `DomainFilter` class: enforces `allowed_domains` and `blocked_domains` lists (stored in SQLite preferences). Methods: `is_allowed(url) → bool`, `add_allowed_domain(domain)`, `add_blocked_domain(domain)`, `get_lists()`. Integrated into agent — before any navigation action, check filter. If blocked, skip action and log. |
| `backend/src/agent/watchdog.py` | **New** | `SafetyWatchdog(BaseWatchdog)`: subclass of browser-use's `BaseWatchdog`. Hooks: `on_action_start(action)` → checks HITLGate → if destructive, pauses and sends confirmation request via WS → waits up to 60s for user response → if confirmed, proceed; if denied or timeout, skip action and log. Also hooks: `on_navigation(url)` → checks DomainFilter. All intercepted actions logged via `AuditLogger`. |
| `backend/src/agent/core.py` | **Modified** | Attach `SafetyWatchdog` to the agent. Pass `hitl_gate`, `audit_logger`, `domain_filter` instances. |
| `backend/src/api/ws.py` | **Modified** | Add handler for incoming WS messages from client: `{"type": "hitl_response", "data": {"task_id": str, "action_id": str, "approved": bool}}`. Routes response to the waiting `HITLGate`. |
| `backend/src/models/agent_event.py` | **Modified** | Add `HITLRequestEvent(type="hitl_request", data={"action_id": str, "action_description": str, "url": str, "element_text": str, "timeout_seconds": int})` |
| `extension/src/components/ConfirmDialog.tsx` | **New** | Modal dialog: "The agent wants to: [action description]. On: [url]. Allow? [Allow] [Deny]". Shows countdown timer (60s). Auto-denies on timeout. Sends `hitl_response` message back to service worker → WS. |
| `extension/src/background/service-worker.ts` | **Modified** | Handle `hitl_request` events from WS → forward to content script / sidepanel → show `ConfirmDialog`. Collect response → send back via WS. |
| `extension/src/sidepanel/TaskDetail.tsx` | **Modified** | Show HITL confirmation inline when the task is paused for confirmation. Show audit trail of blocked/confirmed actions. |

### 7.2 Additional Dependencies

None beyond what's already installed. `cryptography` was added in P5.

### 7.3 HITL Flow (Detailed)

```
1. Agent decides to click "Place Order" button
2. SafetyWatchdog.on_action_start() fires
3. HITLGate.requires_confirmation() → True (matches "place order" pattern)
4. HITLGate.request_confirmation():
   a. Generate unique action_id (UUID)
   b. Create asyncio.Event for this action_id
   c. Emit HITLRequestEvent via WebSocket to all connected clients for this task_id
   d. await asyncio.wait_for(event.wait(), timeout=60)
5. Extension receives HITLRequestEvent:
   a. Service worker forwards to content script
   b. ConfirmDialog rendered in Shadow DOM overlay
   c. User clicks "Allow" or "Deny"
   d. Extension sends hitl_response via WS: {action_id, approved: true/false}
6. Backend WS handler receives hitl_response:
   a. Sets the asyncio.Event for the matching action_id
   b. Stores the approved/denied result
7. HITLGate.request_confirmation() resumes:
   a. If approved → return True → agent proceeds
   b. If denied → return False → agent skips action, logs, tries alternative
   c. If timeout → return False → agent skips, logs timeout
8. AuditLogger records the entire interaction
```

### 7.4 Destructive Action Detection Patterns

```python
DESTRUCTIVE_KEYWORDS = [
    "buy", "purchase", "order", "checkout", "pay",
    "delete", "remove", "unsubscribe", "cancel subscription",
    "submit payment", "confirm order", "place order",
    "send money", "transfer funds", "withdraw",
    "sign contract", "agree to terms",
]

DESTRUCTIVE_URL_PATTERNS = [
    r"checkout", r"payment", r"billing",
    r"order/confirm", r"cart/checkout",
]
```

The check works by:
1. Scanning the action's target element text (button label, link text) against `DESTRUCTIVE_KEYWORDS`
2. Scanning the current page URL against `DESTRUCTIVE_URL_PATTERNS`
3. If either matches → `requires_confirmation()` returns `True`

### 7.5 Audit Log Schema

#### `audit_log` table
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | UUID |
| task_id | TEXT FK | References tasks.id |
| timestamp | TEXT | ISO 8601 |
| action_type | TEXT | click, type, navigate, scroll, etc. |
| target_element | TEXT | CSS selector or element description |
| url | TEXT | Page URL at time of action |
| was_destructive | BOOLEAN | Whether HITL gate flagged it |
| user_confirmed | BOOLEAN | User's response (null if not destructive) |
| was_blocked | BOOLEAN | Whether action was blocked |
| model_used | TEXT | gemini-2.5-pro |
| reasoning | TEXT | Agent's reasoning for the action |

### 7.6 Verification

| Check | How |
|-------|-----|
| **HITL triggers** | Run task "Buy the cheapest flight on Google Flights" → agent reaches "Book" button → extension shows confirmation dialog |
| **Deny works** | Click "Deny" in confirmation → agent skips the purchase action, logs it, continues with alternative or completes |
| **Timeout works** | Don't respond to confirmation → after 60s, action is auto-denied |
| **Domain blocking** | Add `evil.com` to blocked list → run task that navigates to `evil.com` → navigation blocked, logged |
| **Audit trail** | `GET /api/tasks/{id}` includes `audit_trail` field with all logged actions |
| **No false positives** | Run task "Search for shoes on Google" → no HITL prompts triggered for search/navigation/scroll actions |
| **Tests** | `uv run pytest tests/test_safety.py -v` |

---

## 8. Cross-Cutting Concerns

### 8.1 Error Handling Strategy

| Layer | Strategy |
|-------|----------|
| **Agent** | browser-use handles `max_failures` with loop detection. On exception: catch, log, emit `ErrorEvent` via WS, set task status to `failed`. |
| **API** | FastAPI exception handlers for `HTTPException` (400, 404, 500). Pydantic validation errors return 422. Unexpected errors return 500 with structured error body. |
| **WebSocket** | On disconnect: clean up from client registry. On send failure: remove client, log. On backend crash during task: emit `ErrorEvent` with stack trace (sanitized), set task to `failed`. |
| **Extension** | Try/catch around all message handlers. Show user-friendly error toasts. Retry API calls with exponential backoff (3 attempts). |

### 8.2 Configuration Management

All configuration flows through **one** `Settings` class in `backend/src/config.py`:

| Setting | Env Var | Default | Phase |
|---------|---------|---------|-------|
| `gemini_api_key` | `GEMINI_API_KEY` | (required) | P1 |
| `browser_user_data_dir` | `BROWSER_USER_DATA_DIR` | `None` | P1 |
| `headless` | `HEADLESS` | `false` | P1 |
| `max_steps` | `MAX_STEPS` | `50` | P1 |
| `max_failures` | `MAX_FAILURES` | `3` | P1 |
| `use_vision` | `USE_VISION` | `true` | P1 |
| `wait_between_actions` | `WAIT_BETWEEN_ACTIONS` | `1.0` | P1 |
| `log_level` | `LOG_LEVEL` | `INFO` | P1 |
| `server_host` | `SERVER_HOST` | `0.0.0.0` | P2 |
| `server_port` | `SERVER_PORT` | `8000` | P2 |
| `db_path` | `DB_PATH` | `data/browser_agent.db` | P5 |
| `chromadb_path` | `CHROMADB_PATH` | `data/chromadb/` | P5 |
| `vault_passphrase_salt` | `VAULT_SALT` | (auto-generated) | P5 |
| `hitl_timeout_seconds` | `HITL_TIMEOUT` | `60` | P6 |
| `allowed_domains` | `ALLOWED_DOMAINS` | `[]` (empty = all allowed) | P6 |
| `blocked_domains` | `BLOCKED_DOMAINS` | `[]` | P6 |

### 8.3 Logging Strategy

- Use `structlog` throughout the backend
- Every log entry includes: `timestamp`, `level`, `event`, `task_id` (when in task context)
- Agent step logs include: `step_number`, `action`, `model`, `duration_ms`
- JSON format in production, colored console in development
- Log rotation: not needed for MVP (single-file logging), add `RotatingFileHandler` post-MVP

### 8.4 Testing Strategy

| Type | Tool | Coverage Target |
|------|------|-----------------|
| Unit tests | `pytest` + `pytest-asyncio` | LLM factory, config loading, Pydantic models, HITL patterns, domain filter, vault encryption |
| Integration tests | `pytest` + `httpx.AsyncClient` | API endpoints, WebSocket communication, SQLite CRUD |
| E2E tests (manual) | CLI script + real browser | Full task execution against live websites |
| Extension tests | Vitest (optional, P3+) | React component rendering, hook behavior |

**Mock strategy:** Mock `ChatGoogleGenerativeAI` in unit tests (return canned responses). Mock `browser-use Agent` in API tests (return a pre-built `AgentHistoryList`). Only use real LLM + browser in E2E tests.

### 8.5 Security Considerations

| Concern | Mitigation |
|---------|------------|
| API key exposure | `.env` file git-ignored; never sent to extension; only used server-side |
| Vault encryption | Fernet symmetric encryption; key derived from user passphrase via PBKDF2 (100k iterations); vault auto-locks on server restart |
| CORS | Restrict to `chrome-extension://{extension_id}` and `localhost` in production |
| Input validation | All API inputs validated via Pydantic; task text sanitized (strip HTML, limit length to 2000 chars) |
| Browser profile | If using `user_data_dir`, warn user that agent inherits their cookies/sessions; recommend a separate Chrome profile |
| Extension permissions | Minimal: `activeTab` (not `<all_urls>` for host permissions beyond localhost), `sidePanel`, `storage` |

### 8.6 Project Tooling

| Tool | Purpose | Config |
|------|---------|--------|
| `uv` | Python package manager | `backend/pyproject.toml` |
| `pnpm` | JS package manager | `extension/package.json` |
| `ruff` | Python linting + formatting | `[tool.ruff]` section in `pyproject.toml`: `line-length = 100`, `target-version = "py312"` |
| `prettier` | JS/TS formatting | `.prettierrc` in `extension/` |
| `eslint` | JS/TS linting | `eslint.config.js` in `extension/` |
| `alembic` | DB migrations | `backend/alembic.ini` |

### 8.7 Development Workflow

```bash
# Terminal 1: Backend
cd backend
uv run uvicorn src.main:app --reload --port 8000

# Terminal 2: Extension (dev build with watch)
cd extension
pnpm dev    # vite build --watch, output to dist/

# Then load dist/ as unpacked extension in Chrome
# Changes to extension code auto-rebuild; reload extension in Chrome to pick up changes
```

### 8.8 Phase Execution Timeline (Estimated)

| Phase | Estimated Duration | Dependency |
|-------|-------------------|------------|
| Phase 1: Backend Core | 3-5 days | None |
| Phase 2: API + WebSocket | 2-3 days | Phase 1 |
| Phase 3: Extension Shell | 3-5 days | Phase 2 |
| Phase 4: Context Awareness | 2-3 days | Phase 3 |
| Phase 5: Memory + Vault | 3-4 days | Phase 2 |
| Phase 6: Safety + HITL | 3-4 days | Phase 5 + Phase 3 |
| **Total** | **~16-24 days** | |

> Phases 3-4 (extension) can be developed in parallel with Phases 5-6 (memory/safety) since they share only the API interface.

---

## Summary

This plan produces a 6-phase build of a Comet-like browser agent:

1. **P1 (MVP):** Python CLI → browser-use + Gemini → completes tasks in a real browser
2. **P2:** FastAPI server with WebSocket streaming → any client can control the agent
3. **P3:** Chrome Extension shell with CMD+K palette and sidebar → user-facing UI
4. **P4:** Tab context extraction and element highlighting → context-aware agent
5. **P5:** SQLite + ChromaDB + encrypted vault → persistent memory and personalization
6. **P6:** HITL watchdog + audit log + domain filtering → safe autonomous operation

Every file, dependency, schema, and verification step is specified. Execute phases sequentially (with P3-4 ‖ P5-6 parallelism possible) to incrementally build the full product.
