#!/usr/bin/env python3
"""Test QA agent via REST API + WebSocket streaming.

Submits a QA audit task via POST, then connects via WebSocket to stream
real-time events (steps, highlights, done). Verifies the full API flow.

Usage::
    cd backend && uv run python scripts/test_qa_api_ws.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time

import httpx
import websockets


API_BASE = "http://127.0.0.1:8000"
WS_BASE = "ws://127.0.0.1:8000"


async def test_qa_via_api():
    """Submit a QA task via REST and stream results via WebSocket."""
    print("\n" + "█" * 70)
    print("  QA AGENT — API + WEBSOCKET E2E TEST")
    print("█" * 70)

    # 1. Submit task via REST API with context
    context = (
        "URL: https://news.ycombinator.com\n"
        "Title: Hacker News\n"
        "Viewport: 1440x900\n"
        "\nConsole Errors (0):\n"
        "\nAccessibility Issues (3):\n"
        "  [error] input-no-label: Form input has no associated label\n"
        "  [warning] img-no-alt: 2 images missing alt text\n"
        "  [warning] no-skip-nav: Page has navigation but no skip-to-content link\n"
        "\nPage Stats: 67 links, 1 forms, 3 images\n"
        "DOM Nodes: 814\n"
        "Load Time: 580ms\n"
    )

    task = (
        "Go to https://news.ycombinator.com and perform a quick accessibility audit. "
        "Use the audit_accessibility tool. Report all issues found with severity."
    )

    print(f"\n  📤 Submitting task via POST /api/tasks...")
    print(f"     Task: {task[:80]}...")
    print(f"     Context: {len(context)} chars of pre-scanned QA data")

    start = time.monotonic()

    async with httpx.AsyncClient(base_url=API_BASE, timeout=10) as client:
        resp = await client.post(
            "/api/tasks",
            json={"task": task, "context": context},
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        task_id = data["task_id"]
        print(f"  ✅ Task created: {task_id} (status: {data['status']})")

    # 2. Connect WebSocket and stream events
    print(f"\n  📡 Connecting WebSocket: {WS_BASE}/ws/{task_id}")

    events_received = []
    final_result = None

    try:
        async with websockets.connect(f"{WS_BASE}/ws/{task_id}") as ws:
            print("  ✅ WebSocket connected\n")

            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=120)
                    event = json.loads(msg)
                    event_type = event.get("type", "unknown")

                    if event_type == "pong":
                        continue

                    events_received.append(event)

                    if event_type == "status":
                        print(f"    📌 Status: {event.get('status', '?')}")
                    elif event_type == "step":
                        step_data = event.get("data", {})
                        step_num = step_data.get("step_number", "?")
                        action = step_data.get("action", "?")
                        success = step_data.get("success")
                        icon = "✓" if success else ("✗" if success is False else "…")
                        print(f"    [{icon}] Step {step_num}: {action}")
                        if step_data.get("element"):
                            print(f"        → {str(step_data['element'])[:80]}")
                    elif event_type == "plan":
                        print(f"    📝 Plan received ({len(event.get('plan', ''))} chars)")
                    elif event_type == "highlight":
                        print(f"    🔦 Highlight: {event.get('selector', '?')} → {event.get('label', 'no label')}")
                    elif event_type == "done":
                        done_data = event.get("data", {})
                        final_result = done_data.get("final_result", "")
                        total_steps = done_data.get("total_steps", 0)
                        duration = done_data.get("duration_seconds", 0)
                        print(f"\n    ✅ DONE: {done_data.get('status', '?')} | {total_steps} steps | {duration}s")
                        break
                    elif event_type == "error":
                        print(f"\n    ❌ ERROR: {event.get('message', '?')}")
                        break
                    else:
                        print(f"    ❓ Unknown event: {event_type}")

                except asyncio.TimeoutError:
                    print("    ⏰ Timeout waiting for WebSocket message (120s)")
                    break

    except Exception as e:
        print(f"  ❌ WebSocket error: {e}")

    elapsed = time.monotonic() - start

    # 3. Verify task result via REST
    print(f"\n  📥 Fetching task result via GET /api/tasks/{task_id}...")

    async with httpx.AsyncClient(base_url=API_BASE, timeout=10) as client:
        resp = await client.get(f"/api/tasks/{task_id}")
        if resp.status_code == 200:
            detail = resp.json()
            print(f"  ✅ Task detail: status={detail['status']} | steps={detail['total_steps']}")
        else:
            print(f"  ⚠️  Could not fetch task: {resp.status_code}")

    # 4. Summary
    print(f"\n{'═' * 70}")
    print("  E2E TEST SUMMARY")
    print(f"{'═' * 70}")
    print(f"  Total time: {elapsed:.1f}s")
    print(f"  Events received: {len(events_received)}")
    print(f"  Event types: {[e.get('type') for e in events_received]}")

    if final_result:
        print(f"\n  📋 Final result (first 500 chars):")
        print(f"  {final_result[:500]}")

    # Assertions
    event_types = [e.get("type") for e in events_received]
    assert "status" in event_types, "Expected at least one status event"
    assert "step" in event_types, "Expected at least one step event"
    assert "done" in event_types, "Expected a done event"
    assert final_result, "Expected a non-empty final result"
    assert len(final_result) > 50, f"Result too short ({len(final_result)} chars)"

    print(f"\n  🎉 All assertions passed!")
    print(f"{'█' * 70}\n")


if __name__ == "__main__":
    asyncio.run(test_qa_via_api())
