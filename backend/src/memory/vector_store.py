"""Semantic vector memory using ChromaDB (embedded mode).

Stores task descriptions and results as embeddings, enabling similarity
search so the agent can learn from past QA audits.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

from src.utils.logging import get_logger

logger = get_logger(__name__)

_COLLECTION_NAME = "task_memory"


class VectorStore:
    """Wrapper around ChromaDB for semantic task memory."""

    def __init__(self, persist_dir: str | Path) -> None:
        self._persist_dir = str(persist_dir)
        self._client: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None

    # -- lifecycle ---------------------------------------------------------

    async def initialize(self) -> None:
        """Create or open the ChromaDB persistent store and collection.

        ChromaDB operations are synchronous but fast; we keep the async
        interface for consistency with the rest of the memory subsystem.
        """
        Path(self._persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=self._persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        count = self._collection.count()
        logger.info("vector_store_initialized", persist_dir=self._persist_dir, documents=count)

    async def close(self) -> None:
        """No-op for the embedded client (just resets references)."""
        self._client = None
        self._collection = None

    @property
    def collection(self) -> chromadb.Collection:
        assert self._collection is not None, "VectorStore not initialized"
        return self._collection

    # -- write -------------------------------------------------------------

    async def add_task_memory(
        self,
        task_id: str,
        task_text: str,
        result_summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store a completed task as a searchable document.

        The document is ``"{task_text} → {result_summary}"`` so that both
        the task intent and outcome contribute to embedding similarity.
        """
        document = f"{task_text} → {result_summary}"
        meta = {
            "task_id": task_id,
            **(metadata or {}),
        }
        # Ensure metadata values are str/int/float/bool only (ChromaDB constraint)
        sanitized_meta = {
            k: v for k, v in meta.items()
            if isinstance(v, (str, int, float, bool))
        }
        self.collection.upsert(
            ids=[task_id],
            documents=[document[:8000]],  # ChromaDB has document size limits
            metadatas=[sanitized_meta],
        )
        logger.debug("vector_memory_added", task_id=task_id)

    # -- read --------------------------------------------------------------

    async def search_similar(
        self,
        query: str,
        n: int = 5,
        min_score: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Find the *n* most similar past tasks by embedding distance.

        Returns dicts with keys ``task_id``, ``document``, ``score``, ``metadata``.
        Only results with cosine similarity >= *min_score* are returned.
        """
        if self.collection.count() == 0:
            return []

        # ChromaDB returns distances (lower = more similar for cosine)
        actual_n = min(n, self.collection.count())
        results = self.collection.query(
            query_texts=[query],
            n_results=actual_n,
            include=["documents", "metadatas", "distances"],
        )

        matches = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        for i, doc_id in enumerate(ids):
            # ChromaDB cosine distance = 1 - cosine_similarity
            similarity = 1.0 - dists[i]
            if similarity >= min_score:
                matches.append({
                    "task_id": doc_id,
                    "document": docs[i] if docs else "",
                    "score": round(similarity, 3),
                    "metadata": metas[i] if metas else {},
                })

        return matches

    async def count(self) -> int:
        """Return the total number of stored task memories."""
        return self.collection.count()

    async def delete(self, task_id: str) -> None:
        """Remove a specific task memory."""
        self.collection.delete(ids=[task_id])
