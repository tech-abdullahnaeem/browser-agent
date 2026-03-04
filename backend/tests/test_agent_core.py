"""Tests for src.agent.core — BrowserAgentRunner."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent.core import BrowserAgentRunner, _history_entry_to_step
from src.config import Settings
from src.models.task import StepSummary, TaskStatus


@pytest.fixture()
def settings() -> Settings:
    return Settings(
        gemini_api_key="test-key-123",
        headless=True,
        max_steps=3,
        max_failures=2,
        use_vision=False,
        wait_between_actions=0.1,
        enable_planning=False,
        log_level="DEBUG",
    )


class TestBrowserAgentRunner:
    def test_init_with_settings(self, settings: Settings) -> None:
        runner = BrowserAgentRunner(settings=settings)
        assert runner.settings.max_steps == 3
        assert runner.settings.headless is True

    def test_init_without_settings_uses_default(self) -> None:
        """Ensure it doesn't crash when created with env-based settings."""
        # This test only checks that __init__ doesn't raise;
        # it will use get_settings() which needs GEMINI_API_KEY in env
        with patch("src.agent.core.get_settings") as mock_gs:
            mock_gs.return_value = Settings(
                gemini_api_key="dummy",
                headless=True,
            )
            runner = BrowserAgentRunner()
            assert runner.settings.gemini_api_key == "dummy"


class TestHistoryEntryToStep:
    def test_basic_conversion(self) -> None:
        """Test conversion of a mock AgentHistory entry to StepSummary."""
        # Build a minimal mock AgentHistory
        mock_action = MagicMock()
        mock_action.model_dump.return_value = {"click_element": {"index": 5}}

        mock_output = MagicMock()
        mock_output.next_goal = "Click the search button"
        mock_output.thinking = "I need to find and click the search button"
        mock_output.action = [mock_action]

        mock_result = MagicMock()
        mock_result.error = None

        mock_entry = MagicMock()
        mock_entry.model_output = mock_output
        mock_entry.result = [mock_result]

        step = _history_entry_to_step(1, mock_entry)

        assert step.step_number == 1
        assert step.action == "click_element"
        assert step.reasoning == "Click the search button"
        assert step.thinking == "I need to find and click the search button"
        assert step.success is True
        assert step.error is None

    def test_conversion_with_error(self) -> None:
        """Test that errors in ActionResult are captured."""
        mock_output = MagicMock()
        mock_output.next_goal = "Navigate somewhere"
        mock_output.thinking = None
        mock_output.action = []

        mock_result = MagicMock()
        mock_result.error = "Element not found"

        mock_entry = MagicMock()
        mock_entry.model_output = mock_output
        mock_entry.result = [mock_result]

        step = _history_entry_to_step(2, mock_entry)

        assert step.step_number == 2
        assert step.success is False
        assert "Element not found" in step.error

    def test_conversion_with_no_output(self) -> None:
        """Test handling when model_output is None."""
        mock_entry = MagicMock()
        mock_entry.model_output = None
        mock_entry.result = []

        step = _history_entry_to_step(1, mock_entry)
        assert step.action == "unknown"
        assert step.reasoning is None


class TestPlannerIntegration:
    def test_is_complex_task(self, settings: Settings) -> None:
        from src.agent.planner import is_complex_task

        # Simple task
        assert is_complex_task("Go to google.com", settings) is False

        # Long task
        long_task = "Go to the website and then find the product page and then add to cart and then checkout"
        assert is_complex_task(long_task, settings) is True

        # Task with conjunctions
        assert is_complex_task("First search for hotels, then book the cheapest one", settings) is True
