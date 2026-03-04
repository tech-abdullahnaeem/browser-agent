"""Pydantic models for task requests, results, and step summaries."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class TaskStatus(str, enum.Enum):
    """Lifecycle status of a task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskRequest(BaseModel):
    """Payload sent by a client to create a new task."""

    task: str = Field(min_length=1, max_length=2000, description="Natural-language instruction")
    context: str | None = Field(
        default=None,
        max_length=5000,
        description="Optional page context from the extension (URL, visible text, etc.)",
    )


class StepSummary(BaseModel):
    """Summary of a single agent step, suitable for streaming to clients."""

    step_number: int
    action: str = Field(description="High-level action description (e.g. 'click', 'type', 'navigate')")
    element: str | None = Field(default=None, description="Target element description or selector")
    reasoning: str | None = Field(default=None, description="LLM's reasoning / next_goal for this step")
    thinking: str | None = Field(default=None, description="LLM's internal thinking for this step")
    success: bool | None = Field(default=None, description="Whether the step succeeded")
    error: str | None = Field(default=None, description="Error message if the step failed")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TaskResult(BaseModel):
    """Final result of a completed (or failed) task."""

    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    task: str
    status: TaskStatus
    steps: list[StepSummary] = Field(default_factory=list)
    final_result: str | None = Field(default=None, description="Agent's final textual answer / summary")
    error: str | None = Field(default=None, description="Top-level error message if the task failed")
    duration_seconds: float | None = Field(default=None, ge=0.0)
    total_steps: int = Field(default=0, ge=0)
    model_used: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
