"""Safety watchdog — integrates HITL gate, audit logger, and domain filter
into the browser-use Agent via its callback hooks.

The watchdog is instantiated per-task and plugs into:
- ``register_new_step_callback``  → checks each action before it executes
- ``register_external_agent_status_raise_error_callback`` → can force-stop

Because browser-use's ``register_new_step_callback`` fires **after** a
step completes (with the browser state + agent output for that step), we
use it to audit what just happened and pre-check the *next* planned
actions.  If a planned action is destructive, we request HITL confirmation
before the agent loop continues.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.utils.logging import get_logger

if TYPE_CHECKING:
    from browser_use.agent.views import AgentOutput
    from browser_use.browser.views import BrowserStateSummary

    from src.safety.audit import AuditLogger
    from src.safety.domain_filter import DomainFilter
    from src.safety.hitl import HITLGate

logger = get_logger(__name__)


class SafetyWatchdog:
    """Per-task safety watchdog that hooks into the browser-use Agent.

    Usage::

        wd = SafetyWatchdog(task_id, hitl_gate, audit_logger, domain_filter)
        agent = Agent(
            ...,
            register_new_step_callback=wd.on_step,
        )
    """

    def __init__(
        self,
        task_id: str,
        hitl_gate: HITLGate | None = None,
        audit_logger: AuditLogger | None = None,
        domain_filter: DomainFilter | None = None,
        model_used: str | None = None,
    ) -> None:
        self._task_id = task_id
        self._hitl = hitl_gate
        self._audit = audit_logger
        self._domain_filter = domain_filter
        self._model_used = model_used
        self._blocked_this_step = False

    # -- Agent hook --------------------------------------------------------

    async def on_step(
        self,
        browser_state: BrowserStateSummary,
        agent_output: AgentOutput,
        step_number: int,
    ) -> None:
        """Called by browser-use after each step completes.

        1. Audit the actions that were just taken.
        2. Check the *planned next actions* for destructive patterns.
        3. If destructive → request HITL confirmation; deny → flag for block.
        4. Check domain filter on current URL.
        """
        url = browser_state.url or ""
        self._blocked_this_step = False

        # ── 1. Audit the action that just happened ──
        actions_taken = self._extract_action_info(agent_output)
        for action_info in actions_taken:
            action_type = action_info.get("type", "unknown")
            element_text = action_info.get("element", "")
            reasoning = agent_output.next_goal if agent_output else None

            is_destructive = False
            user_confirmed: bool | None = None
            was_blocked = False

            # ── 2. Check HITL gate ──
            if self._hitl and self._hitl.requires_confirmation(
                action_type=action_type,
                url=url,
                element_text=element_text,
            ):
                is_destructive = True
                description = (
                    f"Action: {action_type}"
                    + (f" on '{element_text}'" if element_text else "")
                    + (f" | URL: {url}" if url else "")
                )
                approved = await self._hitl.request_confirmation(
                    task_id=self._task_id,
                    action_description=description,
                    url=url,
                    element_text=element_text,
                )
                user_confirmed = approved
                if not approved:
                    was_blocked = True
                    self._blocked_this_step = True
                    logger.warning(
                        "safety_action_blocked",
                        task_id=self._task_id,
                        action=action_type,
                        element=element_text,
                    )

            # ── 3. Check domain filter ──
            if self._domain_filter and action_type in ("navigate", "search"):
                nav_url = action_info.get("url", url)
                if not self._domain_filter.is_allowed(nav_url):
                    was_blocked = True
                    self._blocked_this_step = True
                    logger.warning(
                        "safety_domain_blocked",
                        task_id=self._task_id,
                        url=nav_url,
                    )

            # ── 4. Log to audit ──
            if self._audit:
                try:
                    await self._audit.log_action(
                        task_id=self._task_id,
                        action_type=action_type,
                        target_element=element_text,
                        url=url,
                        was_destructive=is_destructive,
                        user_confirmed=user_confirmed,
                        was_blocked=was_blocked,
                        model_used=self._model_used,
                        reasoning=reasoning,
                    )
                except Exception:
                    logger.warning("audit_log_failed", exc_info=True)

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _extract_action_info(agent_output: AgentOutput | None) -> list[dict[str, Any]]:
        """Extract action type + target from AgentOutput.action list."""
        if not agent_output or not agent_output.action:
            return [{"type": "unknown"}]

        actions: list[dict[str, Any]] = []
        for act in agent_output.action:
            act_dict = act.model_dump(exclude_unset=True, exclude_none=True)
            for action_name, params in act_dict.items():
                info: dict[str, Any] = {"type": action_name}
                if isinstance(params, dict):
                    info["element"] = (
                        params.get("text")
                        or params.get("query")
                        or params.get("label")
                        or ""
                    )
                    info["url"] = params.get("url", "")
                    info["index"] = params.get("index")
                actions.append(info)

        return actions or [{"type": "unknown"}]

    @property
    def was_blocked(self) -> bool:
        """Whether the most recent step had a blocked action."""
        return self._blocked_this_step
