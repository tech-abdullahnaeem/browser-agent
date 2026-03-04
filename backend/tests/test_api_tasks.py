"""Tests for REST API task endpoints."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.models.task import TaskRequest, TaskStatus


@pytest.fixture()
async def client():
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
async def clear_task_store():
    """Reset the task store between tests."""
    from src.api.task_store import task_store
    task_store._tasks.clear()
    task_store._bg_tasks.clear()
    yield
    # Cancel any remaining background tasks
    for bg in list(task_store._bg_tasks.values()):
        bg.cancel()
    task_store._tasks.clear()
    task_store._bg_tasks.clear()


class TestHealthCheck:
    async def test_health(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    async def test_root(self, client: AsyncClient) -> None:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Browser Agent API"
        assert "version" in data


class TestCreateTask:
    @patch("src.api.task_store.TaskStore._execute_task", new_callable=AsyncMock)
    async def test_create_task_returns_201(self, mock_exec: AsyncMock, client: AsyncClient) -> None:
        response = await client.post(
            "/api/tasks",
            json={"task": "Go to google.com"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"

    @patch("src.api.task_store.TaskStore._execute_task", new_callable=AsyncMock)
    async def test_create_task_with_context(self, mock_exec: AsyncMock, client: AsyncClient) -> None:
        response = await client.post(
            "/api/tasks",
            json={"task": "Click the buy button", "context": "On amazon.com product page"},
        )
        assert response.status_code == 201

    async def test_create_task_empty_body_rejected(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/tasks",
            json={"task": ""},
        )
        assert response.status_code == 422

    async def test_create_task_missing_task_rejected(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/tasks",
            json={},
        )
        assert response.status_code == 422


class TestListTasks:
    async def test_list_tasks_empty(self, client: AsyncClient) -> None:
        response = await client.get("/api/tasks")
        assert response.status_code == 200
        data = response.json()
        assert data["tasks"] == []
        assert data["total"] == 0

    @patch("src.api.task_store.TaskStore._execute_task", new_callable=AsyncMock)
    async def test_list_tasks_after_create(self, mock_exec: AsyncMock, client: AsyncClient) -> None:
        await client.post("/api/tasks", json={"task": "Task 1"})
        await client.post("/api/tasks", json={"task": "Task 2"})

        response = await client.get("/api/tasks")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["tasks"]) == 2

    @patch("src.api.task_store.TaskStore._execute_task", new_callable=AsyncMock)
    async def test_list_tasks_pagination(self, mock_exec: AsyncMock, client: AsyncClient) -> None:
        for i in range(5):
            await client.post("/api/tasks", json={"task": f"Task {i}"})

        response = await client.get("/api/tasks?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 2
        assert data["total"] == 5


class TestGetTask:
    @patch("src.api.task_store.TaskStore._execute_task", new_callable=AsyncMock)
    async def test_get_task_found(self, mock_exec: AsyncMock, client: AsyncClient) -> None:
        create_resp = await client.post("/api/tasks", json={"task": "Go to example.com"})
        task_id = create_resp.json()["task_id"]

        response = await client.get(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["task"] == "Go to example.com"

    async def test_get_task_not_found(self, client: AsyncClient) -> None:
        response = await client.get("/api/tasks/nonexistent")
        assert response.status_code == 404


class TestCancelTask:
    async def test_cancel_task_not_found(self, client: AsyncClient) -> None:
        response = await client.delete("/api/tasks/nonexistent")
        assert response.status_code == 404

    @patch("src.api.task_store.TaskStore._execute_task", new_callable=AsyncMock)
    async def test_cancel_pending_task(self, mock_exec: AsyncMock, client: AsyncClient) -> None:
        create_resp = await client.post("/api/tasks", json={"task": "Some task"})
        task_id = create_resp.json()["task_id"]

        response = await client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
