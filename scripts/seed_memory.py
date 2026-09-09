#!/usr/bin/env python3
"""Seed initial memory entries: contacts, projects, preferences.

Run once after setting up Supabase to populate baseline context.
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
        "content": "Phil prefers a professional but approachable tone in emails. Formal for external clients, casual for internal team.",
    },
    {
        "category": "preference",
        "subject": "morning brief",
        "content": "Phil's morning brief runs at 7AM WAT. He wants: top 3 priorities, emails needing reply, today's tasks, meeting follow-ups.",
    },
]


async def main() -> None:
    from app.memory.embeddings import generate_embedding
    from app.config import settings
    from supabase import create_client

    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)

    for entry in SEED_ENTRIES:
        embedding = await generate_embedding(entry["content"])
        supabase.table("memory_entries").insert(
            {**entry, "embedding": embedding, "source_module": "seed"}
        ).execute()
        print(f"Seeded: [{entry['category']}] {entry['subject']}")

    print(f"\nSeeded {len(SEED_ENTRIES)} memory entries.")


if __name__ == "__main__":
    asyncio.run(main())
