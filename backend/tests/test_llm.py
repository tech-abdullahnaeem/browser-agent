"""Tests for src.agent.llm — LLM factory functions."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.agent.llm import get_default_llm, get_flash_llm, get_pro_llm
from src.config import Settings


@pytest.fixture()
def settings() -> Settings:
    return Settings(
        gemini_api_key="test-key-123",
        headless=True,
        log_level="DEBUG",
    )


class TestGetFlashLLM:
    def test_returns_correct_model(self, settings: Settings) -> None:
        llm = get_flash_llm(settings)
        # ChatGoogle stores the model name — should match settings
        assert llm.model == settings.flash_model

    def test_uses_api_key_from_settings(self, settings: Settings) -> None:
        llm = get_flash_llm(settings)
        assert llm.api_key == settings.gemini_api_key

    def test_uses_configured_temperature(self, settings: Settings) -> None:
        llm = get_flash_llm(settings)
        assert llm.temperature == settings.flash_temperature


class TestGetProLLM:
    def test_returns_correct_model(self, settings: Settings) -> None:
        llm = get_pro_llm(settings)
        assert "pro" in llm.model.lower() or "pro" in settings.pro_model.lower()

    def test_uses_api_key_from_settings(self, settings: Settings) -> None:
        llm = get_pro_llm(settings)
        assert llm.api_key == settings.gemini_api_key

    def test_uses_configured_temperature(self, settings: Settings) -> None:
        llm = get_pro_llm(settings)
        assert llm.temperature == settings.pro_temperature


class TestGetDefaultLLM:
    def test_default_is_flash(self, settings: Settings) -> None:
        default = get_default_llm(settings)
        flash = get_flash_llm(settings)
        assert default.model == flash.model
