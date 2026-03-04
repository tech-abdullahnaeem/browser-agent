"""Encrypted personal data vault.

Uses Fernet symmetric encryption with a key derived from a user passphrase
(PBKDF2, 480 000 iterations).  Data is stored in-memory while unlocked and
persisted encrypted in SQLite.

Supported field types: name, email, phone, address_line1, address_city,
address_state, address_zip, address_country, card_number, card_exp,
card_cvv, card_name.
"""

from __future__ import annotations

import base64
import os
from typing import Any

import aiosqlite
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.utils.logging import get_logger

logger = get_logger(__name__)

_VALID_FIELD_TYPES = frozenset({
    "name", "email", "phone",
    "address_line1", "address_city", "address_state", "address_zip", "address_country",
    "card_number", "card_exp", "card_cvv", "card_name",
    "username", "password", "company", "custom",
})

_CREATE_VAULT = """
CREATE TABLE IF NOT EXISTS vault (
    field_type      TEXT PRIMARY KEY,
    encrypted_value BLOB NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
"""

_CREATE_VAULT_META = """
CREATE TABLE IF NOT EXISTS vault_meta (
    key   TEXT PRIMARY KEY,
    value BLOB NOT NULL
);
"""


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a 32-byte Fernet key from a passphrase and salt using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


class PersonalVault:
    """Encrypted personal data vault backed by SQLite.

    Workflow:
        vault = PersonalVault(db_path)
        await vault.initialize()
        await vault.unlock("my-passphrase")     # derive key, decrypt all fields
        data = await vault.get_all_decrypted()   # {'name': 'John', 'email': '...'}
        await vault.set_field("email", "john@example.com")
        await vault.lock()
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None
        self._fernet: Fernet | None = None
        self._salt: bytes | None = None

    # -- lifecycle ---------------------------------------------------------

    async def initialize(self) -> None:
        """Open DB, create tables, and load/generate salt."""
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute(_CREATE_VAULT)
        await self._db.execute(_CREATE_VAULT_META)
        await self._db.commit()

        # Load or create salt
        cursor = await self._db.execute("SELECT value FROM vault_meta WHERE key = 'salt'")
        row = await cursor.fetchone()
        if row:
            self._salt = bytes(row["value"])
        else:
            self._salt = os.urandom(16)
            await self._db.execute(
                "INSERT INTO vault_meta (key, value) VALUES ('salt', ?)",
                (self._salt,),
            )
            await self._db.commit()

        logger.info("vault_initialized", db_path=self._db_path)

    async def close(self) -> None:
        """Lock and close the vault."""
        self._fernet = None
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        assert self._db is not None, "PersonalVault not initialized"
        return self._db

    # -- lock / unlock -----------------------------------------------------

    async def unlock(self, passphrase: str) -> bool:
        """Derive the encryption key from the passphrase.

        Returns True if the passphrase is valid (can decrypt at least one
        stored field, or the vault is empty).  Returns False on bad passphrase.
        """
        assert self._salt is not None, "Vault not initialized"
        key = _derive_key(passphrase, self._salt)
        fernet = Fernet(key)

        # Verify by attempting to decrypt an existing field
        cursor = await self.db.execute("SELECT encrypted_value FROM vault LIMIT 1")
        row = await cursor.fetchone()
        if row:
            try:
                fernet.decrypt(bytes(row["encrypted_value"]))
            except InvalidToken:
                logger.warning("vault_unlock_failed_bad_passphrase")
                return False

        self._fernet = fernet
        logger.info("vault_unlocked")
        return True

    async def lock(self) -> None:
        """Destroy the in-memory key, locking the vault."""
        self._fernet = None
        logger.info("vault_locked")

    def is_unlocked(self) -> bool:
        """Check whether the vault is currently unlocked."""
        return self._fernet is not None

    # -- field CRUD --------------------------------------------------------

    async def set_field(self, field_type: str, value: str) -> None:
        """Encrypt and store (or update) a vault field."""
        if not self.is_unlocked():
            raise PermissionError("Vault is locked — call unlock() first")
        if field_type not in _VALID_FIELD_TYPES:
            raise ValueError(f"Invalid field type: {field_type}")

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()

        assert self._fernet is not None
        encrypted = self._fernet.encrypt(value.encode("utf-8"))

        await self.db.execute(
            """
            INSERT INTO vault (field_type, encrypted_value, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(field_type) DO UPDATE SET
                encrypted_value = excluded.encrypted_value,
                updated_at = excluded.updated_at
            """,
            (field_type, encrypted, now, now),
        )
        await self.db.commit()

    async def get_field(self, field_type: str) -> str | None:
        """Decrypt and return a single field value, or None."""
        if not self.is_unlocked():
            raise PermissionError("Vault is locked")
        assert self._fernet is not None

        cursor = await self.db.execute(
            "SELECT encrypted_value FROM vault WHERE field_type = ?",
            (field_type,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._fernet.decrypt(bytes(row["encrypted_value"])).decode("utf-8")

    async def get_all_decrypted(self) -> dict[str, str]:
        """Decrypt and return ALL vault fields as a dict."""
        if not self.is_unlocked():
            raise PermissionError("Vault is locked")
        assert self._fernet is not None

        cursor = await self.db.execute("SELECT field_type, encrypted_value FROM vault")
        rows = await cursor.fetchall()
        result: dict[str, str] = {}
        for row in rows:
            try:
                result[row["field_type"]] = self._fernet.decrypt(
                    bytes(row["encrypted_value"])
                ).decode("utf-8")
            except InvalidToken:
                logger.warning("vault_decrypt_failed_for_field", field=row["field_type"])
        return result

    async def delete_field(self, field_type: str) -> bool:
        """Delete a vault field.  Returns True if deleted."""
        cursor = await self.db.execute(
            "DELETE FROM vault WHERE field_type = ?",
            (field_type,),
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def list_fields(self) -> list[str]:
        """List stored field types (without decrypting values)."""
        cursor = await self.db.execute("SELECT field_type FROM vault ORDER BY field_type")
        rows = await cursor.fetchall()
        return [row["field_type"] for row in rows]

    async def get_form_fill_data(self) -> dict[str, str]:
        """Return all vault data suitable for auto-filling a form.

        Only returns data the agent would need for form filling.  The vault
        must be unlocked.
        """
        return await self.get_all_decrypted()
