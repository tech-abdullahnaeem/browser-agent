"""REST API routes for runtime agent configuration.

- ``GET  /api/config``  — read current config
- ``PUT  /api/config``  — update config (partial)
"""

from __future__ import annotations

from fastapi import APIRouter

from src.config import get_settings
from src.models.config import AgentConfig, AgentConfigUpdate

router = APIRouter(prefix="/api/config", tags=["config"])

# ---------------------------------------------------------------------------
# In-memory runtime config override layer
# ---------------------------------------------------------------------------
_runtime_overrides: dict[str, object] = {}


def get_effective_config() -> AgentConfig:
    """Return the effective agent configuration (base settings + overrides)."""
    s = get_settings()
    base = AgentConfig(
        max_steps=s.max_steps,
        max_failures=s.max_failures,
        use_vision=s.use_vision,
        headless=s.headless,
        wait_between_actions=s.wait_between_actions,
        max_actions_per_step=s.max_actions_per_step,
        enable_planning=s.enable_planning,
        flash_model=s.flash_model,
        pro_model=s.pro_model,
    )
    if _runtime_overrides:
        return base.model_copy(update=_runtime_overrides)
    return base


def apply_config_to_settings() -> None:
    """Apply runtime overrides back to the singleton Settings.

    This ensures the agent runner picks up the latest config.
    """
    s = get_settings()
    cfg = get_effective_config()
    s.max_steps = cfg.max_steps
    s.max_failures = cfg.max_failures
    s.use_vision = cfg.use_vision
    s.headless = cfg.headless
    s.wait_between_actions = cfg.wait_between_actions
    s.max_actions_per_step = cfg.max_actions_per_step
    s.enable_planning = cfg.enable_planning
    s.flash_model = cfg.flash_model
    s.pro_model = cfg.pro_model


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=AgentConfig, summary="Get current agent config")
async def get_config() -> AgentConfig:
    """Return the current effective agent configuration."""
    return get_effective_config()


@router.put("", response_model=AgentConfig, summary="Update agent config")
async def update_config(update: AgentConfigUpdate) -> AgentConfig:
    """Apply partial updates to the runtime agent configuration.

    Only provided (non-null) fields are updated.
    """
    updates = update.model_dump(exclude_none=True)
    _runtime_overrides.update(updates)
    apply_config_to_settings()
    return get_effective_config()
