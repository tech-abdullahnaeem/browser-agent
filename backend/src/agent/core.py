"""BrowserAgentRunner — central orchestration layer.

Creates browser-use Agent instances, manages browser sessions, handles
multi-model routing (Flash for execution, Pro for planning), and converts
browser-use's AgentHistoryList into our TaskResult model.
"""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

import structlog

from browser_use import Agent, BrowserSession
from browser_use.agent.views import AgentHistory, AgentHistoryList, AgentOutput

from src.agent.llm import get_flash_llm, get_pro_llm
from src.agent.planner import build_planned_task, generate_plan, is_complex_task
from src.agent.prompts import MEMORY_INJECTION_TEMPLATE, SYSTEM_PROMPT_EXTENSION
from src.agent.tools import custom_tools
from src.config import Settings, get_settings
from src.models.task import StepSummary, TaskResult, TaskStatus
from src.utils.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from src.memory.vector_store import VectorStore
    from src.safety.audit import AuditLogger
    from src.safety.domain_filter import DomainFilter
    from src.safety.hitl import HITLGate

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper: convert a single AgentHistory entry into our StepSummary
# ---------------------------------------------------------------------------

def _history_entry_to_step(step_number: int, entry: AgentHistory) -> StepSummary:
    """Map a browser-use AgentHistory record to our StepSummary model."""
    output: AgentOutput | None = entry.model_output

    # Derive action description from model output
    action_desc = "unknown"
    element_desc: str | None = None
    reasoning: str | None = None
    thinking: str | None = None
    success: bool | None = None
    error: str | None = None

    if output:
        reasoning = output.next_goal
        thinking = output.thinking

        # Summarise actions taken in this step
        if output.action:
            action_names = []
            for act in output.action:
                # ActionModel stores the action as a dict with a single key
                act_dict = act.model_dump(exclude_unset=True, exclude_none=True)
                for action_name, params in act_dict.items():
                    action_names.append(action_name)
                    # Try to extract an element/text hint from params
                    if isinstance(params, dict):
                        element_desc = (
                            params.get("text")
                            or params.get("query")
                            or params.get("url")
                            or params.get("index")
                            or element_desc
                        )
                        if element_desc is not None:
                            element_desc = str(element_desc)[:200]
            action_desc = ", ".join(action_names) if action_names else "unknown"

    # Result status from ActionResult list
    if entry.result:
        errors = [r.error for r in entry.result if r.error]
        if errors:
            error = "; ".join(errors)
            success = False
        else:
            success = True

    return StepSummary(
        step_number=step_number,
        action=action_desc,
        element=element_desc,
        reasoning=reasoning,
        thinking=thinking,
        success=success,
        error=error,
    )


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

class BrowserAgentRunner:
    """High-level wrapper that creates and runs a browser-use Agent for a task.

    Usage::

        runner = BrowserAgentRunner()
        result = await runner.run_task("Search Google for 'hello world'")
        print(result.model_dump_json(indent=2))
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._vector_store: VectorStore | None = None
        # Safety (Phase 6)
        self._hitl_gate: HITLGate | None = None
        self._audit_logger: AuditLogger | None = None
        self._domain_filter: DomainFilter | None = None

    def set_vector_store(self, store: VectorStore) -> None:
        """Inject the vector store for memory-augmented prompts."""
        self._vector_store = store

    def set_safety(
        self,
        hitl_gate: HITLGate | None = None,
        audit_logger: AuditLogger | None = None,
        domain_filter: DomainFilter | None = None,
    ) -> None:
        """Inject safety components for HITL, auditing, and domain filtering."""
        self._hitl_gate = hitl_gate
        self._audit_logger = audit_logger
        self._domain_filter = domain_filter

    # -- public API --------------------------------------------------------

    async def run_task(
        self,
        task: str,
        context: str | None = None,
        task_id: str | None = None,
        on_step: Callable[[StepSummary], Awaitable[None] | None] | None = None,
    ) -> TaskResult:
        """Execute *task* in a real browser and return a :class:`TaskResult`.

        Parameters
        ----------
        task:
            Natural-language instruction.
        context:
            Optional page context (URL, visible text) from the extension.
        task_id:
            Optional pre-assigned task ID (generated if not provided).
        on_step:
            Optional callback invoked after each agent step with a StepSummary.
            Used by Phase 2 to stream events over WebSocket.
        """
        task_id = task_id or uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(task_id=task_id)
        logger.info("task_start", task_preview=task[:120])

        s = self.settings
        start_time = time.monotonic()

        # -- Inject context if provided ------------------------------------
        effective_task = task
        if context:
            effective_task = f"{context}\n\n{task}"

        # -- Inject memory from similar past tasks --------------------------
        memory_extension = ""
        if self._vector_store and s.enable_memory and s.memory_similar_tasks > 0:
            try:
                similar = await self._vector_store.search_similar(
                    query=task,
                    n=s.memory_similar_tasks,
                    min_score=s.memory_min_similarity,
                )
                if similar:
                    summaries = "\n".join(
                        f"- {m['document'][:300]}" for m in similar
                    )
                    memory_extension = MEMORY_INJECTION_TEMPLATE.format(
                        memory_summaries=summaries
                    )
                    logger.info(
                        "memory_injected",
                        similar_tasks=len(similar),
                        top_score=similar[0]["score"],
                    )
            except Exception:
                logger.warning("memory_search_failed", exc_info=True)

        # -- Planning (multi-model routing) --------------------------------
        if s.enable_planning and is_complex_task(effective_task, s):
            logger.info("task_is_complex_planning_with_pro")
            try:
                plan = await generate_plan(task, context=context, settings=s)
                effective_task = build_planned_task(task, plan)
            except Exception:
                logger.warning("planning_failed_falling_back_to_direct_execution", exc_info=True)

        # -- Build browser session -----------------------------------------
        session = BrowserSession(
            headless=s.headless,
            user_data_dir=s.browser_user_data_dir,
            wait_between_actions=s.wait_between_actions,
        )

        # -- Step tracking -------------------------------------------------
        steps: list[StepSummary] = []
        step_counter = 0

        async def _on_step_end(agent_instance: Agent) -> None:
            """Callback fired after each agent step to collect step data."""
            nonlocal step_counter
            history_list: AgentHistoryList = agent_instance.history
            if not history_list.history:
                return

            latest = history_list.history[-1]
            step_counter += 1
            summary = _history_entry_to_step(step_counter, latest)
            steps.append(summary)
            logger.info(
                "step_completed",
                step=step_counter,
                action=summary.action,
                success=summary.success,
            )
            if on_step:
                result = on_step(summary)
                if result is not None:
                    await result

        # -- Safety watchdog (Phase 6) ------------------------------------
        safety_watchdog = None
        if s.enable_safety and (self._hitl_gate or self._audit_logger or self._domain_filter):
            from src.agent.watchdog import SafetyWatchdog

            safety_watchdog = SafetyWatchdog(
                task_id=task_id,
                hitl_gate=self._hitl_gate,
                audit_logger=self._audit_logger,
                domain_filter=self._domain_filter,
                model_used=s.flash_model,
            )

        # -- Create and run the agent --------------------------------------
        flash_llm = get_flash_llm(s)

        # Combine base system prompt with optional memory injection
        system_extension = SYSTEM_PROMPT_EXTENSION
        if memory_extension:
            system_extension = f"{SYSTEM_PROMPT_EXTENSION}\n\n{memory_extension}"

        agent = Agent(
            task=effective_task,
            llm=flash_llm,
            browser_session=session,
            tools=custom_tools,
            use_vision=s.use_vision,
            max_failures=s.max_failures,
            max_actions_per_step=s.max_actions_per_step,
            extend_system_message=system_extension,
            enable_planning=s.enable_planning,
            register_new_step_callback=safety_watchdog.on_step if safety_watchdog else None,
        )

        status = TaskStatus.RUNNING
        final_result_text: str | None = None
        error_text: str | None = None

        try:
            history: AgentHistoryList = await agent.run(
                max_steps=s.max_steps,
                on_step_end=_on_step_end,
            )

            # -- Determine outcome -----------------------------------------
            if history.is_done():
                status = TaskStatus.COMPLETED
                final_result_text = history.final_result()
            else:
                status = TaskStatus.FAILED
                error_text = "Agent did not complete within max_steps"

            if history.has_errors():
                errors = history.errors()
                if errors and not history.is_done():
                    error_text = "; ".join(str(e) for e in errors[-3:])  # last 3 errors
                    status = TaskStatus.FAILED

        except Exception as exc:
            logger.error("agent_execution_error", error=str(exc), exc_info=True)
            status = TaskStatus.FAILED
            error_text = str(exc)

        finally:
            # Always close the browser session
            try:
                await session.stop()
            except Exception:
                logger.warning("browser_session_close_error", exc_info=True)
            structlog.contextvars.unbind_contextvars("task_id")

        duration = time.monotonic() - start_time
        logger.info(
            "task_finished",
            status=status.value,
            steps=len(steps),
            duration_s=round(duration, 2),
        )

        return TaskResult(
            task_id=task_id,
            task=task,
            status=status,
            steps=steps,
            final_result=final_result_text,
            error=error_text,
            duration_seconds=round(duration, 2),
            total_steps=len(steps),
            model_used=s.flash_model,
        )
