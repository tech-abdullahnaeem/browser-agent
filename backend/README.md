# Browser Agent — Backend

AI browser automation agent powered by [browser-use](https://github.com/browser-use/browser-use) and Google Gemini.

## Quick Start

### 1. Install dependencies

```bash
cd backend
uv sync
uv run playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY
```

### 3. Run a task

```bash
uv run python scripts/run_task.py "Go to google.com and search for 'browser automation'"
```

Options:
```bash
uv run python scripts/run_task.py --headless "Search Wikipedia for Python programming"
uv run python scripts/run_task.py --max-steps 30 "Find the weather in New York"
```

### 4. Run tests

```bash
uv run pytest -v
```

## Project Structure

```
backend/
├── src/
│   ├── config.py          # Settings loaded from .env
│   ├── agent/
│   │   ├── core.py        # BrowserAgentRunner — main orchestration
│   │   ├── llm.py         # LLM factory (Gemini Flash + Pro)
│   │   ├── tools.py       # Custom browser-use tools
│   │   ├── planner.py     # Multi-model task planner
│   │   └── prompts.py     # System prompt templates
│   ├── models/
│   │   └── task.py        # Pydantic models for tasks/results
│   └── utils/
│       └── logging.py     # Structured logging setup
├── scripts/
│   └── run_task.py        # CLI entry point
└── tests/
```
