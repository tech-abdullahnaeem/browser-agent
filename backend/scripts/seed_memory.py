#!/usr/bin/env python3
"""Seed the ChromaDB vector store with sample task memories.

Usage::

    uv run python scripts/seed_memory.py
"""

import asyncio
import sys
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import get_settings
from src.memory.vector_store import VectorStore

SAMPLE_MEMORIES = [
    {
        "task_id": "seed-001",
        "task": "Run a full accessibility audit on a React dashboard app",
        "result": "Found 12 issues: 3 images missing alt text, 2 form inputs without labels, "
                  "heading hierarchy skipped from H1 to H3, 4 buttons without accessible names, "
                  "no skip navigation link. Score: 6/10.",
        "metadata": {"status": "completed", "domain": "localhost:3000", "step_count": 8, "duration": 45.0},
    },
    {
        "task_id": "seed-002",
        "task": "Test all forms on an e-commerce checkout page",
        "result": "Tested 3 forms: shipping form (6 fields, 2 missing labels, autocomplete missing), "
                  "payment form (4 fields, card validation works, CVV accepts letters — bug), "
                  "promo code form (submits but shows no feedback — bug). 3 issues found.",
        "metadata": {"status": "completed", "domain": "localhost:3000", "step_count": 15, "duration": 92.0},
    },
    {
        "task_id": "seed-003",
        "task": "Check for broken links and console errors on a portfolio website",
        "result": "Scanned 45 links: 2 broken (404 on /projects/old-project and /blog/draft-post), "
                  "3 external links timing out. Console: 1 TypeError in main.js line 42, "
                  "2 failed resource loads (missing favicon.ico, font file 404).",
        "metadata": {"status": "completed", "domain": "localhost:5173", "step_count": 6, "duration": 38.0},
    },
    {
        "task_id": "seed-004",
        "task": "Full QA audit of an AI-generated landing page",
        "result": "Crawled 5 pages. Issues: homepage has lorem ipsum placeholder text (HIGH), "
                  "contact form submits but shows no confirmation (HIGH), /about page returns 404 (CRITICAL), "
                  "mobile nav hamburger doesn't toggle (HIGH), 2 images are broken placeholder URLs (MEDIUM). "
                  "Performance OK (1.2s load). SEO: missing meta description on 3 pages.",
        "metadata": {"status": "completed", "domain": "localhost:3000", "step_count": 22, "duration": 156.0},
    },
    {
        "task_id": "seed-005",
        "task": "Test user signup and login flow on a SaaS app",
        "result": "Signup: form accepts empty name (bug), email validation works, password requires 8+ chars — good. "
                  "After signup, redirects to dashboard correctly. Login: correct credentials work, "
                  "wrong password shows error message. Logout: works but doesn't clear session cookie (security concern). "
                  "Password reset link returns 500 error (CRITICAL).",
        "metadata": {"status": "completed", "domain": "localhost:3000", "step_count": 18, "duration": 120.0},
    },
]


async def main() -> None:
    s = get_settings()
    store = VectorStore(s.get_chromadb_path())
    await store.initialize()

    print(f"Seeding {len(SAMPLE_MEMORIES)} memories into ChromaDB at {s.get_chromadb_path()}")

    for mem in SAMPLE_MEMORIES:
        await store.add_task_memory(
            task_id=mem["task_id"],
            task_text=mem["task"],
            result_summary=mem["result"],
            metadata=mem["metadata"],
        )
        print(f"  ✓ {mem['task_id']}: {mem['task'][:60]}...")

    count = await store.count()
    print(f"\nDone. Total memories in store: {count}")

    # Test a similarity search
    print("\n--- Testing similarity search ---")
    results = await store.search_similar("audit accessibility on a web app", n=3)
    for r in results:
        print(f"  [{r['score']:.3f}] {r['document'][:80]}...")

    await store.close()


if __name__ == "__main__":
    asyncio.run(main())
