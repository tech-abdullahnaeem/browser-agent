"""REST API routes for the personal data vault.

- ``POST   /api/vault/unlock``              — unlock with passphrase
- ``POST   /api/vault/lock``                — lock the vault
- ``GET    /api/vault/status``              — check unlock status & field list
- ``GET    /api/vault/fields``              — get all decrypted fields (requires unlocked)
- ``GET    /api/vault/fields/{field_type}`` — get a single decrypted field
- ``PUT    /api/vault/fields/{field_type}`` — set / update a field
- ``DELETE /api/vault/fields/{field_type}`` — delete a field
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.models.vault import (
    VaultFieldResponse,
    VaultFieldsResponse,
    VaultFieldUpdate,
    VaultStatusResponse,
    VaultUnlockRequest,
)

router = APIRouter(prefix="/api/vault", tags=["vault"])


# ---------------------------------------------------------------------------
# Module-level vault reference (set by main.py lifespan)
# ---------------------------------------------------------------------------
_vault = None


def set_vault(vault):
    """Called by main.py to inject the initialized PersonalVault instance."""
    global _vault  # noqa: PLW0603
    _vault = vault


def _get_vault():
    """Return the vault or 503 if not initialized."""
    if _vault is None:
        raise HTTPException(status_code=503, detail="Vault not initialized")
    return _vault


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/unlock",
    summary="Unlock the vault",
    status_code=status.HTTP_200_OK,
)
async def unlock_vault(request: VaultUnlockRequest) -> dict[str, str]:
    """Unlock the vault with the given passphrase."""
    vault = _get_vault()
    ok = await vault.unlock(request.passphrase)
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid passphrase")
    return {"message": "Vault unlocked"}


@router.post(
    "/lock",
    summary="Lock the vault",
    status_code=status.HTTP_200_OK,
)
async def lock_vault() -> dict[str, str]:
    """Lock the vault and destroy the in-memory key."""
    vault = _get_vault()
    await vault.lock()
    return {"message": "Vault locked"}


@router.get(
    "/status",
    response_model=VaultStatusResponse,
    summary="Get vault status",
)
async def vault_status() -> VaultStatusResponse:
    """Return whether the vault is unlocked and list stored field types."""
    vault = _get_vault()
    fields = await vault.list_fields()
    return VaultStatusResponse(
        is_unlocked=vault.is_unlocked(),
        stored_fields=fields,
    )


@router.get(
    "/fields",
    response_model=VaultFieldsResponse,
    summary="Get all decrypted fields",
)
async def get_all_fields() -> VaultFieldsResponse:
    """Return all decrypted vault fields.  Vault must be unlocked."""
    vault = _get_vault()
    if not vault.is_unlocked():
        raise HTTPException(status_code=403, detail="Vault is locked")
    data = await vault.get_all_decrypted()
    fields = [VaultFieldResponse(field_type=k, value=v) for k, v in data.items()]
    return VaultFieldsResponse(fields=fields, total=len(fields))


@router.get(
    "/fields/{field_type}",
    response_model=VaultFieldResponse,
    summary="Get a single decrypted field",
)
async def get_field(field_type: str) -> VaultFieldResponse:
    """Return one decrypted value.  Vault must be unlocked."""
    vault = _get_vault()
    if not vault.is_unlocked():
        raise HTTPException(status_code=403, detail="Vault is locked")
    value = await vault.get_field(field_type)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Field '{field_type}' not found")
    return VaultFieldResponse(field_type=field_type, value=value)


@router.put(
    "/fields/{field_type}",
    summary="Set or update a vault field",
    status_code=status.HTTP_200_OK,
)
async def set_field(field_type: str, body: VaultFieldUpdate) -> dict[str, str]:
    """Encrypt and store a value for the given field type."""
    vault = _get_vault()
    if not vault.is_unlocked():
        raise HTTPException(status_code=403, detail="Vault is locked")
    try:
        await vault.set_field(field_type, body.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": f"Field '{field_type}' saved"}


@router.delete(
    "/fields/{field_type}",
    summary="Delete a vault field",
    status_code=status.HTTP_200_OK,
)
async def delete_field(field_type: str) -> dict[str, str]:
    """Delete a stored field."""
    vault = _get_vault()
    deleted = await vault.delete_field(field_type)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Field '{field_type}' not found")
    return {"message": f"Field '{field_type}' deleted"}
