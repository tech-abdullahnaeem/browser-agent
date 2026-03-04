"""In-memory task state store with optional persistent memory.

Tracks active and completed tasks in a dictionary.  When memory stores are
injected (Phase 5), completed tasks are persisted to SQLite and ChromaDB.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from src.agent.core import BrowserAgentRunner
from src.api.ws import ws_manager
from src.config import Settings, get_settings
from src.models.agent_event import (
    DoneEvent,
    ErrorEvent,
    PlanEvent,
    StatusEvent,
    StepEvent,
)
from src.models.task import StepSummary, TaskRequest, TaskResult, TaskStatus
from src.utils.logging import get_logger

if TYPE_CHECKING:
    from src.memory.sqlite_store import SQLiteStore
    from src.memory.vector_store import VectorStore
    from src.safety.audit import AuditLogger
    from src.safety.domain_filter import DomainFilter
    from src.safety.hitl import HITLGate

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Task state model
# ---------------------------------------------------------------------------

class TaskState(BaseModel):
    """In-memory representation of a running or completed task."""

    task_id: str
    request: TaskRequest
    status: TaskStatus = TaskStatus.PENDING
    steps: list[StepSummary] = Field(default_factory=list)
    result: TaskResult | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# Task Store
# ---------------------------------------------------------------------------

class TaskStore:
    """In-memory store for tasks with optional persistent memory."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskState] = {}
        self._bg_tasks: dict[str, asyncio.Task[Any]] = {}
        self._agent_lock = asyncio.Semaphore(1)  # serialize agent runs
        self._lock = asyncio.Lock()
        # Phase 5 memory stores (injected by main.py)
        self._sqlite: SQLiteStore | None = None
        self._vector: VectorStore | None = None
        # Phase 6 safety (injected by main.py)
        self._hitl_gate: HITLGate | None = None
        self._audit_logger: AuditLogger | None = None
        self._domain_filter: DomainFilter | None = None

    def set_memory_stores(self, sqlite: SQLiteStore, vector: VectorStore) -> None:
        """Inject persistent memory stores (called from main.py lifespan)."""
        self._sqlite = sqlite
        self._vector = vector
        logger.info("task_store_memory_stores_set")

    def set_safety(
        self,
        hitl_gate: HITLGate,
        audit_logger: AuditLogger,
        domain_filter: DomainFilter,
    ) -> None:
        """Inject safety components (called from main.py lifespan)."""
        self._hitl_gate = hitl_gate
        self._audit_logger = audit_logger
        self._domain_filter = domain_filter
        logger.info("task_store_safety_set")

    async def create_task(self, request: TaskRequest, settings: Settings | None = None) -> TaskState:
        """Create a new task, store it, and start the agent in the background."""
        task_id = uuid.uuid4().hex
        state = TaskState(task_id=task_id, request=request)

        async with self._lock:
            self._tasks[task_id] = state

        # Start background execution
        bg = asyncio.create_task(self._execute_task(task_id, settings))
        self._bg_tasks[task_id] = bg
        bg.add_done_callback(lambda _: self._bg_tasks.pop(task_id, None))

        logger.info("task_created", task_id=task_id)
        return state

    async def get_task(self, task_id: str) -> TaskState | None:
        """Return the task state or None if not found."""
        async with self._lock:
            return self._tasks.get(task_id)

    async def list_tasks(self, limit: int = 50, offset: int = 0) -> list[TaskState]:
        """Return all tasks, most recent first."""
        async with self._lock:
            all_tasks = sorted(
                self._tasks.values(),
                key=lambda t: t.created_at,
                reverse=True,
            )
            return all_tasks[offset : offset + limit]

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task.  Returns True if cancelled, False if not found/already done."""
        bg = self._bg_tasks.get(task_id)
        if bg and not bg.done():
            bg.cancel()
            async with self._lock:
                state = self._tasks.get(task_id)
                if state:
                    state.status = TaskStatus.CANCELLED
                    state.updated_at = datetime.now(timezone.utc)

            await ws_manager.broadcast(
                task_id,
                StatusEvent(task_id=task_id, status=TaskStatus.CANCELLED.value),
            )
            logger.info("task_cancelled", task_id=task_id)
            return True
        return False

    async def task_count(self) -> int:
        """Return total number of tasks."""
        async with self._lock:
            return len(self._tasks)

    # -- Background execution ----------------------------------------------

    async def _execute_task(self, task_id: str, settings: Settings | None = None) -> None:
        """Run the agent for a task, updating state and broadcasting events."""
        s = settings or get_settings()

        async with self._lock:
            state = self._tasks.get(task_id)
            if not state:
                return

        # Update status → running
        state.status = TaskStatus.RUNNING
        state.updated_at = datetime.now(timezone.utc)
        await ws_manager.broadcast(
            task_id,
            StatusEvent(task_id=task_id, status=TaskStatus.RUNNING.value),
        )

        # Step callback — streams each step to WebSocket clients
        async def on_step(step: StepSummary) -> None:
            state.steps.append(step)
            state.updated_at = datetime.now(timezone.utc)
            await ws_manager.broadcast(
                task_id,
                StepEvent(task_id=task_id, data=step),
            )

        # Acquire the agent lock (only 1 agent at a time)
        async with self._agent_lock:
            try:
                runner = BrowserAgentRunner(settings=s)
                # Inject vector store for memory-augmented prompts
                if self._vector:
                    runner.set_vector_store(self._vector)
                # Inject safety components (Phase 6)
                if self._hitl_gate or self._audit_logger or self._domain_filter:
                    runner.set_safety(
                        hitl_gate=self._hitl_gate,
                        audit_logger=self._audit_logger,
                        domain_filter=self._domain_filter,
                    )
                result = await runner.run_task(
                    task=state.request.task,
                    context=state.request.context,
                    task_id=task_id,
                    on_step=on_step,
                )

                state.result = result
                state.status = result.status
                state.updated_at = datetime.now(timezone.utc)

                # Persist to SQLite + ChromaDB (Phase 5)
                await self._persist_task_result(state)

                await ws_manager.broadcast(
                    task_id,
                    DoneEvent(task_id=task_id, data=result),
                )

            except asyncio.CancelledError:
                state.status = TaskStatus.CANCELLED
                state.updated_at = datetime.now(timezone.utc)
                await ws_manager.broadcast(
                    task_id,
                    StatusEvent(task_id=task_id, status=TaskStatus.CANCELLED.value),
                )
                logger.info("task_cancelled_during_execution", task_id=task_id)

            except Exception as exc:
                state.status = TaskStatus.FAILED
                state.result = TaskResult(
                    task_id=task_id,
                    task=state.request.task,
                    status=TaskStatus.FAILED,
                    steps=state.steps,
                    error=str(exc),
                    total_steps=len(state.steps),
                    model_used=s.flash_model,
                )
                state.updated_at = datetime.now(timezone.utc)

                await ws_manager.broadcast(
                    task_id,
                    ErrorEvent(task_id=task_id, message=str(exc)),
                )
                logger.error("task_execution_error", task_id=task_id, error=str(exc), exc_info=True)

    # -- persistence (Phase 5) ---------------------------------------------

    async def _persist_task_result(self, state: TaskState) -> None:
        """Save task + steps to SQLite and add to vector memory."""
        if not self._sqlite or not self._vector:
            return  # Memory not configured

        try:
            result = state.result
            result_json = result.model_dump_json() if result else None
            await self._sqlite.save_task(
                task_id=state.task_id,
                task_text=state.request.task,
                status=state.status.value,
                context=state.request.context,
                result_json=result_json,
                duration_seconds=result.duration_seconds if result else None,
            )
            # Save individual steps
            for step in state.steps:
                await self._sqlite.save_step(
                    task_id=state.task_id,
                    step_number=step.step_number,
                    action=step.action,
                    element=step.element,
                    reasoning=step.reasoning,
                    thinking=step.thinking,
                    success=step.success,
                    error=step.error,
                )

            # Add to vector memory for similarity search
            if result and result.final_result:
                # Extract domain from context if available
                domain = ""
                if state.request.context:
                    import re
                    url_match = re.search(r"https?://([^/\s]+)", state.request.context)
                    if url_match:
                        domain = url_match.group(1)

                await self._vector.add_task_memory(
                    task_id=state.task_id,
                    task_text=state.request.task,
                    result_summary=result.final_result[:2000],
                    metadata={
                        "status": state.status.value,
                        "domain": domain,
                        "step_count": len(state.steps),
                        "duration": result.duration_seconds or 0,
                    },
                )

            logger.info("task_persisted_to_memory", task_id=state.task_id)
        except Exception:
            logger.warning("task_persist_failed", task_id=state.task_id, exc_info=True)


# Module-level singleton
task_store = TaskStore()
