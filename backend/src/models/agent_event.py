"""Pydantic models for WebSocket streaming events.

Each event sent over the WebSocket has a ``type`` discriminator and a ``data``
payload.  Clients can switch on ``type`` to handle each event differently.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.models.task import StepSummary, TaskResult


# ---------------------------------------------------------------------------
# Base event
# ---------------------------------------------------------------------------

class AgentEvent(BaseModel):
    """Base WebSocket event.  All events have a ``type`` and ``timestamp``."""

    type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def ws_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict suitable for ``ws.send_json``."""
        return self.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Concrete event types
# ---------------------------------------------------------------------------

class StatusEvent(AgentEvent):
    """Emitted when the task status changes (e.g. pending → running → done)."""

    type: Literal["status"] = "status"
    task_id: str
    status: str


class StepEvent(AgentEvent):
    """Emitted after each agent step completes."""

    type: Literal["step"] = "step"
    task_id: str
    data: StepSummary


class PlanEvent(AgentEvent):
    """Emitted when the Pro model generates a plan for a complex task."""

    type: Literal["plan"] = "plan"
    task_id: str
    plan: str


class ScreenshotEvent(AgentEvent):
    """Emitted when a screenshot is captured."""

    type: Literal["screenshot"] = "screenshot"
    task_id: str
    b64: str  # base64-encoded PNG


class DoneEvent(AgentEvent):
    """Emitted when the task finishes (success or failure)."""

    type: Literal["done"] = "done"
    task_id: str
    data: TaskResult


class ErrorEvent(AgentEvent):
    """Emitted when an unrecoverable error occurs."""

    type: Literal["error"] = "error"
    task_id: str
    message: str


class HighlightEvent(AgentEvent):
    """Emitted when the agent wants to visually highlight an element on the page.

    Used by the QA testing agent to point out issues (broken images,
    accessibility violations, etc.) in the extension overlay.
    """

    type: Literal["highlight"] = "highlight"
    task_id: str
    selector: str
    label: str | None = None
    action: str | None = None  # "click" | "type" | "inspect" | "error" | "warning" | "info"
    duration: int | None = None  # ms, 0 = indefinite


class HITLRequestEvent(AgentEvent):
    """Emitted when the safety watchdog needs user confirmation for a destructive action."""

    type: Literal["hitl_request"] = "hitl_request"
    task_id: str
    action_id: str
    action_description: str
    url: str = ""
    element_text: str = ""
    timeout_seconds: int = 60
