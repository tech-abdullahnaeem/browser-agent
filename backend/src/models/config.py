"""Runtime-adjustable agent configuration model.

These are settings the user can change via the REST API without restarting
the server.  The underlying ``Settings`` (from env / .env) provides defaults.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """User-adjustable agent configuration exposed via ``GET/PUT /api/config``."""

    max_steps: int = Field(default=50, ge=1, le=500, description="Maximum steps per task")
    max_failures: int = Field(default=5, ge=1, le=50, description="Max consecutive failures before abort")
    use_vision: bool = Field(default=True, description="Enable screenshot-based vision")
    headless: bool = Field(default=False, description="Run browser in headless mode")
    wait_between_actions: float = Field(
        default=0.5, ge=0.0, le=10.0, description="Seconds to wait between browser actions"
    )
    max_actions_per_step: int = Field(default=5, ge=1, le=20, description="Max actions per agent step")
    enable_planning: bool = Field(default=True, description="Use Gemini Pro for complex task planning")
    flash_model: str = Field(default="gemini-2.5-pro", description="Model for step execution")
    pro_model: str = Field(default="gemini-2.5-pro", description="Model for planning")


class AgentConfigUpdate(BaseModel):
    """Partial update for agent configuration — all fields optional."""

    max_steps: int | None = Field(default=None, ge=1, le=500)
    max_failures: int | None = Field(default=None, ge=1, le=50)
    use_vision: bool | None = None
    headless: bool | None = None
    wait_between_actions: float | None = Field(default=None, ge=0.0, le=10.0)
    max_actions_per_step: int | None = Field(default=None, ge=1, le=20)
    enable_planning: bool | None = None
    flash_model: str | None = None
    pro_model: str | None = None
