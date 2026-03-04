"""FastAPI application entrypoint.

Run with::

    uv run uvicorn src.main:app --reload --port 8000

Or via the convenience script::

    uv run python -m uvicorn src.main:app --reload --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes_config import router as config_router
from src.api.routes_tasks import router as tasks_router
from src.api.routes_vault import router as vault_router
from src.api.routes_ws import router as ws_router
from src.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — runs on startup and shutdown."""
    from src.config import get_settings

    s = get_settings()
    setup_logging(s.log_level)
    logger.info(
        "server_starting",
        model=s.flash_model,
        headless=s.headless,
        max_steps=s.max_steps,
    )

    # -- Initialize memory subsystem (Phase 5) ----------------------------
    if s.enable_memory:
        from src.memory.sqlite_store import SQLiteStore
        from src.memory.vault import PersonalVault
        from src.memory.vector_store import VectorStore

        sqlite_store = SQLiteStore(s.get_db_path())
        await sqlite_store.initialize()
        app.state.sqlite_store = sqlite_store

        vector_store = VectorStore(s.get_chromadb_path())
        await vector_store.initialize()
        app.state.vector_store = vector_store

        vault = PersonalVault(s.get_vault_db_path())
        await vault.initialize()
        app.state.vault = vault

        # Inject vault into routes
        from src.api.routes_vault import set_vault
        set_vault(vault)

        # Inject stores into task_store so it can persist results
        from src.api.task_store import task_store
        task_store.set_memory_stores(sqlite_store, vector_store)

        logger.info(
            "memory_subsystem_initialized",
            db=s.get_db_path(),
            chromadb=s.get_chromadb_path(),
            vault=s.get_vault_db_path(),
        )

    # -- Initialize safety subsystem (Phase 6) -----------------------------
    if s.enable_safety:
        from src.safety.audit import AuditLogger
        from src.safety.domain_filter import DomainFilter
        from src.safety.hitl import HITLGate

        audit_logger = AuditLogger(s.get_db_path())
        await audit_logger.initialize()
        app.state.audit_logger = audit_logger

        domain_filter = DomainFilter(
            allowed_domains=s.allowed_domains,
            blocked_domains=s.blocked_domains,
        )
        app.state.domain_filter = domain_filter

        hitl_gate = HITLGate(
            timeout=s.hitl_timeout_seconds,
            broadcast_fn=ws_manager.broadcast,
        )
        app.state.hitl_gate = hitl_gate

        # Inject HITL gate into WS route handler
        from src.api.routes_ws import set_hitl_gate
        set_hitl_gate(hitl_gate)

        # Inject safety into task_store
        from src.api.task_store import task_store
        task_store.set_safety(hitl_gate, audit_logger, domain_filter)

        logger.info(
            "safety_subsystem_initialized",
            hitl_timeout=s.hitl_timeout_seconds,
            allowed_domains=len(s.allowed_domains),
            blocked_domains=len(s.blocked_domains),
        )

    yield

    # -- Cleanup safety subsystem ------------------------------------------
    if hasattr(app.state, "audit_logger"):
        await app.state.audit_logger.close()

    # -- Cleanup memory subsystem ------------------------------------------
    if hasattr(app.state, "vault"):
        await app.state.vault.close()
    if hasattr(app.state, "vector_store"):
        await app.state.vector_store.close()
    if hasattr(app.state, "sqlite_store"):
        await app.state.sqlite_store.close()

    logger.info("server_shutting_down")


app = FastAPI(
    title="Browser Agent API",
    description="AI browser automation agent powered by browser-use and Google Gemini",
    version="0.6.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow Chrome extension and local development
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"^chrome-extension://.*$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------
app.include_router(tasks_router)
app.include_router(config_router)
app.include_router(vault_router)
app.include_router(ws_router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "ok"}


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    """Root endpoint — API info."""
    return {
        "name": "Browser Agent API",
        "version": "0.6.0",
        "docs": "/docs",
    }
