#!/usr/bin/env python3
"""Seed baseline memory entries: people, projects, preferences.

Writes through app.memory.store, so each entry gets a Titan embedding and lands
in pgvector exactly as a runtime memory write would. Re-running is safe —
entries that already exist are skipped.

Usage: python scripts/seed_memory.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


SEED_ENTRIES = [
    # People
    {
        "category": "person",
        "subject": "Henry",
        "content": "Henry is a team member on the AyaData AI Solutions team. Works closely with Phil on AI projects.",
    },
    {
        "category": "person",
        "subject": "Elton",
        "content": "Elton is a team member on the AyaData AI Solutions team. Key collaborator for project delivery.",
    },
    # Projects
    {
        "category": "project",
        "subject": "AyaData Logistics",
        "content": "AyaData Logistics is an active project at AyaData. Involves logistics optimization using AI.",
    },
    {
        "category": "project",
        "subject": "TranslateGemma",
        "content": "TranslateGemma is an active AI translation project at AyaData.",
    },
    # Preferences
    {
        "category": "preference",
        "subject": "email tone",
        "content": (
            "Phil prefers a professional but approachable tone in emails. "
            "Formal for external clients, casual for internal team."
        ),
    },
    {
        "category": "preference",
        "subject": "morning brief",
        "content": (
            "Phil's morning brief runs at 7AM WAT. He wants: top 3 priorities, "
            "emails needing reply, today's tasks, meeting follow-ups."
        ),
    },
]


async def _already_seeded(category: str, subject: str) -> bool:
    from app.db.client import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(
            text(
                "SELECT 1 FROM memory_entries "
                "WHERE category = :category AND subject = :subject LIMIT 1"
            ),
            {"category": category, "subject": subject},
        )
        return result.first() is not None


async def main() -> None:
    # Imported here so the sys.path insert above is in effect.
    from app.memory.store import save_entry
    from app.models.memory import MemoryCategory

    created = 0
    skipped = 0

    for entry in SEED_ENTRIES:
        category = MemoryCategory(entry["category"])
        subject = entry["subject"]

        if await _already_seeded(category.value, subject):
            print(f"Skipped (exists): [{category.value}] {subject}")
            skipped += 1
            continue

        await save_entry(
            category=category,
            subject=subject,
            content=entry["content"],
            source_module="seed",
        )
        print(f"Seeded: [{category.value}] {subject}")
        created += 1

    print(f"\n{created} entries seeded, {skipped} already present.")


if __name__ == "__main__":
    asyncio.run(main())
