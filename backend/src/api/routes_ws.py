"""WebSocket endpoint for real-time task streaming.

Clients connect to ``/ws/{task_id}`` to receive live agent events as the
task executes.  If the task is already completed when the client connects,
the full history is replayed and the connection is closed.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.task_store import task_store
from src.api.ws import ws_manager
from src.models.agent_event import DoneEvent, ErrorEvent, StepEvent, StatusEvent
from src.models.task import TaskStatus
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Module-level reference to the HITL gate (injected from main.py)
_hitl_gate = None


def set_hitl_gate(gate) -> None:
    """Inject the HITLGate instance for handling hitl_response messages."""
    global _hitl_gate  # noqa: PLW0603
    _hitl_gate = gate

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(ws: WebSocket, task_id: str) -> None:
    """WebSocket endpoint for streaming task events.

    Behaviour:
    - If the task doesn't exist → send error and close.
    - If the task is already completed → replay full history then close.
    - If the task is pending or running → stream events in real-time.
    """
    state = await task_store.get_task(task_id)

    if not state:
        await ws.accept()
        await ws.send_json(
            ErrorEvent(task_id=task_id, message=f"Task {task_id} not found").ws_dict()
        )
        await ws.close(code=4004, reason="Task not found")
        return

    # Connect and register
    await ws_manager.connect(task_id, ws)

    try:
        # If task is already done, replay history and close
        if state.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            await _replay_history(ws, state)
            return

        # Send current status
        await ws_manager.send_personal(
            ws,
            StatusEvent(task_id=task_id, status=state.status.value),
        )

        # Replay any steps that already happened before we connected
        for step in state.steps:
            await ws_manager.send_personal(
                ws,
                StepEvent(task_id=task_id, data=step),
            )

        # Keep the connection alive, receiving pings/messages from client
        while True:
            try:
                # Wait for client messages (heartbeat pings or close)
                data = await asyncio.wait_for(ws.receive_text(), timeout=60.0)
                # Client can send "ping" to keep alive
                if data == "ping":
                    await ws.send_json({"type": "pong"})
                else:
                    # Try to parse as JSON for hitl_response or other messages
                    try:
                        import json
                        msg = json.loads(data)
                        await _handle_client_message(msg, task_id)
                    except (json.JSONDecodeError, Exception):
                        pass  # Not JSON or unknown message
            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await ws.send_json({"type": "ping"})
                except Exception:
                    break
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.warning("ws_endpoint_error", task_id=task_id, exc_info=True)
    finally:
        await ws_manager.disconnect(task_id, ws)


async def _replay_history(ws: WebSocket, state: object) -> None:
    """Send the full task history to a late-connecting client, then close."""
    from src.api.task_store import TaskState

    if not isinstance(state, TaskState):
        return

    # Send status
    await ws_manager.send_personal(
        ws,
        StatusEvent(task_id=state.task_id, status=state.status.value),
    )

    # Replay all steps
    for step in state.steps:
        await ws_manager.send_personal(
            ws,
            StepEvent(task_id=state.task_id, data=step),
        )

    # Send done event with result
    if state.result:
        await ws_manager.send_personal(
            ws,
            DoneEvent(task_id=state.task_id, data=state.result),
        )

    await ws.close(code=1000, reason="Task already completed — history replayed")


async def _handle_client_message(msg: dict, task_id: str) -> None:
    """Route incoming client messages (e.g. hitl_response) to the right handler."""
    msg_type = msg.get("type")

    if msg_type == "hitl_response":
        data = msg.get("data", {})
        action_id = data.get("action_id")
        approved = data.get("approved", False)
        if action_id and _hitl_gate:
            resolved = _hitl_gate.resolve_confirmation(action_id, approved)
            logger.info(
                "hitl_response_received",
                task_id=task_id,
                action_id=action_id,
                approved=approved,
                resolved=resolved,
            )
        else:
            logger.warning(
                "hitl_response_no_gate_or_id",
                task_id=task_id,
                action_id=action_id,
            )
