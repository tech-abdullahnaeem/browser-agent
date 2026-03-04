"""Human-in-the-Loop (HITL) gate for destructive action confirmation.

The gate checks action element text and page URLs against configurable
patterns.  When a match is found, it emits a WebSocket event asking the
user for confirmation and **blocks** the agent until a response or timeout.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from typing import Any

from src.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Default destructive-action patterns
# ---------------------------------------------------------------------------

DESTRUCTIVE_KEYWORDS: list[str] = [
    "buy", "purchase", "order", "checkout", "pay",
    "delete", "remove", "unsubscribe", "cancel subscription",
    "submit payment", "confirm order", "place order",
    "send money", "transfer funds", "withdraw",
    "sign contract", "agree to terms",
]

DESTRUCTIVE_URL_PATTERNS: list[str] = [
    r"checkout", r"payment", r"billing",
    r"order/confirm", r"cart/checkout",
]


class HITLGate:
    """Gate that pauses the agent for user confirmation on destructive actions.

    Usage::

        gate = HITLGate(timeout=60, broadcast_fn=ws_manager.broadcast)
        if gate.requires_confirmation(action, url, element_text):
            approved = await gate.request_confirmation(task_id, description)
    """

    def __init__(
        self,
        timeout: int = 60,
        broadcast_fn: Any | None = None,
        keywords: list[str] | None = None,
        url_patterns: list[str] | None = None,
    ) -> None:
        self._timeout = timeout
        self._broadcast_fn = broadcast_fn
        self._keywords = [k.lower() for k in (keywords or DESTRUCTIVE_KEYWORDS)]
        self._url_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in (url_patterns or DESTRUCTIVE_URL_PATTERNS)
        ]
        # Auto-approved domains (whitelist)
        self._auto_approve_domains: set[str] = set()

        # Pending confirmation requests: action_id → asyncio.Event
        self._pending: dict[str, asyncio.Event] = {}
        # Responses: action_id → bool (approved)
        self._responses: dict[str, bool] = {}

    # -- pattern matching --------------------------------------------------

    def requires_confirmation(
        self,
        action_type: str | None = None,
        url: str | None = None,
        element_text: str | None = None,
    ) -> bool:
        """Return True if the action matches a destructive pattern."""
        # Check auto-approve domains
        if url and self._auto_approve_domains:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lower()
            if domain in self._auto_approve_domains:
                return False

        # Check element text against keywords
        if element_text:
            text_lower = element_text.lower()
            for keyword in self._keywords:
                if keyword in text_lower:
                    logger.info(
                        "hitl_keyword_match",
                        keyword=keyword,
                        element_text=element_text[:100],
                    )
                    return True

        # Check URL against patterns
        if url:
            for pattern in self._url_patterns:
                if pattern.search(url):
                    logger.info("hitl_url_match", pattern=pattern.pattern, url=url)
                    return True

        return False

    # -- confirmation request / response -----------------------------------

    async def request_confirmation(
        self,
        task_id: str,
        action_description: str,
        url: str | None = None,
        element_text: str | None = None,
    ) -> bool:
        """Emit a confirmation request via WebSocket and wait for response.

        Returns True if the user approves, False on deny or timeout.
        """
        action_id = uuid.uuid4().hex
        event = asyncio.Event()
        self._pending[action_id] = event

        # Send HITL request to connected clients
        if self._broadcast_fn:
            from src.models.agent_event import HITLRequestEvent

            hitl_event = HITLRequestEvent(
                task_id=task_id,
                action_id=action_id,
                action_description=action_description,
                url=url or "",
                element_text=element_text or "",
                timeout_seconds=self._timeout,
            )
            try:
                await self._broadcast_fn(task_id, hitl_event)
            except Exception:
                logger.warning("hitl_broadcast_failed", exc_info=True)

        logger.info(
            "hitl_confirmation_requested",
            task_id=task_id,
            action_id=action_id,
            description=action_description[:120],
        )

        # Wait for response or timeout
        try:
            await asyncio.wait_for(event.wait(), timeout=self._timeout)
            approved = self._responses.get(action_id, False)
        except asyncio.TimeoutError:
            logger.warning(
                "hitl_confirmation_timeout",
                task_id=task_id,
                action_id=action_id,
            )
            approved = False
        finally:
            self._pending.pop(action_id, None)
            self._responses.pop(action_id, None)

        logger.info(
            "hitl_confirmation_result",
            task_id=task_id,
            action_id=action_id,
            approved=approved,
        )
        return approved

    def resolve_confirmation(self, action_id: str, approved: bool) -> bool:
        """Called by the WS handler when the user responds.

        Returns True if the action_id was found (still pending).
        """
        event = self._pending.get(action_id)
        if not event:
            logger.warning("hitl_resolve_unknown_action", action_id=action_id)
            return False

        self._responses[action_id] = approved
        event.set()
        return True

    # -- auto-approve whitelist --------------------------------------------

    def set_auto_approve(self, domain: str) -> None:
        """Add a domain to the auto-approve whitelist."""
        self._auto_approve_domains.add(domain.lower())

    def remove_auto_approve(self, domain: str) -> None:
        """Remove a domain from the auto-approve whitelist."""
        self._auto_approve_domains.discard(domain.lower())

    def get_auto_approve_domains(self) -> list[str]:
        """Return the list of auto-approved domains."""
        return sorted(self._auto_approve_domains)

    # -- introspection -----------------------------------------------------

    @property
    def pending_count(self) -> int:
        """Number of pending confirmation requests."""
        return len(self._pending)
