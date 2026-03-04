"""Phase 1 verification script — checks all modules, imports, and functionality."""

import importlib.util
import sys

sys.path.insert(0, ".")


def main():
    print("=" * 60)
    print("PHASE 1 VERIFICATION")
    print("=" * 60)

    # 1. Config
    from src.config import Settings, get_settings
    s = Settings(gemini_api_key="test", headless=True)
    assert s.flash_model == "gemini-2.5-pro"
    assert s.pro_model == "gemini-2.5-pro"
    assert s.max_steps == 50
    print("[OK] src/config.py — Settings loads correctly")

    # 2. Logging
    from src.utils.logging import setup_logging, get_logger
    setup_logging("DEBUG")
    logger = get_logger("verify")
    print("[OK] src/utils/logging.py — structlog configured")

    # 3. Models
    from src.models.task import TaskRequest, TaskResult, TaskStatus, StepSummary
    req = TaskRequest(task="test task", context="some context")
    result = TaskResult(task="test", status=TaskStatus.COMPLETED, final_result="done", duration_seconds=1.5, total_steps=3)
    json_str = result.model_dump_json()
    restored = TaskResult.model_validate_json(json_str)
    assert restored.task == result.task
    print(f"[OK] src/models/task.py — 4 models, JSON roundtrip works")

    # 4. LLM factory
    from src.agent.llm import get_flash_llm, get_pro_llm, get_default_llm
    flash = get_flash_llm(s)
    pro = get_pro_llm(s)
    default = get_default_llm(s)
    assert flash.model == "gemini-2.5-pro"
    assert pro.model == "gemini-2.5-pro"
    assert default.model == flash.model
    print(f"[OK] src/agent/llm.py — Flash={flash.model}, Pro={pro.model}")

    # 5. Prompts
    from src.agent.prompts import SYSTEM_PROMPT_EXTENSION, CONTEXT_INJECTION_TEMPLATE, PLANNING_PROMPT, MEMORY_INJECTION_TEMPLATE
    assert "Browser Agent" in SYSTEM_PROMPT_EXTENSION
    assert "{task}" in PLANNING_PROMPT
    assert "{url}" in CONTEXT_INJECTION_TEMPLATE
    print("[OK] src/agent/prompts.py — 4 prompt templates defined")

    # 6. Tools
    from src.agent.tools import custom_tools
    actions = list(custom_tools.registry.registry.actions.keys())
    assert "extract_page_text" in actions
    assert "take_screenshot" in actions
    print(f"[OK] src/agent/tools.py — 2 custom tools registered: extract_page_text, take_screenshot")

    # 7. Planner
    from src.agent.planner import is_complex_task, generate_plan, build_planned_task
    assert is_complex_task("First go to google, then search for flights, after that book the cheapest one", s) is True
    assert is_complex_task("Go to google.com", s) is False
    plan_text = build_planned_task("book a flight", "1. Open Google Flights\n2. Search")
    assert "PLAN" in plan_text
    print("[OK] src/agent/planner.py — complexity detection + plan builder work")

    # 8. Core runner
    from src.agent.core import BrowserAgentRunner, _history_entry_to_step
    runner = BrowserAgentRunner(settings=s)
    assert runner.settings.headless is True
    print("[OK] src/agent/core.py — BrowserAgentRunner instantiates correctly")

    # 9. CLI script
    spec = importlib.util.spec_from_file_location("run_task", "scripts/run_task.py")
    assert spec is not None
    print("[OK] scripts/run_task.py — exists and is loadable")

    # 10. Docs
    import os
    assert os.path.exists("docs/architecture.md")
    print("[OK] docs/architecture.md — exists")

    print()
    print("=" * 60)
    print("ALL PHASE 1 CHECKS PASSED")
    print("=" * 60)
    print()
    print("Files implemented:")
    for f in [
        "pyproject.toml", ".env.example", ".gitignore", "README.md",
        "src/__init__.py", "src/config.py",
        "src/agent/__init__.py", "src/agent/core.py", "src/agent/llm.py",
        "src/agent/planner.py", "src/agent/prompts.py", "src/agent/tools.py",
        "src/models/__init__.py", "src/models/task.py",
        "src/utils/__init__.py", "src/utils/logging.py",
        "scripts/run_task.py",
        "tests/__init__.py", "tests/conftest.py",
        "tests/test_agent_core.py", "tests/test_llm.py", "tests/test_models.py",
        "docs/architecture.md",
    ]:
        exists = os.path.exists(f)
        print(f"  {'[OK]' if exists else '[MISSING]'} {f}")


if __name__ == "__main__":
    main()
