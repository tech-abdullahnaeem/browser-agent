#!/usr/bin/env python3
"""Aggressive live test for Phase 4 QA tools.

Tests each QA tool individually against real websites, then tests the full
QA audit flow. Runs headless for speed.

Usage::
    cd backend && uv run python scripts/test_qa_tools_live.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent.core import BrowserAgentRunner
from src.config import Settings
from src.models.task import StepSummary


DIVIDER = "═" * 70


def print_step(step: StepSummary) -> None:
    icon = "✓" if step.success else ("✗" if step.success is False else "…")
    print(f"    [{icon}] Step {step.step_number}: {step.action}", end="")
    if step.element:
        print(f" → {step.element}", end="")
    print()


async def run_test(runner: BrowserAgentRunner, name: str, task: str) -> dict:
    """Run a single test and return result summary."""
    print(f"\n{DIVIDER}")
    print(f"  TEST: {name}")
    print(f"  Task: {task[:100]}...")
    print(DIVIDER)

    start = time.monotonic()
    try:
        result = await runner.run_task(task=task, on_step=print_step)
        elapsed = time.monotonic() - start

        status = result.status.value
        icon = "✅" if status == "completed" else "❌"
        print(f"\n  {icon} {status.upper()} in {elapsed:.1f}s ({result.total_steps} steps)")

        if result.final_result:
            # Print first 500 chars of result
            trimmed = result.final_result[:500]
            print(f"\n  📋 Result (first 500 chars):\n{trimmed}")

        if result.error:
            print(f"\n  ⚠️  Error: {result.error}")

        return {
            "name": name,
            "status": status,
            "steps": result.total_steps,
            "duration": round(elapsed, 1),
            "has_result": bool(result.final_result),
            "result_length": len(result.final_result) if result.final_result else 0,
            "error": result.error,
        }
    except Exception as e:
        elapsed = time.monotonic() - start
        print(f"\n  💥 EXCEPTION in {elapsed:.1f}s: {e}")
        return {
            "name": name,
            "status": "exception",
            "steps": 0,
            "duration": round(elapsed, 1),
            "has_result": False,
            "result_length": 0,
            "error": str(e),
        }


async def main() -> None:
    settings = Settings(headless=True, max_steps=15, enable_planning=False)
    runner = BrowserAgentRunner(settings=settings)

    print("\n" + "█" * 70)
    print("  PHASE 4 QA TOOLS — AGGRESSIVE LIVE TEST")
    print(f"  Model: {settings.flash_model} | Headless: True | Max steps: 15")
    print("█" * 70)

    tests = [
        # Test 1: Accessibility audit on a real site
        (
            "Accessibility Audit (Wikipedia)",
            "Go to https://en.wikipedia.org/wiki/Web_accessibility and use the "
            "audit_accessibility tool to check this page for accessibility issues. "
            "Report all findings.",
        ),
        # Test 2: Console errors check
        (
            "Console Errors Check (GitHub)",
            "Go to https://github.com and use the check_console_errors tool to check "
            "for any JavaScript errors or failed resources. Report what you find.",
        ),
        # Test 3: Performance analysis
        (
            "Performance Check (Wikipedia)",
            "Go to https://en.wikipedia.org/wiki/Main_Page and use the check_performance "
            "tool to analyze the performance of this page. Report all metrics and recommendations.",
        ),
        # Test 4: SEO audit
        (
            "SEO Audit (Python.org)",
            "Go to https://www.python.org and use the check_seo tool to audit the SEO "
            "of this page. Report all issues found.",
        ),
        # Test 5: Form validation on a page with forms
        (
            "Form Validation (Google)",
            "Go to https://www.google.com and use the validate_forms tool to check all "
            "forms on the page. Report the findings.",
        ),
        # Test 6: Broken links check
        (
            "Broken Links Check (Example.com)",
            "Go to https://example.com and use the check_broken_links tool to test all "
            "links on the page. Report any broken or problematic links.",
        ),
        # Test 7: Full QA audit combining multiple tools
        (
            "Full QA Audit (Hacker News)",
            "Go to https://news.ycombinator.com and perform a comprehensive QA audit. "
            "Use audit_accessibility, check_console_errors, and check_performance tools. "
            "Summarize all issues by severity.",
        ),
    ]

    results = []
    total_start = time.monotonic()

    for name, task in tests:
        result = await run_test(runner, name, task)
        results.append(result)

    total_elapsed = time.monotonic() - total_start

    # Print summary
    print(f"\n\n{'█' * 70}")
    print("  TEST SUMMARY")
    print(f"{'█' * 70}")
    print(f"  Total time: {total_elapsed:.1f}s")
    print(f"  Tests run: {len(results)}")

    passed = sum(1 for r in results if r["status"] == "completed")
    failed = sum(1 for r in results if r["status"] != "completed")

    print(f"  Passed: {passed} | Failed: {failed}")
    print()

    for r in results:
        icon = "✅" if r["status"] == "completed" else "❌"
        print(f"  {icon} {r['name']}: {r['status']} | {r['steps']} steps | "
              f"{r['duration']}s | result: {r['result_length']} chars")
        if r["error"]:
            print(f"     ⚠️  {r['error'][:100]}")

    print(f"\n{'█' * 70}")

    # Exit with failure code if any test failed
    if failed > 0:
        print(f"\n⚠️  {failed} test(s) did not complete successfully.")
        sys.exit(1)
    else:
        print(f"\n🎉 All {passed} tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
