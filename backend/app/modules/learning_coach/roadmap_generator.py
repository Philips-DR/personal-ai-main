"""Generate and persist learning roadmaps."""

import logging

from app.claude import invoke_claude_json
from app.memory.store import save_entry
from app.models.memory import MemoryCategory
from app.modules.learning_coach.coach_prompts import roadmap_system

logger = logging.getLogger(__name__)


async def generate_roadmap(
    goal: str, experience_level: str, time_per_day_minutes: int, duration_weeks: int
) -> dict:
    """Generate a structured learning roadmap via Claude and persist it to memory."""

    user_prompt = (
        f"Goal: {goal}\n"
        f"My experience level: {experience_level}\n"
        f"Daily study time: {time_per_day_minutes} minutes\n"
        f"Duration: {duration_weeks} weeks\n\n"
        "Generate a detailed, actionable roadmap."
    )

    roadmap = await invoke_claude_json(
        system_prompt=roadmap_system(),
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=4096,
        temperature=0.3,
    )

    content = (
        f"Learning Roadmap: {goal}\n"
        f"Duration: {roadmap.get('duration_weeks', duration_weeks)} weeks, "
        f"{roadmap.get('daily_minutes', time_per_day_minutes)} min/day\n\n"
        f"Milestones:\n"
        + "\n".join(
            f"Week {m['week']}: {m['title']} — {', '.join(m.get('topics', []))}"
            for m in roadmap.get("milestones", [])
        )
    )

    await save_entry(
        category=MemoryCategory.LEARNING_ROADMAP,
        subject=f"Roadmap: {goal}",
        content=content,
        source_module="learning_coach",
        metadata=roadmap,
    )

    logger.info("Generated and stored learning roadmap for: %s", goal)
    return roadmap
