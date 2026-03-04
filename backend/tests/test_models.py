"""Tests for src.models.task — Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models.task import StepSummary, TaskRequest, TaskResult, TaskStatus


class TestTaskRequest:
    def test_valid_request(self) -> None:
        req = TaskRequest(task="Go to google.com")
        assert req.task == "Go to google.com"
        assert req.context is None

    def test_with_context(self) -> None:
        req = TaskRequest(task="Click the buy button", context="URL: https://amazon.com")
        assert req.context is not None

    def test_empty_task_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TaskRequest(task="")

    def test_task_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TaskRequest(task="x" * 2001)


class TestTaskStatus:
    def test_enum_values(self) -> None:
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"


class TestStepSummary:
    def test_minimal_step(self) -> None:
        step = StepSummary(step_number=1, action="click")
        assert step.step_number == 1
        assert step.element is None

    def test_full_step(self) -> None:
        step = StepSummary(
            step_number=3,
            action="type",
            element="Search input",
            reasoning="Need to type the query",
            success=True,
        )
        assert step.success is True
        assert step.reasoning is not None


class TestTaskResult:
    def test_auto_generates_id(self) -> None:
        r1 = TaskResult(task="test", status=TaskStatus.COMPLETED)
        r2 = TaskResult(task="test", status=TaskStatus.COMPLETED)
        assert r1.task_id != r2.task_id

    def test_serialization(self) -> None:
        result = TaskResult(
            task="Go to google.com",
            status=TaskStatus.COMPLETED,
            final_result="Navigated to google.com successfully",
            duration_seconds=12.5,
            total_steps=3,
        )
        data = result.model_dump()
        assert data["status"] == "completed"
        assert data["duration_seconds"] == 12.5

    def test_json_roundtrip(self) -> None:
        result = TaskResult(
            task="test task",
            status=TaskStatus.FAILED,
            error="Something went wrong",
        )
        json_str = result.model_dump_json()
        restored = TaskResult.model_validate_json(json_str)
        assert restored.task == result.task
        assert restored.error == result.error
