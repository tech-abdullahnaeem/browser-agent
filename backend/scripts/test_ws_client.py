"""WebSocket client test script for Phase 2 verification.

Usage:
    python scripts/test_ws_client.py <task_id>
    python scripts/test_ws_client.py  # submits a new task automatically
"""

import asyncio
import json
import sys

import httpx
import websockets


API_BASE = "http://localhost:8000"
WS_BASE = "ws://localhost:8000"


async def submit_task(task: str = "Go to google.com and tell me the title of the page") -> str:
    """Submit a task via REST and return the task_id."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/api/tasks",
            json={"task": task},
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"Task submitted: {data['task_id']} (status: {data['status']})")
        return data["task_id"]


async def stream_events(task_id: str) -> None:
    """Connect to the WebSocket and print events until done."""
    uri = f"{WS_BASE}/ws/{task_id}"
    print(f"Connecting to {uri}...")

    async with websockets.connect(uri) as ws:
        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=180)
                data = json.loads(msg)
                event_type = data.get("type", "?")

                if event_type == "status":
                    print(f"  [{event_type}] {data['status']}")
                elif event_type == "step":
                    step = data["data"]
                    print(
                        f"  [step {step['step_number']}] "
                        f"{step['action']} — success={step.get('success')}"
                    )
                elif event_type == "done":
                    result = data["data"]
                    print(f"  [done] status={result['status']}")
                    print(f"         result={result.get('final_result', 'N/A')}")
                    print(f"         steps={result.get('total_steps', 0)}")
                    print(f"         duration={result.get('duration_seconds', 0)}s")
                    break
                elif event_type == "error":
                    print(f"  [error] {data['message']}")
                    break
                elif event_type == "pong":
                    pass
                else:
                    print(f"  [{event_type}] {json.dumps(data)[:120]}")
        except asyncio.TimeoutError:
            print("  (timeout — no events for 180s)")
        except websockets.ConnectionClosed as e:
            print(f"  (connection closed: code={e.code} reason={e.reason})")


async def verify_task_detail(task_id: str) -> None:
    """Fetch the task detail via REST and print it."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/api/tasks/{task_id}")
        resp.raise_for_status()
        data = resp.json()
        print(f"\n=== Task Detail (GET /api/tasks/{task_id}) ===")
        print(f"  Status: {data['status']}")
        print(f"  Steps: {data['total_steps']}")
        print(f"  Result: {data.get('final_result', 'N/A')}")
        print(f"  Duration: {data.get('duration_seconds', 0)}s")


async def main() -> None:
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
    else:
        task_id = await submit_task()

    await stream_events(task_id)
    await verify_task_detail(task_id)


if __name__ == "__main__":
    asyncio.run(main())
