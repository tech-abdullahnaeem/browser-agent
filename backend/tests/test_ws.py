"""Tests for WebSocket streaming and the ConnectionManager."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from src.api.ws import ConnectionManager
from src.main import app
from src.models.agent_event import (
    AgentEvent,
    DoneEvent,
    ErrorEvent,
    StatusEvent,
    StepEvent,
)
from src.models.task import StepSummary, TaskResult, TaskStatus


class TestAgentEventModels:
    """Test the Pydantic event models serialize correctly."""

    def test_status_event(self) -> None:
        event = StatusEvent(task_id="abc123", status="running")
        data = event.ws_dict()
        assert data["type"] == "status"
        assert data["task_id"] == "abc123"
        assert data["status"] == "running"
        assert "timestamp" in data

    def test_step_event(self) -> None:
        step = StepSummary(step_number=1, action="click", success=True)
        event = StepEvent(task_id="abc123", data=step)
        data = event.ws_dict()
        assert data["type"] == "step"
        assert data["data"]["step_number"] == 1
        assert data["data"]["action"] == "click"

    def test_error_event(self) -> None:
        event = ErrorEvent(task_id="abc123", message="Something went wrong")
        data = event.ws_dict()
        assert data["type"] == "error"
        assert data["message"] == "Something went wrong"

    def test_done_event(self) -> None:
        result = TaskResult(
            task_id="abc123",
            task="test task",
            status=TaskStatus.COMPLETED,
            final_result="done",
        )
        event = DoneEvent(task_id="abc123", data=result)
        data = event.ws_dict()
        assert data["type"] == "done"
        assert data["data"]["final_result"] == "done"


class TestConnectionManager:
    """Test the WebSocket connection manager."""

    def test_initial_state(self) -> None:
        mgr = ConnectionManager()
        assert mgr.total_connections == 0
        assert mgr.client_count("any") == 0

    async def test_connect_and_count(self) -> None:
        mgr = ConnectionManager()
        fake_ws = AsyncMock()
        fake_ws.client_state = "connected"

        await mgr.connect("task1", fake_ws)
        assert mgr.client_count("task1") == 1
        assert mgr.total_connections == 1

    async def test_disconnect(self) -> None:
        mgr = ConnectionManager()
        fake_ws = AsyncMock()

        await mgr.connect("task1", fake_ws)
        assert mgr.client_count("task1") == 1

        await mgr.disconnect("task1", fake_ws)
        assert mgr.client_count("task1") == 0
        assert mgr.total_connections == 0

    async def test_disconnect_nonexistent(self) -> None:
        """Disconnecting from a non-existent task should not raise."""
        mgr = ConnectionManager()
        fake_ws = AsyncMock()
        await mgr.disconnect("nonexistent", fake_ws)  # Should not raise

    async def test_multiple_clients(self) -> None:
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await mgr.connect("task1", ws1)
        await mgr.connect("task1", ws2)
        assert mgr.client_count("task1") == 2

        await mgr.disconnect("task1", ws1)
        assert mgr.client_count("task1") == 1

    async def test_broadcast_no_clients(self) -> None:
        """Broadcasting to a task with no clients should not raise."""
        mgr = ConnectionManager()
        event = StatusEvent(task_id="task1", status="running")
        await mgr.broadcast("task1", event)  # Should not raise


class TestConfigAPI:
    """Test the config REST API endpoints."""

    @pytest.fixture()
    async def client(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    async def test_get_config(self, client: AsyncClient) -> None:
        response = await client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "max_steps" in data
        assert "use_vision" in data
        assert "headless" in data
        assert "enable_planning" in data

    async def test_update_config(self, client: AsyncClient) -> None:
        response = await client.put(
            "/api/config",
            json={"max_steps": 20, "headless": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["max_steps"] == 20
        assert data["headless"] is True

    async def test_update_config_partial(self, client: AsyncClient) -> None:
        """Only provided fields should be updated."""
        # Set an initial value
        await client.put("/api/config", json={"max_steps": 30})

        # Update a different field — max_steps should remain
        response = await client.put("/api/config", json={"use_vision": False})
        data = response.json()
        assert data["use_vision"] is False
        # max_steps should still reflect the override
        assert data["max_steps"] == 30

    async def test_update_config_invalid(self, client: AsyncClient) -> None:
        response = await client.put(
            "/api/config",
            json={"max_steps": -1},
        )
        assert response.status_code == 422


class TestWebSocketEndpoint:
    """Integration tests for the WebSocket endpoint using starlette TestClient."""

    @pytest.fixture(autouse=True)
    async def clear_store(self):
        from src.api.task_store import task_store
        task_store._tasks.clear()
        task_store._bg_tasks.clear()
        yield
        for bg in list(task_store._bg_tasks.values()):
            bg.cancel()
        task_store._tasks.clear()
        task_store._bg_tasks.clear()

    def test_ws_nonexistent_task(self) -> None:
        """Connecting to a non-existent task should return an error event."""
        sync_client = TestClient(app)
        with sync_client.websocket_connect("/ws/nonexistent") as ws:
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "not found" in data["message"].lower()

    @patch("src.api.task_store.TaskStore._execute_task", new_callable=AsyncMock)
    def test_ws_connect_to_pending_task(self, mock_exec: AsyncMock) -> None:
        """Connecting to a pending task should receive a status event."""
        sync_client = TestClient(app)

        # Create a task first via REST
        response = sync_client.post("/api/tasks", json={"task": "Test task"})
        assert response.status_code == 201
        task_id = response.json()["task_id"]

        with sync_client.websocket_connect(f"/ws/{task_id}") as ws:
            data = ws.receive_json()
            assert data["type"] == "status"
            assert data["task_id"] == task_id
