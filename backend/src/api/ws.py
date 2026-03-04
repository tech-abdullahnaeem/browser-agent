"""WebSocket connection manager.

Maintains a mapping of ``task_id`` → set of connected WebSocket clients.
Provides methods to broadcast :class:`AgentEvent` instances to all clients
subscribed to a given task.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from src.models.agent_event import AgentEvent
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by task_id."""

    def __init__(self) -> None:
        # task_id → set of active WebSocket connections
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, task_id: str, ws: WebSocket) -> None:
        """Accept and register a WebSocket connection for *task_id*."""
        await ws.accept()
        async with self._lock:
            if task_id not in self._connections:
                self._connections[task_id] = set()
            self._connections[task_id].add(ws)
        logger.debug("ws_client_connected", task_id=task_id)

    async def disconnect(self, task_id: str, ws: WebSocket) -> None:
        """Remove a WebSocket from the *task_id* group."""
        async with self._lock:
            conns = self._connections.get(task_id)
            if conns:
                conns.discard(ws)
                if not conns:
                    del self._connections[task_id]
        logger.debug("ws_client_disconnected", task_id=task_id)

    async def broadcast(self, task_id: str, event: AgentEvent) -> None:
        """Send *event* to all WebSocket clients subscribed to *task_id*.

        Silently removes any clients that have disconnected.
        """
        async with self._lock:
            conns = self._connections.get(task_id)
            if not conns:
                return
            clients = list(conns)

        stale: list[WebSocket] = []
        payload = event.ws_dict()

        for ws in clients:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json(payload)
                else:
                    stale.append(ws)
            except Exception:
                stale.append(ws)

        # Clean up stale connections
        if stale:
            async with self._lock:
                conns = self._connections.get(task_id)
                if conns:
                    for ws in stale:
                        conns.discard(ws)
                    if not conns:
                        del self._connections[task_id]

    async def send_personal(self, ws: WebSocket, event: AgentEvent) -> None:
        """Send an event to a single WebSocket client."""
        try:
            if ws.client_state == WebSocketState.CONNECTED:
                await ws.send_json(event.ws_dict())
        except Exception:
            logger.warning("ws_send_personal_failed", exc_info=True)

    def client_count(self, task_id: str) -> int:
        """Return the number of connected clients for *task_id*."""
        return len(self._connections.get(task_id, set()))

    @property
    def total_connections(self) -> int:
        """Total number of active WebSocket connections across all tasks."""
        return sum(len(v) for v in self._connections.values())


# Module-level singleton
ws_manager = ConnectionManager()
