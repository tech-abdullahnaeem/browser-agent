"""Shared pytest fixtures for the browser-agent test suite."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import Settings


@pytest.fixture()
def test_settings() -> Settings:
    """Return a Settings instance with a dummy API key for unit tests."""
    return Settings(
        gemini_api_key="test-api-key-not-real",
        headless=True,
        max_steps=5,
        max_failures=2,
        use_vision=False,
        wait_between_actions=0.1,
        enable_planning=False,
        log_level="DEBUG",
    )


@pytest.fixture()
def mock_flash_llm() -> MagicMock:
    """Return a mock LLM that simulates Gemini Flash responses."""
    llm = MagicMock()
    llm.model_name = "gemini-2.5-pro"

    mock_response = MagicMock()
    mock_response.content = "I'll click the search button."
    llm.invoke.return_value = mock_response
    llm.ainvoke = AsyncMock(return_value=mock_response)
    return llm


@pytest.fixture()
def mock_pro_llm() -> MagicMock:
    """Return a mock LLM that simulates Gemini Pro responses."""
    llm = MagicMock()
    llm.model_name = "gemini-2.5-pro"

    mock_response = MagicMock()
    mock_response.content = (
        "1. Navigate to google.com\n"
        "2. Type search query\n"
        "3. Click search button\n"
        "4. Extract results"
    )
    llm.invoke.return_value = mock_response
    llm.ainvoke = AsyncMock(return_value=mock_response)
    return llm
