"""Application settings loaded from environment variables / .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the browser-agent backend.

    Values are read from environment variables first, then from a `.env` file
    located alongside the `backend/` directory (or wherever the process is run).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────
    gemini_api_key: str = Field(description="Google Gemini API key")
    flash_model: str = Field(default="gemini-2.5-pro", description="Fast model for step execution")
    pro_model: str = Field(default="gemini-2.5-pro", description="Powerful model for planning")
    flash_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    pro_temperature: float = Field(default=0.2, ge=0.0, le=2.0)

    # ── Browser ──────────────────────────────────────────────────────────
    browser_user_data_dir: str | None = Field(
        default=None,
        description="Path to Chrome user-data-dir. None = fresh temp profile.",
    )
    headless: bool = Field(default=False)

    # ── Agent ────────────────────────────────────────────────────────────
    max_steps: int = Field(default=50, ge=1)
    max_failures: int = Field(default=5, ge=1)
    use_vision: bool = Field(default=True)
    wait_between_actions: float = Field(default=0.5, ge=0.0)
    max_actions_per_step: int = Field(default=5, ge=1)
    enable_planning: bool = Field(default=True)

    # ── Complexity heuristic (for multi-model routing) ────────────────────
    complexity_word_threshold: int = Field(
        default=15,
        description="Tasks with more words than this are considered complex → use Pro for planning.",
    )

    # ── Logging ──────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")

    # ── Paths ────────────────────────────────────────────────────────────
    data_dir: Path = Field(default=Path("data"), description="Directory for DB / vector store / screenshots")

    # ── Memory (Phase 5) ─────────────────────────────────────────────────
    db_path: str | None = Field(
        default=None,
        description="SQLite database path. Defaults to data_dir/browser_agent.db",
    )
    chromadb_path: str | None = Field(
        default=None,
        description="ChromaDB persist directory. Defaults to data_dir/chromadb",
    )
    vault_db_path: str | None = Field(
        default=None,
        description="Vault SQLite path. Defaults to data_dir/vault.db",
    )
    enable_memory: bool = Field(
        default=True,
        description="Enable persistent task memory (SQLite + ChromaDB)",
    )
    memory_similar_tasks: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Number of similar past tasks to inject into the prompt",
    )
    memory_min_similarity: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity to include a past task memory",
    )

    # ── Safety & HITL (Phase 6) ──────────────────────────────────────────
    hitl_timeout_seconds: int = Field(
        default=60,
        ge=5,
        le=300,
        description="Seconds to wait for user confirmation before auto-denying",
    )
    allowed_domains: list[str] = Field(
        default_factory=list,
        description="If non-empty, agent can only navigate to these domains",
    )
    blocked_domains: list[str] = Field(
        default_factory=list,
        description="Agent will never navigate to these domains",
    )
    enable_safety: bool = Field(
        default=True,
        description="Enable HITL safety gate and domain filtering",
    )

    def ensure_data_dir(self) -> Path:
        """Create the data directory if it doesn't exist and return its path."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir

    def get_db_path(self) -> str:
        """Return resolved SQLite path."""
        if self.db_path:
            return self.db_path
        return str(self.ensure_data_dir() / "browser_agent.db")

    def get_chromadb_path(self) -> str:
        """Return resolved ChromaDB path."""
        if self.chromadb_path:
            return self.chromadb_path
        return str(self.ensure_data_dir() / "chromadb")

    def get_vault_db_path(self) -> str:
        """Return resolved vault DB path."""
        if self.vault_db_path:
            return self.vault_db_path
        return str(self.ensure_data_dir() / "vault.db")


# Singleton-ish helper – import and call get_settings() wherever needed.
_settings: Settings | None = None


def get_settings() -> Settings:
    """Return a cached Settings instance (creates on first call)."""
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings
