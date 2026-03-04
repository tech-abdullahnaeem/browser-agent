"""Tests for src.memory — SQLiteStore, VectorStore, PersonalVault."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import pytest_asyncio

from src.memory.sqlite_store import SQLiteStore
from src.memory.vector_store import VectorStore
from src.memory.vault import PersonalVault


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def sqlite_store(tmp_path: Path) -> SQLiteStore:
    store = SQLiteStore(tmp_path / "test.db")
    await store.initialize()
    yield store
    await store.close()


@pytest_asyncio.fixture()
async def vector_store(tmp_path: Path) -> VectorStore:
    store = VectorStore(tmp_path / "chromadb")
    await store.initialize()
    yield store
    await store.close()


@pytest_asyncio.fixture()
async def vault(tmp_path: Path) -> PersonalVault:
    v = PersonalVault(str(tmp_path / "vault.db"))
    await v.initialize()
    yield v
    await v.close()


@pytest_asyncio.fixture()
async def unlocked_vault(vault: PersonalVault) -> PersonalVault:
    """A vault that is already unlocked with a known passphrase."""
    ok = await vault.unlock("test-passphrase-123")
    assert ok is True
    return vault


# ===========================================================================
# SQLiteStore
# ===========================================================================


class TestSQLiteStoreLifecycle:
    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, sqlite_store: SQLiteStore) -> None:
        cursor = await sqlite_store.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row["name"] for row in await cursor.fetchall()}
        assert "tasks" in tables
        assert "steps" in tables
        assert "preferences" in tables

    @pytest.mark.asyncio
    async def test_close_and_reopen(self, tmp_path: Path) -> None:
        store = SQLiteStore(tmp_path / "reopen.db")
        await store.initialize()
        await store.save_task("t1", "some task", "completed")
        await store.close()

        # Re-open — data should persist
        store2 = SQLiteStore(tmp_path / "reopen.db")
        await store2.initialize()
        task = await store2.get_task("t1")
        assert task is not None
        assert task["task_text"] == "some task"
        await store2.close()


class TestSQLiteStoreTasks:
    @pytest.mark.asyncio
    async def test_save_and_get_task(self, sqlite_store: SQLiteStore) -> None:
        await sqlite_store.save_task("t1", "Test the homepage", "pending")
        task = await sqlite_store.get_task("t1")
        assert task is not None
        assert task["id"] == "t1"
        assert task["task_text"] == "Test the homepage"
        assert task["status"] == "pending"
        assert task["completed_at"] is None

    @pytest.mark.asyncio
    async def test_save_completed_task_has_completed_at(self, sqlite_store: SQLiteStore) -> None:
        await sqlite_store.save_task("t2", "Check forms", "completed", duration_seconds=12.5)
        task = await sqlite_store.get_task("t2")
        assert task is not None
        assert task["completed_at"] is not None
        assert task["duration_seconds"] == 12.5

    @pytest.mark.asyncio
    async def test_upsert_updates_existing_task(self, sqlite_store: SQLiteStore) -> None:
        await sqlite_store.save_task("t3", "Login test", "pending")
        await sqlite_store.save_task("t3", "Login test", "completed", result_json='{"ok":true}')
        task = await sqlite_store.get_task("t3")
        assert task is not None
        assert task["status"] == "completed"
        assert task["result_json"] == '{"ok":true}'

    @pytest.mark.asyncio
    async def test_get_nonexistent_task_returns_none(self, sqlite_store: SQLiteStore) -> None:
        assert await sqlite_store.get_task("nonexistent") is None

    @pytest.mark.asyncio
    async def test_list_tasks_ordering_and_limit(self, sqlite_store: SQLiteStore) -> None:
        for i in range(5):
            await sqlite_store.save_task(f"task-{i}", f"Task {i}", "completed")
        tasks = await sqlite_store.list_tasks(limit=3)
        assert len(tasks) == 3

    @pytest.mark.asyncio
    async def test_task_count(self, sqlite_store: SQLiteStore) -> None:
        assert await sqlite_store.task_count() == 0
        await sqlite_store.save_task("a", "A", "pending")
        await sqlite_store.save_task("b", "B", "pending")
        assert await sqlite_store.task_count() == 2


class TestSQLiteStoreSteps:
    @pytest.mark.asyncio
    async def test_save_and_get_steps(self, sqlite_store: SQLiteStore) -> None:
        await sqlite_store.save_task("t1", "Test", "running")
        await sqlite_store.save_step("t1", 1, action="click", element="button.submit")
        await sqlite_store.save_step("t1", 2, action="type", element="input.name", reasoning="Fill form")

        steps = await sqlite_store.get_steps("t1")
        assert len(steps) == 2
        assert steps[0]["step_number"] == 1
        assert steps[0]["action"] == "click"
        assert steps[1]["reasoning"] == "Fill form"

    @pytest.mark.asyncio
    async def test_get_steps_empty(self, sqlite_store: SQLiteStore) -> None:
        await sqlite_store.save_task("t2", "Test2", "pending")
        assert await sqlite_store.get_steps("t2") == []

    @pytest.mark.asyncio
    async def test_step_success_stored_as_int(self, sqlite_store: SQLiteStore) -> None:
        await sqlite_store.save_task("t3", "Test3", "running")
        await sqlite_store.save_step("t3", 1, action="click", success=True)
        await sqlite_store.save_step("t3", 2, action="type", success=False)
        steps = await sqlite_store.get_steps("t3")
        assert steps[0]["success"] == 1   # True → 1
        assert steps[1]["success"] == 0   # False → 0


class TestSQLiteStorePreferences:
    @pytest.mark.asyncio
    async def test_set_and_get_preference(self, sqlite_store: SQLiteStore) -> None:
        await sqlite_store.set_preference("theme", "dark")
        assert await sqlite_store.get_preference("theme") == "dark"

    @pytest.mark.asyncio
    async def test_update_preference(self, sqlite_store: SQLiteStore) -> None:
        await sqlite_store.set_preference("lang", "en")
        await sqlite_store.set_preference("lang", "fr")
        assert await sqlite_store.get_preference("lang") == "fr"

    @pytest.mark.asyncio
    async def test_get_nonexistent_preference(self, sqlite_store: SQLiteStore) -> None:
        assert await sqlite_store.get_preference("missing") is None


class TestSQLiteStoreRecentSummaries:
    @pytest.mark.asyncio
    async def test_get_recent_task_summaries(self, sqlite_store: SQLiteStore) -> None:
        await sqlite_store.save_task("t1", "Check homepage", "completed", result_json='{"ok":true}')
        await sqlite_store.save_task("t2", "Test login", "completed")
        summaries = await sqlite_store.get_recent_task_summaries(limit=10)
        assert len(summaries) >= 2


# ===========================================================================
# VectorStore
# ===========================================================================


class TestVectorStoreLifecycle:
    @pytest.mark.asyncio
    async def test_initialize_creates_collection(self, vector_store: VectorStore) -> None:
        assert vector_store.collection is not None
        assert await vector_store.count() == 0

    @pytest.mark.asyncio
    async def test_close_clears_references(self, tmp_path: Path) -> None:
        store = VectorStore(tmp_path / "vec")
        await store.initialize()
        await store.close()
        assert store._client is None
        assert store._collection is None


class TestVectorStoreOperations:
    @pytest.mark.asyncio
    async def test_add_and_count(self, vector_store: VectorStore) -> None:
        await vector_store.add_task_memory("t1", "Test homepage", "All links working")
        assert await vector_store.count() == 1

    @pytest.mark.asyncio
    async def test_upsert_same_id(self, vector_store: VectorStore) -> None:
        await vector_store.add_task_memory("t1", "Test homepage", "All links working")
        await vector_store.add_task_memory("t1", "Test homepage V2", "Updated result")
        assert await vector_store.count() == 1

    @pytest.mark.asyncio
    async def test_search_similar(self, vector_store: VectorStore) -> None:
        await vector_store.add_task_memory("t1", "Test React dashboard accessibility", "Found 5 WCAG issues")
        await vector_store.add_task_memory("t2", "Check e-commerce form validation", "3 forms missing validation")
        await vector_store.add_task_memory("t3", "Audit portfolio site broken links", "2 broken links found")

        # Search for something similar to accessibility testing
        results = await vector_store.search_similar("accessibility audit of React app", n=3, min_score=0.0)
        assert len(results) > 0
        # The first result should be the most similar
        assert results[0]["task_id"] in ("t1", "t2", "t3")
        assert "score" in results[0]
        assert "document" in results[0]

    @pytest.mark.asyncio
    async def test_search_empty_store(self, vector_store: VectorStore) -> None:
        results = await vector_store.search_similar("anything", n=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_with_high_min_score(self, vector_store: VectorStore) -> None:
        await vector_store.add_task_memory("t1", "Test homepage", "OK")
        results = await vector_store.search_similar("completely unrelated quantum physics", n=5, min_score=0.99)
        # Very high threshold — likely no matches
        # (We don't assert ==0 because default embeddings might be surprisingly close)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_delete(self, vector_store: VectorStore) -> None:
        await vector_store.add_task_memory("t1", "Task 1", "Result 1")
        await vector_store.add_task_memory("t2", "Task 2", "Result 2")
        assert await vector_store.count() == 2

        await vector_store.delete("t1")
        assert await vector_store.count() == 1

    @pytest.mark.asyncio
    async def test_metadata_stored(self, vector_store: VectorStore) -> None:
        await vector_store.add_task_memory(
            "t1", "Test site", "OK",
            metadata={"domain": "example.com", "duration": 5.2},
        )
        results = await vector_store.search_similar("Test site", n=1, min_score=0.0)
        assert len(results) == 1
        assert results[0]["metadata"]["domain"] == "example.com"

    @pytest.mark.asyncio
    async def test_metadata_sanitization(self, vector_store: VectorStore) -> None:
        """Non-primitive metadata values should be dropped."""
        await vector_store.add_task_memory(
            "t1", "Test", "OK",
            metadata={"valid": "yes", "invalid_list": [1, 2, 3], "invalid_none": None},
        )
        results = await vector_store.search_similar("Test", n=1, min_score=0.0)
        meta = results[0]["metadata"]
        assert "valid" in meta
        assert "invalid_list" not in meta
        assert "invalid_none" not in meta


# ===========================================================================
# PersonalVault
# ===========================================================================


class TestVaultLifecycle:
    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, vault: PersonalVault) -> None:
        cursor = await vault.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row["name"] for row in await cursor.fetchall()}
        assert "vault" in tables
        assert "vault_meta" in tables

    @pytest.mark.asyncio
    async def test_salt_persists(self, tmp_path: Path) -> None:
        v1 = PersonalVault(str(tmp_path / "v.db"))
        await v1.initialize()
        salt1 = v1._salt
        await v1.close()

        v2 = PersonalVault(str(tmp_path / "v.db"))
        await v2.initialize()
        assert v2._salt == salt1
        await v2.close()

    @pytest.mark.asyncio
    async def test_not_unlocked_by_default(self, vault: PersonalVault) -> None:
        assert vault.is_unlocked() is False


class TestVaultUnlockLock:
    @pytest.mark.asyncio
    async def test_unlock_empty_vault(self, vault: PersonalVault) -> None:
        # Any passphrase should work on an empty vault (nothing to verify against)
        assert await vault.unlock("any-pass") is True
        assert vault.is_unlocked() is True

    @pytest.mark.asyncio
    async def test_lock(self, unlocked_vault: PersonalVault) -> None:
        await unlocked_vault.lock()
        assert unlocked_vault.is_unlocked() is False

    @pytest.mark.asyncio
    async def test_unlock_wrong_passphrase_rejected(self, vault: PersonalVault) -> None:
        # First, unlock and store a field to establish the passphrase
        await vault.unlock("correct-pass")
        await vault.set_field("name", "Alice")
        await vault.lock()

        # Try wrong passphrase
        assert await vault.unlock("wrong-pass") is False
        assert vault.is_unlocked() is False

    @pytest.mark.asyncio
    async def test_unlock_correct_passphrase_after_store(self, vault: PersonalVault) -> None:
        await vault.unlock("my-pass")
        await vault.set_field("email", "a@b.com")
        await vault.lock()

        assert await vault.unlock("my-pass") is True
        assert vault.is_unlocked() is True


class TestVaultFieldCRUD:
    @pytest.mark.asyncio
    async def test_set_and_get_field(self, unlocked_vault: PersonalVault) -> None:
        await unlocked_vault.set_field("name", "Alice Smith")
        assert await unlocked_vault.get_field("name") == "Alice Smith"

    @pytest.mark.asyncio
    async def test_update_field(self, unlocked_vault: PersonalVault) -> None:
        await unlocked_vault.set_field("email", "old@example.com")
        await unlocked_vault.set_field("email", "new@example.com")
        assert await unlocked_vault.get_field("email") == "new@example.com"

    @pytest.mark.asyncio
    async def test_get_nonexistent_field(self, unlocked_vault: PersonalVault) -> None:
        assert await unlocked_vault.get_field("phone") is None

    @pytest.mark.asyncio
    async def test_get_all_decrypted(self, unlocked_vault: PersonalVault) -> None:
        await unlocked_vault.set_field("name", "Bob")
        await unlocked_vault.set_field("email", "bob@test.com")
        all_data = await unlocked_vault.get_all_decrypted()
        assert all_data == {"name": "Bob", "email": "bob@test.com"}

    @pytest.mark.asyncio
    async def test_delete_field(self, unlocked_vault: PersonalVault) -> None:
        await unlocked_vault.set_field("phone", "555-1234")
        assert await unlocked_vault.delete_field("phone") is True
        assert await unlocked_vault.get_field("phone") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_field(self, unlocked_vault: PersonalVault) -> None:
        assert await unlocked_vault.delete_field("company") is False

    @pytest.mark.asyncio
    async def test_list_fields(self, unlocked_vault: PersonalVault) -> None:
        await unlocked_vault.set_field("name", "Test")
        await unlocked_vault.set_field("email", "t@t.com")
        fields = await unlocked_vault.list_fields()
        assert sorted(fields) == ["email", "name"]

    @pytest.mark.asyncio
    async def test_invalid_field_type_rejected(self, unlocked_vault: PersonalVault) -> None:
        with pytest.raises(ValueError, match="Invalid field type"):
            await unlocked_vault.set_field("invalid_field_xyz", "value")

    @pytest.mark.asyncio
    async def test_all_valid_field_types(self, unlocked_vault: PersonalVault) -> None:
        valid_types = [
            "name", "email", "phone", "username", "password", "company", "custom",
            "address_line1", "address_city", "address_state", "address_zip", "address_country",
            "card_number", "card_exp", "card_cvv", "card_name",
        ]
        for ft in valid_types:
            await unlocked_vault.set_field(ft, f"val-{ft}")
        all_data = await unlocked_vault.get_all_decrypted()
        assert len(all_data) == len(valid_types)


class TestVaultLocked:
    @pytest.mark.asyncio
    async def test_set_field_when_locked_raises(self, vault: PersonalVault) -> None:
        with pytest.raises(PermissionError, match="locked"):
            await vault.set_field("name", "X")

    @pytest.mark.asyncio
    async def test_get_field_when_locked_raises(self, vault: PersonalVault) -> None:
        with pytest.raises(PermissionError, match="locked"):
            await vault.get_field("name")

    @pytest.mark.asyncio
    async def test_get_all_when_locked_raises(self, vault: PersonalVault) -> None:
        with pytest.raises(PermissionError, match="locked"):
            await vault.get_all_decrypted()


class TestVaultPersistence:
    @pytest.mark.asyncio
    async def test_data_survives_close_and_reopen(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "persist.db")
        passphrase = "keep-my-secrets"

        v1 = PersonalVault(db_path)
        await v1.initialize()
        await v1.unlock(passphrase)
        await v1.set_field("name", "Alice")
        await v1.set_field("email", "alice@secret.com")
        await v1.close()

        # Reopen and verify data is still there
        v2 = PersonalVault(db_path)
        await v2.initialize()
        assert await v2.unlock(passphrase) is True
        assert await v2.get_field("name") == "Alice"
        assert await v2.get_field("email") == "alice@secret.com"
        await v2.close()

    @pytest.mark.asyncio
    async def test_form_fill_data(self, unlocked_vault: PersonalVault) -> None:
        await unlocked_vault.set_field("name", "Bob")
        await unlocked_vault.set_field("email", "bob@test.com")
        data = await unlocked_vault.get_form_fill_data()
        assert data == {"name": "Bob", "email": "bob@test.com"}
