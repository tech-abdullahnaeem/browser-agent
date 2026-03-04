"""Pydantic models for the personal data vault API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VaultUnlockRequest(BaseModel):
    """Request body for unlocking the vault."""
    passphrase: str = Field(..., min_length=1, description="Passphrase to derive encryption key")


class VaultFieldUpdate(BaseModel):
    """Request body for setting a vault field value."""
    value: str = Field(..., min_length=1, description="The value to store (will be encrypted)")


class VaultFieldResponse(BaseModel):
    """Single vault field returned to the client."""
    field_type: str
    value: str


class VaultFieldsResponse(BaseModel):
    """All decrypted vault fields."""
    fields: list[VaultFieldResponse]
    total: int


class VaultStatusResponse(BaseModel):
    """Vault lock/unlock status."""
    is_unlocked: bool
    stored_fields: list[str] = Field(default_factory=list)
