"""REST API routes for task management.

- ``POST   /api/tasks``         — submit a new task
- ``GET    /api/tasks``         — list all tasks
- ``GET    /api/tasks/{id}``    — get a single task detail
- ``DELETE /api/tasks/{id}``    — cancel a running task
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.api.task_store import task_store
from src.models.task import TaskRequest, TaskStatus

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class TaskCreatedResponse(BaseModel):
    """Returned when a new task is submitted."""
    task_id: str
    status: str


class TaskSummaryResponse(BaseModel):
    """Brief summary for task listing."""
    task_id: str
    task: str
    status: TaskStatus
    total_steps: int = 0
    final_result: str | None = None
    error: str | None = None
    created_at: str
    duration_seconds: float | None = None


class TaskDetailResponse(BaseModel):
    """Full task detail including step history."""
    task_id: str
    task: str
    status: TaskStatus
    steps: list[dict] = Field(default_factory=list)
    final_result: str | None = None
    error: str | None = None
    created_at: str
    updated_at: str
    duration_seconds: float | None = None
    total_steps: int = 0
    model_used: str | None = None


class TaskListResponse(BaseModel):
    """Response for task listing."""
    tasks: list[TaskSummaryResponse]
    total: int


class CancelResponse(BaseModel):
    """Response for task cancellation."""
    task_id: str
    cancelled: bool
    message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=TaskCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new task",
)
async def create_task(request: TaskRequest) -> TaskCreatedResponse:
    """Accept a task request, queue it for execution, and return the task ID."""
    state = await task_store.create_task(request)
    return TaskCreatedResponse(
        task_id=state.task_id,
        status=state.status.value,
    )


@router.get(
    "",
    response_model=TaskListResponse,
    summary="List all tasks",
)
async def list_tasks(limit: int = 50, offset: int = 0) -> TaskListResponse:
    """Return all tasks, most recent first."""
    tasks = await task_store.list_tasks(limit=limit, offset=offset)
    total = await task_store.task_count()

    summaries = []
    for t in tasks:
        result = t.result
        summaries.append(
            TaskSummaryResponse(
                task_id=t.task_id,
                task=t.request.task,
                status=t.status,
                total_steps=len(t.steps),
                final_result=result.final_result if result else None,
                error=result.error if result else None,
                created_at=t.created_at.isoformat(),
                duration_seconds=result.duration_seconds if result else None,
            )
        )

    return TaskListResponse(tasks=summaries, total=total)


@router.get(
    "/{task_id}",
    response_model=TaskDetailResponse,
    summary="Get task detail",
)
async def get_task(task_id: str) -> TaskDetailResponse:
    """Return full task detail including step-by-step history."""
    state = await task_store.get_task(task_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    result = state.result
    steps_data = [s.model_dump(mode="json") for s in state.steps]

    return TaskDetailResponse(
        task_id=state.task_id,
        task=state.request.task,
        status=state.status,
        steps=steps_data,
        final_result=result.final_result if result else None,
        error=result.error if result else None,
        created_at=state.created_at.isoformat(),
        updated_at=state.updated_at.isoformat(),
        duration_seconds=result.duration_seconds if result else None,
        total_steps=len(state.steps),
        model_used=result.model_used if result else None,
    )


@router.delete(
    "/{task_id}",
    response_model=CancelResponse,
    summary="Cancel a running task",
)
async def cancel_task(task_id: str) -> CancelResponse:
    """Attempt to cancel a running task."""
    state = await task_store.get_task(task_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    cancelled = await task_store.cancel_task(task_id)
    if cancelled:
        return CancelResponse(
            task_id=task_id,
            cancelled=True,
            message="Task cancellation requested",
        )
    return CancelResponse(
        task_id=task_id,
        cancelled=False,
        message=f"Task cannot be cancelled (status: {state.status.value})",
    )
