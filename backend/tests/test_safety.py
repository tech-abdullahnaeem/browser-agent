"""Tests for src.safety — HITLGate, AuditLogger, DomainFilter, SafetyWatchdog."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.safety.hitl import HITLGate, DESTRUCTIVE_KEYWORDS, DESTRUCTIVE_URL_PATTERNS
from src.safety.audit import AuditLogger
from src.safety.domain_filter import DomainFilter
from src.agent.watchdog import SafetyWatchdog


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def audit_logger(tmp_path: Path) -> AuditLogger:
    logger = AuditLogger(str(tmp_path / "test_audit.db"))
    await logger.initialize()
    yield logger
    await logger.close()


@pytest.fixture()
def domain_filter() -> DomainFilter:
    return DomainFilter()


@pytest.fixture()
def hitl_gate() -> HITLGate:
    return HITLGate(timeout=5, broadcast_fn=AsyncMock())


# ═══════════════════════════════════════════════════════════════════════════
# HITLGate — Pattern Matching
# ═══════════════════════════════════════════════════════════════════════════


class TestHITLGatePatterns:
    """Test requires_confirmation pattern matching."""

    def test_destructive_keyword_buy(self, hitl_gate: HITLGate) -> None:
        assert hitl_gate.requires_confirmation(element_text="Buy Now") is True

    def test_destructive_keyword_checkout(self, hitl_gate: HITLGate) -> None:
        assert hitl_gate.requires_confirmation(element_text="Proceed to Checkout") is True

    def test_destructive_keyword_delete(self, hitl_gate: HITLGate) -> None:
        assert hitl_gate.requires_confirmation(element_text="Delete Account") is True

    def test_destructive_keyword_pay(self, hitl_gate: HITLGate) -> None:
        assert hitl_gate.requires_confirmation(element_text="Pay $99.00") is True

    def test_destructive_keyword_submit_payment(self, hitl_gate: HITLGate) -> None:
        assert hitl_gate.requires_confirmation(element_text="Submit Payment") is True

    def test_destructive_keyword_cancel_subscription(self, hitl_gate: HITLGate) -> None:
        assert hitl_gate.requires_confirmation(element_text="Cancel Subscription") is True

    def test_destructive_keyword_transfer_funds(self, hitl_gate: HITLGate) -> None:
        assert hitl_gate.requires_confirmation(element_text="Transfer Funds") is True

    def test_safe_text_not_flagged(self, hitl_gate: HITLGate) -> None:
        assert hitl_gate.requires_confirmation(element_text="Click here for info") is False

    def test_safe_navigation_not_flagged(self, hitl_gate: HITLGate) -> None:
        assert hitl_gate.requires_confirmation(element_text="Next Page") is False

    def test_empty_text_not_flagged(self, hitl_gate: HITLGate) -> None:
        assert hitl_gate.requires_confirmation(element_text="") is False

    def test_none_text_not_flagged(self, hitl_gate: HITLGate) -> None:
        assert hitl_gate.requires_confirmation(element_text=None) is False

    def test_url_pattern_checkout(self, hitl_gate: HITLGate) -> None:
        assert hitl_gate.requires_confirmation(url="https://shop.com/checkout") is True

    def test_url_pattern_payment(self, hitl_gate: HITLGate) -> None:
        assert hitl_gate.requires_confirmation(url="https://shop.com/payment/confirm") is True

    def test_url_pattern_billing(self, hitl_gate: HITLGate) -> None:
        assert hitl_gate.requires_confirmation(url="https://shop.com/billing") is True

    def test_url_pattern_order_confirm(self, hitl_gate: HITLGate) -> None:
        assert hitl_gate.requires_confirmation(url="https://shop.com/order/confirm") is True

    def test_url_safe(self, hitl_gate: HITLGate) -> None:
        assert hitl_gate.requires_confirmation(url="https://example.com/about") is False

    def test_url_none(self, hitl_gate: HITLGate) -> None:
        assert hitl_gate.requires_confirmation(url=None) is False


class TestHITLGateAutoApprove:
    """Test auto-approve domain whitelist."""

    def test_auto_approve_skips_confirmation(self, hitl_gate: HITLGate) -> None:
        hitl_gate.set_auto_approve("safe-shop.com")
        # This would normally require confirmation due to "checkout" keyword
        assert hitl_gate.requires_confirmation(
            url="https://safe-shop.com/checkout",
            element_text="Buy Now",
        ) is False

    def test_auto_approve_does_not_affect_other_domains(self, hitl_gate: HITLGate) -> None:
        hitl_gate.set_auto_approve("safe-shop.com")
        assert hitl_gate.requires_confirmation(
            url="https://other-shop.com/checkout",
            element_text="Buy Now",
        ) is True

    def test_remove_auto_approve(self, hitl_gate: HITLGate) -> None:
        hitl_gate.set_auto_approve("safe-shop.com")
        hitl_gate.remove_auto_approve("safe-shop.com")
        assert hitl_gate.requires_confirmation(
            url="https://safe-shop.com/checkout",
            element_text="Buy Now",
        ) is True

    def test_get_auto_approve_domains(self, hitl_gate: HITLGate) -> None:
        hitl_gate.set_auto_approve("b.com")
        hitl_gate.set_auto_approve("a.com")
        assert hitl_gate.get_auto_approve_domains() == ["a.com", "b.com"]


class TestHITLGateConfirmation:
    """Test async confirmation request/resolve flow."""

    @pytest.mark.asyncio
    async def test_approve_flow(self) -> None:
        broadcast_fn = AsyncMock()
        gate = HITLGate(timeout=5, broadcast_fn=broadcast_fn)

        async def _approve_after_delay():
            await asyncio.sleep(0.1)
            # Find the pending action_id
            while gate.pending_count == 0:
                await asyncio.sleep(0.05)
            action_id = list(gate._pending.keys())[0]
            gate.resolve_confirmation(action_id, approved=True)

        asyncio.create_task(_approve_after_delay())

        result = await gate.request_confirmation(
            task_id="task-1",
            action_description="Buy widget",
            url="https://shop.com/checkout",
            element_text="Buy Now",
        )
        assert result is True
        assert gate.pending_count == 0

    @pytest.mark.asyncio
    async def test_deny_flow(self) -> None:
        broadcast_fn = AsyncMock()
        gate = HITLGate(timeout=5, broadcast_fn=broadcast_fn)

        async def _deny_after_delay():
            await asyncio.sleep(0.1)
            while gate.pending_count == 0:
                await asyncio.sleep(0.05)
            action_id = list(gate._pending.keys())[0]
            gate.resolve_confirmation(action_id, approved=False)

        asyncio.create_task(_deny_after_delay())

        result = await gate.request_confirmation(
            task_id="task-1",
            action_description="Delete account",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_timeout_auto_denies(self) -> None:
        gate = HITLGate(timeout=1, broadcast_fn=AsyncMock())
        result = await gate.request_confirmation(
            task_id="task-1",
            action_description="Submit payment",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_resolve_unknown_action_returns_false(self) -> None:
        gate = HITLGate(timeout=5)
        assert gate.resolve_confirmation("nonexistent-id", True) is False

    @pytest.mark.asyncio
    async def test_broadcast_called_on_request(self) -> None:
        broadcast_fn = AsyncMock()
        gate = HITLGate(timeout=1, broadcast_fn=broadcast_fn)
        await gate.request_confirmation(
            task_id="task-1",
            action_description="Buy something",
        )
        broadcast_fn.assert_called_once()
        call_args = broadcast_fn.call_args
        assert call_args[0][0] == "task-1"


# ═══════════════════════════════════════════════════════════════════════════
# AuditLogger
# ═══════════════════════════════════════════════════════════════════════════


class TestAuditLogger:
    """Test audit logging to SQLite."""

    @pytest.mark.asyncio
    async def test_log_action(self, audit_logger: AuditLogger) -> None:
        audit_id = await audit_logger.log_action(
            task_id="task-1",
            action_type="click",
            target_element="Buy Now",
            url="https://shop.com/product",
            was_destructive=True,
            user_confirmed=True,
        )
        assert isinstance(audit_id, str)
        assert len(audit_id) == 32  # UUID hex

    @pytest.mark.asyncio
    async def test_get_audit_trail(self, audit_logger: AuditLogger) -> None:
        await audit_logger.log_action(task_id="task-1", action_type="click")
        await audit_logger.log_action(task_id="task-1", action_type="type")
        await audit_logger.log_action(task_id="task-2", action_type="navigate")

        trail = await audit_logger.get_audit_trail("task-1")
        assert len(trail) == 2
        assert trail[0]["action_type"] == "click"
        assert trail[1]["action_type"] == "type"

    @pytest.mark.asyncio
    async def test_get_audit_trail_empty(self, audit_logger: AuditLogger) -> None:
        trail = await audit_logger.get_audit_trail("nonexistent")
        assert trail == []

    @pytest.mark.asyncio
    async def test_count_all(self, audit_logger: AuditLogger) -> None:
        await audit_logger.log_action(task_id="t1", action_type="a")
        await audit_logger.log_action(task_id="t2", action_type="b")
        assert await audit_logger.count() == 2

    @pytest.mark.asyncio
    async def test_count_by_task(self, audit_logger: AuditLogger) -> None:
        await audit_logger.log_action(task_id="t1", action_type="a")
        await audit_logger.log_action(task_id="t1", action_type="b")
        await audit_logger.log_action(task_id="t2", action_type="c")
        assert await audit_logger.count("t1") == 2
        assert await audit_logger.count("t2") == 1

    @pytest.mark.asyncio
    async def test_log_destructive_fields(self, audit_logger: AuditLogger) -> None:
        await audit_logger.log_action(
            task_id="task-1",
            action_type="click",
            was_destructive=True,
            user_confirmed=False,
            was_blocked=True,
        )
        trail = await audit_logger.get_audit_trail("task-1")
        assert len(trail) == 1
        entry = trail[0]
        assert entry["was_destructive"] == 1
        assert entry["user_confirmed"] == 0
        assert entry["was_blocked"] == 1

    @pytest.mark.asyncio
    async def test_log_long_element_truncated(self, audit_logger: AuditLogger) -> None:
        long_text = "x" * 1000
        await audit_logger.log_action(
            task_id="task-1",
            target_element=long_text,
        )
        trail = await audit_logger.get_audit_trail("task-1")
        assert len(trail[0]["target_element"]) == 500

    @pytest.mark.asyncio
    async def test_get_audit_trail_by_date(self, audit_logger: AuditLogger) -> None:
        await audit_logger.log_action(task_id="t1", action_type="a")
        # All entries should be within the last minute
        start = "2020-01-01T00:00:00"
        end = "2099-12-31T23:59:59"
        trail = await audit_logger.get_audit_trail_by_date(start, end)
        assert len(trail) == 1


# ═══════════════════════════════════════════════════════════════════════════
# DomainFilter
# ═══════════════════════════════════════════════════════════════════════════


class TestDomainFilter:
    """Test domain allow/block list filtering."""

    def test_all_allowed_by_default(self) -> None:
        df = DomainFilter()
        assert df.is_allowed("https://example.com/page") is True

    def test_blocked_domain(self) -> None:
        df = DomainFilter(blocked_domains=["evil.com"])
        assert df.is_allowed("https://evil.com/page") is False

    def test_blocked_wins_over_allowed(self) -> None:
        df = DomainFilter(
            allowed_domains=["evil.com"],
            blocked_domains=["evil.com"],
        )
        assert df.is_allowed("https://evil.com") is False

    def test_allowed_only(self) -> None:
        df = DomainFilter(allowed_domains=["safe.com"])
        assert df.is_allowed("https://safe.com/page") is True
        assert df.is_allowed("https://other.com/page") is False

    def test_case_insensitive(self) -> None:
        df = DomainFilter(blocked_domains=["Evil.COM"])
        assert df.is_allowed("https://EVIL.com") is False

    def test_port_stripped(self) -> None:
        df = DomainFilter(blocked_domains=["localhost"])
        assert df.is_allowed("http://localhost:8080/page") is False

    def test_non_http_url_allowed(self) -> None:
        df = DomainFilter(allowed_domains=["safe.com"])
        assert df.is_allowed("about:blank") is True

    def test_empty_url_allowed(self) -> None:
        df = DomainFilter(blocked_domains=["evil.com"])
        assert df.is_allowed("") is True

    def test_add_blocked_domain(self) -> None:
        df = DomainFilter()
        df.add_blocked_domain("spam.com")
        assert df.is_allowed("https://spam.com") is False

    def test_remove_blocked_domain(self) -> None:
        df = DomainFilter(blocked_domains=["spam.com"])
        df.remove_blocked_domain("spam.com")
        assert df.is_allowed("https://spam.com") is True

    def test_add_allowed_domain(self) -> None:
        df = DomainFilter(allowed_domains=["only.com"])
        df.add_allowed_domain("also.com")
        assert df.is_allowed("https://also.com") is True

    def test_remove_allowed_domain(self) -> None:
        df = DomainFilter(allowed_domains=["only.com", "other.com"])
        df.remove_allowed_domain("other.com")
        assert df.is_allowed("https://other.com") is False

    def test_get_lists(self) -> None:
        df = DomainFilter(
            allowed_domains=["b.com", "a.com"],
            blocked_domains=["z.com"],
        )
        lists = df.get_lists()
        assert lists["allowed"] == ["a.com", "b.com"]
        assert lists["blocked"] == ["z.com"]


# ═══════════════════════════════════════════════════════════════════════════
# SafetyWatchdog — action extraction
# ═══════════════════════════════════════════════════════════════════════════


class TestWatchdogExtraction:
    """Test _extract_action_info from AgentOutput."""

    def test_none_output(self) -> None:
        result = SafetyWatchdog._extract_action_info(None)
        assert result == [{"type": "unknown"}]

    def test_output_no_actions(self) -> None:
        mock_output = MagicMock()
        mock_output.action = []
        result = SafetyWatchdog._extract_action_info(mock_output)
        assert result == [{"type": "unknown"}]

    def test_output_with_click_action(self) -> None:
        mock_action = MagicMock()
        mock_action.model_dump.return_value = {
            "click_element": {"index": 5, "text": "Submit"}
        }
        mock_output = MagicMock()
        mock_output.action = [mock_action]

        result = SafetyWatchdog._extract_action_info(mock_output)
        assert len(result) == 1
        assert result[0]["type"] == "click_element"
        assert result[0]["element"] == "Submit"

    def test_output_with_navigate_action(self) -> None:
        mock_action = MagicMock()
        mock_action.model_dump.return_value = {
            "go_to_url": {"url": "https://example.com"}
        }
        mock_output = MagicMock()
        mock_output.action = [mock_action]

        result = SafetyWatchdog._extract_action_info(mock_output)
        assert len(result) == 1
        assert result[0]["type"] == "go_to_url"
        assert result[0]["url"] == "https://example.com"

    def test_output_with_multiple_actions(self) -> None:
        mock_action1 = MagicMock()
        mock_action1.model_dump.return_value = {
            "click_element": {"index": 1, "text": "OK"}
        }
        mock_action2 = MagicMock()
        mock_action2.model_dump.return_value = {
            "input_text": {"index": 2, "text": "hello"}
        }
        mock_output = MagicMock()
        mock_output.action = [mock_action1, mock_action2]

        result = SafetyWatchdog._extract_action_info(mock_output)
        assert len(result) == 2
        assert result[0]["type"] == "click_element"
        assert result[1]["type"] == "input_text"


class TestWatchdogOnStep:
    """Test on_step integration with HITL gate, audit, and domain filter."""

    @pytest.mark.asyncio
    async def test_on_step_logs_to_audit(self, audit_logger: AuditLogger) -> None:
        wd = SafetyWatchdog(
            task_id="task-1",
            audit_logger=audit_logger,
            model_used="test-model",
        )

        browser_state = MagicMock()
        browser_state.url = "https://example.com"

        mock_action = MagicMock()
        mock_action.model_dump.return_value = {
            "click_element": {"index": 1, "text": "Next"}
        }
        agent_output = MagicMock()
        agent_output.action = [mock_action]
        agent_output.next_goal = "Navigate forward"

        await wd.on_step(browser_state, agent_output, step_number=1)

        count = await audit_logger.count("task-1")
        assert count == 1

    @pytest.mark.asyncio
    async def test_on_step_blocks_domain(self, audit_logger: AuditLogger) -> None:
        df = DomainFilter(blocked_domains=["evil.com"])
        wd = SafetyWatchdog(
            task_id="task-1",
            domain_filter=df,
            audit_logger=audit_logger,
        )

        browser_state = MagicMock()
        browser_state.url = "https://evil.com/page"

        mock_action = MagicMock()
        mock_action.model_dump.return_value = {
            "navigate": {"url": "https://evil.com/page"}
        }
        agent_output = MagicMock()
        agent_output.action = [mock_action]
        agent_output.next_goal = "Go to evil"

        await wd.on_step(browser_state, agent_output, step_number=1)

        assert wd.was_blocked is True
        trail = await audit_logger.get_audit_trail("task-1")
        assert trail[0]["was_blocked"] == 1

    @pytest.mark.asyncio
    async def test_on_step_hitl_approve(self, audit_logger: AuditLogger) -> None:
        broadcast_fn = AsyncMock()
        gate = HITLGate(timeout=5, broadcast_fn=broadcast_fn)
        wd = SafetyWatchdog(
            task_id="task-1",
            hitl_gate=gate,
            audit_logger=audit_logger,
        )

        browser_state = MagicMock()
        browser_state.url = "https://shop.com/checkout"

        mock_action = MagicMock()
        mock_action.model_dump.return_value = {
            "click_element": {"index": 3, "text": "Buy Now"}
        }
        agent_output = MagicMock()
        agent_output.action = [mock_action]
        agent_output.next_goal = "Purchase item"

        async def _approve():
            await asyncio.sleep(0.1)
            while gate.pending_count == 0:
                await asyncio.sleep(0.05)
            action_id = list(gate._pending.keys())[0]
            gate.resolve_confirmation(action_id, approved=True)

        asyncio.create_task(_approve())
        await wd.on_step(browser_state, agent_output, step_number=1)

        assert wd.was_blocked is False
        trail = await audit_logger.get_audit_trail("task-1")
        assert trail[0]["was_destructive"] == 1
        assert trail[0]["user_confirmed"] == 1

    @pytest.mark.asyncio
    async def test_on_step_hitl_deny(self, audit_logger: AuditLogger) -> None:
        broadcast_fn = AsyncMock()
        gate = HITLGate(timeout=5, broadcast_fn=broadcast_fn)
        wd = SafetyWatchdog(
            task_id="task-1",
            hitl_gate=gate,
            audit_logger=audit_logger,
        )

        browser_state = MagicMock()
        browser_state.url = "https://shop.com/checkout"

        mock_action = MagicMock()
        mock_action.model_dump.return_value = {
            "click_element": {"index": 3, "text": "Delete Account"}
        }
        agent_output = MagicMock()
        agent_output.action = [mock_action]
        agent_output.next_goal = "Delete the account"

        async def _deny():
            await asyncio.sleep(0.1)
            while gate.pending_count == 0:
                await asyncio.sleep(0.05)
            action_id = list(gate._pending.keys())[0]
            gate.resolve_confirmation(action_id, approved=False)

        asyncio.create_task(_deny())
        await wd.on_step(browser_state, agent_output, step_number=1)

        assert wd.was_blocked is True
        trail = await audit_logger.get_audit_trail("task-1")
        assert trail[0]["was_destructive"] == 1
        assert trail[0]["user_confirmed"] == 0
        assert trail[0]["was_blocked"] == 1


# ═══════════════════════════════════════════════════════════════════════════
# Constants / regression
# ═══════════════════════════════════════════════════════════════════════════


class TestConstants:
    """Ensure keyword/pattern lists are not accidentally emptied."""

    def test_destructive_keywords_not_empty(self) -> None:
        assert len(DESTRUCTIVE_KEYWORDS) >= 10

    def test_destructive_url_patterns_not_empty(self) -> None:
        assert len(DESTRUCTIVE_URL_PATTERNS) >= 3
