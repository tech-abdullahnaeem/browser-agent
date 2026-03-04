#!/usr/bin/env python3
"""CLI entry point — run a browser automation task from the command line.

Usage::

    uv run python scripts/run_task.py "Go to google.com and search for 'hello world'"
    uv run python scripts/run_task.py --headless "Search Wikipedia for Python"
    uv run python scripts/run_task.py --max-steps 30 "Find the weather in NYC"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Ensure the backend src package is importable when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent.core import BrowserAgentRunner
from src.config import Settings
from src.models.task import StepSummary
from src.utils.logging import setup_logging


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a browser automation task via browser-use + Gemini",
    )
    parser.add_argument("task", help="Natural-language task to perform")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--max-steps", type=int, default=None, help="Max agent steps (default: from .env)")
    parser.add_argument("--no-vision", action="store_true", help="Disable vision (screenshots)")
    parser.add_argument("--no-planning", action="store_true", help="Disable multi-model planning")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable DEBUG logging")
    return parser.parse_args()


def _print_step(step: StepSummary) -> None:
    """Pretty-print a step to stdout as it completes."""
    status_icon = "✓" if step.success else ("✗" if step.success is False else "…")
    print(f"  [{status_icon}] Step {step.step_number}: {step.action}", end="")
    if step.element:
        print(f" → {step.element}", end="")
    if step.error:
        print(f"  ⚠ {step.error}", end="")
    print()


async def main() -> None:
    args = _parse_args()

    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_level)

    # Build settings with CLI overrides
    overrides: dict = {}
    if args.headless:
        overrides["headless"] = True
    if args.max_steps is not None:
        overrides["max_steps"] = args.max_steps
    if args.no_vision:
        overrides["use_vision"] = False
    if args.no_planning:
        overrides["enable_planning"] = False

    settings = Settings(**overrides)  # type: ignore[call-arg]

    runner = BrowserAgentRunner(settings=settings)

    print(f"\n🚀 Starting task: {args.task}")
    print(f"   Model: {settings.flash_model} | Headless: {settings.headless} | Vision: {settings.use_vision}")
    print(f"   Max steps: {settings.max_steps} | Planning: {settings.enable_planning}")
    print("─" * 60)

    result = await runner.run_task(
        task=args.task,
        on_step=_print_step,
    )

    print("─" * 60)
    if result.status.value == "completed":
        print(f"✅ Task completed in {result.duration_seconds}s ({result.total_steps} steps)")
    else:
        print(f"❌ Task {result.status.value} after {result.duration_seconds}s ({result.total_steps} steps)")

    if result.final_result:
        print(f"\n📋 Result:\n{result.final_result}")
    if result.error:
        print(f"\n⚠️  Error: {result.error}")

    # Dump full JSON result
    print(f"\n{'─' * 60}")
    print("Full result JSON:")
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
