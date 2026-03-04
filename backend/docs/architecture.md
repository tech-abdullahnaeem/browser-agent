# Architecture Overview

## High-Level Diagram

```mermaid
graph TB
    subgraph "User Interface"
        CLI["CLI (scripts/run_task.py)"]
        EXT["Chrome Extension (Phase 3+)"]
    end

    subgraph "Backend (Python)"
        API["FastAPI Server (Phase 2+)"]
        RUNNER["BrowserAgentRunner"]
        
        subgraph "Agent Layer"
            PLANNER["TaskPlanner (Gemini Pro)"]
            AGENT["browser-use Agent (Gemini Flash)"]
            TOOLS["Custom Tools"]
        end
        
        subgraph "Memory (Phase 5+)"
            SQLITE["SQLite"]
            VECTOR["ChromaDB"]
            VAULT["Personal Vault"]
        end
        
        subgraph "Safety (Phase 6+)"
            HITL["HITL Watchdog"]
            AUDIT["Audit Log"]
            DOMAIN["Domain Filter"]
        end
    end

    subgraph "External"
        GEMINI["Google Gemini API"]
        BROWSER["Chrome Browser (Playwright/CDP)"]
    end

    CLI --> RUNNER
    EXT -->|"WS + REST"| API
    API --> RUNNER
    RUNNER --> PLANNER
    RUNNER --> AGENT
    AGENT --> TOOLS
    AGENT --> BROWSER
    PLANNER --> GEMINI
    AGENT --> GEMINI
    RUNNER --> SQLITE
    RUNNER --> VECTOR
    TOOLS --> VAULT
    AGENT --> HITL
    HITL --> AUDIT
    AGENT --> DOMAIN
```

## Phase 1 Data Flow

```mermaid
sequenceDiagram
    participant U as User (CLI)
    participant R as BrowserAgentRunner
    participant P as TaskPlanner
    participant A as browser-use Agent
    participant L as Gemini Flash
    participant B as Browser

    U->>R: run_task("Search for flights...")
    
    alt Task is complex
        R->>P: generate_plan(task)
        P->>L: Gemini Pro: decompose task
        L-->>P: Numbered plan
        P-->>R: Augmented task string
    end

    R->>A: Agent(task, llm=flash, browser_session)
    
    loop Each Step (max_steps)
        A->>B: Capture DOM state
        B-->>A: DOM elements + screenshot
        A->>L: State + task → next action
        L-->>A: Action decision
        A->>B: Execute action (click/type/navigate)
        B-->>A: Action result
        A-->>R: on_step_end callback
        R-->>U: Print step summary
    end

    A-->>R: AgentHistoryList (done)
    R-->>U: TaskResult JSON
```

## Key Components (Phase 1)

| Component | File | Responsibility |
|-----------|------|----------------|
| Settings | `src/config.py` | Load env vars, provide typed config |
| LLM Factory | `src/agent/llm.py` | Create Gemini Flash / Pro instances |
| Prompts | `src/agent/prompts.py` | System messages, templates |
| Planner | `src/agent/planner.py` | Complex task decomposition via Pro |
| Tools | `src/agent/tools.py` | Custom browser-use actions |
| Runner | `src/agent/core.py` | Orchestrate agent lifecycle |
| Models | `src/models/task.py` | Pydantic schemas for tasks/results |
| CLI | `scripts/run_task.py` | Command-line entry point |
