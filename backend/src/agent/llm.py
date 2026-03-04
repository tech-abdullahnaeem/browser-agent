"""LLM factory — creates Gemini Flash (fast) and Gemini Pro (planning) instances."""

from __future__ import annotations

from functools import lru_cache

from browser_use import ChatGoogle

from src.config import Settings, get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _build_chat_google(
    model: str,
    *,
    api_key: str,
    temperature: float,
) -> ChatGoogle:
    """Construct a browser-use ChatGoogle instance."""
    return ChatGoogle(
        model=model,
        api_key=api_key,
        temperature=temperature,
    )


def get_flash_llm(settings: Settings | None = None) -> ChatGoogle:
    """Return the *fast* Gemini model used for step-by-step execution."""
    s = settings or get_settings()
    llm = _build_chat_google(
        model=s.flash_model,
        api_key=s.gemini_api_key,
        temperature=s.flash_temperature,
    )
    logger.debug("created_flash_llm", model=s.flash_model)
    return llm


def get_pro_llm(settings: Settings | None = None) -> ChatGoogle:
    """Return the *powerful* Gemini model used for planning / complex reasoning."""
    s = settings or get_settings()
    llm = _build_chat_google(
        model=s.pro_model,
        api_key=s.gemini_api_key,
        temperature=s.pro_temperature,
    )
    logger.debug("created_pro_llm", model=s.pro_model)
    return llm


def get_default_llm(settings: Settings | None = None) -> ChatGoogle:
    """Convenience alias — the default agent LLM is Flash."""
    return get_flash_llm(settings)
