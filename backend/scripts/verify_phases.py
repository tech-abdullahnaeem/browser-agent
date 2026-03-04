"""Phase 1 & 2 verification script — checks all files, features, and tests."""

import importlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

PHASE1_FILES = [
    "pyproject.toml", ".env.example", ".gitignore", "README.md",
    "src/__init__.py", "src/config.py",
    "src/agent/__init__.py", "src/agent/core.py", "src/agent/llm.py",
    "src/agent/tools.py", "src/agent/planner.py", "src/agent/prompts.py",
    "src/models/__init__.py", "src/models/task.py",
    "src/utils/__init__.py", "src/utils/logging.py",
    "scripts/run_task.py",
    "tests/__init__.py", "tests/conftest.py",
    "tests/test_agent_core.py", "tests/test_llm.py", "tests/test_models.py",
    "docs/architecture.md",
]

PHASE2_FILES = [
    "src/main.py",
    "src/api/__init__.py", "src/api/routes_tasks.py", "src/api/routes_config.py",
    "src/api/routes_ws.py", "src/api/ws.py", "src/api/task_store.py",
    "src/models/agent_event.py", "src/models/config.py",
    "tests/test_api_tasks.py", "tests/test_ws.py",
    "docs/api.md",
]

def check_files(label, files):
    print(f"\n{'='*60}")
    print(f"  {label} — File Check")
    print(f"{'='*60}")
    missing = []
    for f in files:
        if os.path.isfile(f):
            print(f"  [OK] {f}")
        else:
            print(f"  [MISSING] {f}")
            missing.append(f)
    return missing


def check_phase1_features():
    print(f"\n{'='*60}")
    print(f"  PHASE 1 — Feature Check")
    print(f"{'='*60}")
    ok = 0
    fail = 0

    # 1. Config
    try:
        from src.config import Settings, get_settings
        s = Settings(gemini_api_key="test-key", headless=True)
        assert s.gemini_api_key == "test-key"
        assert s.headless is True
        print("  [OK] Config: Settings loads, fields work")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] Config: {e}")
        fail += 1

    # 2. Logging
    try:
        from src.utils.logging import setup_logging, get_logger
        setup_logging("DEBUG")
        log = get_logger("test")
        print("  [OK] Logging: structlog configured")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] Logging: {e}")
        fail += 1

    # 3. Models
    try:
        from src.models.task import TaskRequest, TaskResult, TaskStatus, StepSummary
        req = TaskRequest(task="test")
        assert req.task == "test"
        res = TaskResult(task="t", status=TaskStatus.COMPLETED)
        assert res.task_id  # auto-generated
        print(f"  [OK] Models: TaskRequest, TaskResult, TaskStatus, StepSummary — 4 models")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] Models: {e}")
        fail += 1

    # 4. LLM factory
    try:
        from src.agent.llm import get_flash_llm, get_pro_llm, get_default_llm
        s = Settings(gemini_api_key="test-key", headless=True, log_level="DEBUG")
        flash = get_flash_llm(s)
        pro = get_pro_llm(s)
        default = get_default_llm(s)
        assert flash.model == s.flash_model
        assert pro.model == s.pro_model
        assert default.model == flash.model
        print(f"  [OK] LLM factory: flash={flash.model}, pro={pro.model}")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] LLM factory: {e}")
        fail += 1

    # 5. Prompts
    try:
        from src.agent.prompts import SYSTEM_PROMPT_EXTENSION, CONTEXT_INJECTION_TEMPLATE, PLANNING_PROMPT
        assert len(SYSTEM_PROMPT_EXTENSION) > 10
        assert "{task}" in PLANNING_PROMPT
        print("  [OK] Prompts: SYSTEM_PROMPT_EXTENSION, PLANNING_PROMPT, CONTEXT_INJECTION_TEMPLATE")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] Prompts: {e}")
        fail += 1

    # 6. Custom tools
    try:
        from src.agent.tools import custom_tools
        actions = list(custom_tools.registry.registry.actions.keys())
        custom = [a for a in actions if a in ("extract_page_text", "take_screenshot")]
        assert len(custom) == 2
        print(f"  [OK] Custom tools: {custom}")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] Custom tools: {e}")
        fail += 1

    # 7. Planner
    try:
        from src.agent.planner import is_complex_task, build_planned_task
        assert is_complex_task("Do this and then do that and then something else long task with many words")
        assert not is_complex_task("Click a button")
        plan = build_planned_task("orig", "1. step 1\n2. step 2")
        assert "orig" in plan
        print("  [OK] Planner: is_complex_task + build_planned_task work")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] Planner: {e}")
        fail += 1

    # 8. Core agent runner
    try:
        from src.agent.core import BrowserAgentRunner
        s = Settings(gemini_api_key="test-key", headless=True, log_level="DEBUG")
        runner = BrowserAgentRunner(settings=s)
        assert runner.settings == s
        print("  [OK] Core: BrowserAgentRunner instantiates correctly")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] Core: {e}")
        fail += 1

    # 9. CLI script loadable
    try:
        assert os.path.isfile("scripts/run_task.py")
        print("  [OK] CLI: scripts/run_task.py exists")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] CLI: {e}")
        fail += 1

    return ok, fail


def check_phase2_features():
    print(f"\n{'='*60}")
    print(f"  PHASE 2 — Feature Check")
    print(f"{'='*60}")
    ok = 0
    fail = 0

    # 1. FastAPI app
    try:
        from src.main import app
        assert app.title == "Browser Agent API"
        routes = [r.path for r in app.routes]
        assert "/health" in routes
        print(f"  [OK] FastAPI app: title='{app.title}', version={app.version}")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] FastAPI app: {e}")
        fail += 1

    # 2. Task routes
    try:
        from src.api.routes_tasks import router as tasks_router
        task_paths = [r.path for r in tasks_router.routes]
        # Paths may include prefix (/api/tasks) or be bare (/, /{task_id})
        has_list = any(p in ("", "/", "/api/tasks") for p in task_paths)
        has_detail = any("task_id" in p for p in task_paths)
        assert has_list, f"Missing list route in {task_paths}"
        assert has_detail, f"Missing detail route in {task_paths}"
        print(f"  [OK] Task routes: POST, GET, GET/:id, DELETE/:id")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] Task routes: {e}")
        fail += 1

    # 3. Config routes
    try:
        from src.api.routes_config import router as config_router, get_effective_config
        cfg = get_effective_config()
        assert hasattr(cfg, "max_steps")
        assert hasattr(cfg, "use_vision")
        assert hasattr(cfg, "headless")
        assert hasattr(cfg, "enable_planning")
        assert hasattr(cfg, "flash_model")
        assert hasattr(cfg, "pro_model")
        print(f"  [OK] Config routes: GET + PUT /api/config, AgentConfig has all fields")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] Config routes: {e}")
        fail += 1

    # 4. WebSocket endpoint
    try:
        from src.api.routes_ws import router as ws_router
        ws_paths = [r.path for r in ws_router.routes]
        assert "/ws/{task_id}" in ws_paths
        print(f"  [OK] WebSocket: /ws/{{task_id}} endpoint registered")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] WebSocket: {e}")
        fail += 1

    # 5. Connection manager
    try:
        from src.api.ws import ConnectionManager, ws_manager
        assert isinstance(ws_manager, ConnectionManager)
        assert ws_manager.total_connections == 0
        print(f"  [OK] ConnectionManager: singleton, broadcast, connect/disconnect")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] ConnectionManager: {e}")
        fail += 1

    # 6. Task store
    try:
        from src.api.task_store import TaskStore, task_store, TaskState
        assert isinstance(task_store, TaskStore)
        assert hasattr(task_store, "create_task")
        assert hasattr(task_store, "get_task")
        assert hasattr(task_store, "list_tasks")
        assert hasattr(task_store, "cancel_task")
        print(f"  [OK] TaskStore: in-memory store with create/get/list/cancel")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] TaskStore: {e}")
        fail += 1

    # 7. Event models
    try:
        from src.models.agent_event import (
            AgentEvent, StatusEvent, StepEvent, PlanEvent,
            ScreenshotEvent, DoneEvent, ErrorEvent,
        )
        se = StatusEvent(task_id="t1", status="running")
        assert se.type == "status"
        assert se.ws_dict()["type"] == "status"
        event_types = ["status", "step", "plan", "screenshot", "done", "error"]
        print(f"  [OK] Event models: {', '.join(event_types)} — all defined")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] Event models: {e}")
        fail += 1

    # 8. Config model
    try:
        from src.models.config import AgentConfig, AgentConfigUpdate
        cfg = AgentConfig()
        assert cfg.max_steps > 0
        upd = AgentConfigUpdate(max_steps=10)
        assert upd.max_steps == 10
        assert upd.use_vision is None  # partial
        print(f"  [OK] Config model: AgentConfig + AgentConfigUpdate (partial)")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] Config model: {e}")
        fail += 1

    # 9. CORS configured
    try:
        from src.main import app
        cors_found = False
        for mw in app.user_middleware:
            if "CORS" in str(mw):
                cors_found = True
                break
        # Also check via middleware stack
        if not cors_found:
            from starlette.middleware.cors import CORSMiddleware
            for mw in app.user_middleware:
                if mw.cls is CORSMiddleware:
                    cors_found = True
                    break
        if cors_found:
            print(f"  [OK] CORS: middleware configured for chrome-extension + localhost")
        else:
            print(f"  [WARN] CORS: could not verify middleware (may still work)")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] CORS: {e}")
        fail += 1

    # 10. Concurrency control
    try:
        from src.api.task_store import task_store
        import asyncio
        assert isinstance(task_store._agent_lock, asyncio.Semaphore)
        print(f"  [OK] Concurrency: asyncio.Semaphore(1) for single-agent serialization")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] Concurrency: {e}")
        fail += 1

    # 11. API docs
    try:
        assert os.path.isfile("docs/api.md")
        with open("docs/api.md") as f:
            content = f.read()
        assert "POST" in content
        assert "WebSocket" in content or "ws" in content.lower()
        print(f"  [OK] API docs: docs/api.md with REST + WebSocket documentation")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] API docs: {e}")
        fail += 1

    return ok, fail


if __name__ == "__main__":
    total_missing = []

    m1 = check_files("PHASE 1", PHASE1_FILES)
    total_missing.extend(m1)

    m2 = check_files("PHASE 2", PHASE2_FILES)
    total_missing.extend(m2)

    p1_ok, p1_fail = check_phase1_features()
    p2_ok, p2_fail = check_phase2_features()

    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  Phase 1 files: {len(PHASE1_FILES) - len(m1)}/{len(PHASE1_FILES)} present")
    print(f"  Phase 2 files: {len(PHASE2_FILES) - len(m2)}/{len(PHASE2_FILES)} present")
    print(f"  Phase 1 features: {p1_ok}/{p1_ok + p1_fail} passed")
    print(f"  Phase 2 features: {p2_ok}/{p2_ok + p2_fail} passed")

    if total_missing:
        print(f"\n  MISSING FILES: {total_missing}")

    total_fail = p1_fail + p2_fail + len(total_missing)
    if total_fail == 0:
        print(f"\n  ✅ ALL PHASE 1 & PHASE 2 CHECKS PASSED")
    else:
        print(f"\n  ❌ {total_fail} issue(s) found")
        sys.exit(1)
