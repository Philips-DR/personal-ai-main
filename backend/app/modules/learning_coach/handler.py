"""Learning Coach module — roadmaps, coaching, life suggestions."""

import logging

from app.claude import invoke_claude
from app.config import settings
from app.memory.store import get_by_category, save_entry, search_similar
from app.models.memory import MemoryCategory
from app.models.orchestrator import Intent, ModuleRequest, ModuleResponse
from app.modules.base import ModuleHandler
from app.modules.learning_coach.coach_prompts import coaching_system, life_system, review_system

logger = logging.getLogger(__name__)

_MAX_TOKENS_REVIEW = 2048
_MAX_TOKENS_COACHING = 2048
_MAX_TOKENS_LIFE = 1024
_TEMPERATURE_REVIEW = 0.5
_TEMPERATURE_COACHING = 0.6
_TEMPERATURE_LIFE = 0.7

_SUBJECT_MAX = 60    # chars of user message used as memory subject
_RESPONSE_MAX = 500  # chars of response stored in memory


class LearningCoachModule(ModuleHandler):
    @property
    def name(self) -> str:
        return "learning_coach"

    @property
    def supported_intents(self) -> list[Intent]:
        return [
            Intent.LEARNING_PLAN,
            Intent.LEARNING_REVIEW,
            Intent.LEARNING_PROMPT,
            Intent.LIFE_SUGGEST,
        ]

    async def handle(self, request: ModuleRequest) -> ModuleResponse:
        intent = request.intent

        if intent == Intent.LEARNING_PLAN:
            return await self._learning_plan(request)
        if intent == Intent.LEARNING_REVIEW:
            return await self._learning_review(request)
        if intent == Intent.LEARNING_PROMPT:
            return await self._learning_prompt(request)
        if intent == Intent.LIFE_SUGGEST:
            return await self._life_suggest(request)

        return ModuleResponse(content="Unsupported learning intent.")

    async def _learning_plan(self, request: ModuleRequest) -> ModuleResponse:
        from app.modules.learning_coach.roadmap_generator import generate_roadmap

        goal = request.parameters.get("goal") or request.user_message
        experience_level = request.parameters.get("experience_level", settings.default_experience_level)
        daily_minutes = int(request.parameters.get("daily_minutes", settings.default_daily_minutes))
        weeks = int(request.parameters.get("duration_weeks", settings.default_duration_weeks))

        roadmap = await generate_roadmap(goal, experience_level, daily_minutes, weeks)

        milestones_md = "\n".join(
            f"**Week {m['week']}: {m['title']}**\n"
            + "\n".join(f"  - {t}" for t in m.get("topics", []))
            + (f"\n  - Project: *{m['project']}*" if m.get("project") else "")
            for m in roadmap.get("milestones", [])
        )

        return ModuleResponse(
            content=(
                f"## Learning Roadmap: {roadmap.get('goal', goal)}\n\n"
                f"**Duration:** {roadmap.get('duration_weeks', weeks)} weeks | "
                f"**Daily:** {roadmap.get('daily_minutes', daily_minutes)} min\n\n"
                f"**Prerequisites:** {', '.join(roadmap.get('prerequisites', [])) or 'None'}\n\n"
                f"### Milestones\n{milestones_md}\n\n"
                f"**Success metrics:** {', '.join(roadmap.get('success_metrics', []))}\n\n"
                "_Roadmap saved to memory. I'll reference it in your morning brief._"
            ),
            structured=roadmap,
            memory_updates=[{"category": "learning_roadmap", "subject": f"Roadmap: {goal}"}],
        )

    async def _learning_review(self, request: ModuleRequest) -> ModuleResponse:
        roadmaps = await get_by_category(MemoryCategory.LEARNING_ROADMAP)
        habits = await get_by_category(MemoryCategory.HABIT)

        context_parts = []
        if roadmaps:
            roadmap_text = "\n".join(r.content[:300] for r in roadmaps[:settings.brief_roadmaps_limit])
            context_parts.append(f"Current roadmaps:\n{roadmap_text}")
        if habits:
            habit_text = "\n".join(h.content for h in habits[:settings.brief_habits_limit])
            context_parts.append(f"Current habits:\n{habit_text}")

        context = "\n\n".join(context_parts) if context_parts else "No roadmaps or habits stored yet."

        review = await invoke_claude(
            system_prompt=review_system(),
            messages=[{"role": "user", "content": f"Context:\n{context}\n\nUser: {request.user_message}"}],
            max_tokens=_MAX_TOKENS_REVIEW,
            temperature=_TEMPERATURE_REVIEW,
        )

        return ModuleResponse(content=review)

    async def _learning_prompt(self, request: ModuleRequest) -> ModuleResponse:
        similar = await search_similar(
            request.user_message, limit=settings.max_memory_entries_per_query // 3,
            category=MemoryCategory.LEARNING_ROADMAP,
        )
        context = "\n\n".join(e.content for e in similar) if similar else ""

        history = request.conversation_history[-settings.conversation_history_limit:]
        messages_payload = [{"role": m.role, "content": m.content} for m in history]
        messages_payload.append({"role": "user", "content": request.user_message})

        system = coaching_system()
        if context:
            system += f"\n\nRelevant roadmap context:\n{context}"

        response = await invoke_claude(
            system_prompt=system,
            messages=messages_payload,
            max_tokens=_MAX_TOKENS_COACHING,
            temperature=_TEMPERATURE_COACHING,
        )

        await save_entry(
            category=MemoryCategory.INTEREST,
            subject=f"Study session: {request.user_message[:_SUBJECT_MAX]}",
            content=f"Q: {request.user_message}\nA: {response[:_RESPONSE_MAX]}",
            source_module="learning_coach",
        )

        return ModuleResponse(content=response)

    async def _life_suggest(self, request: ModuleRequest) -> ModuleResponse:
        interests = await get_by_category(MemoryCategory.INTEREST)
        context = "\n".join(
            i.content[:200] for i in interests[:settings.brief_interests_limit]
        ) if interests else ""

        system = life_system()
        if context:
            system += f"\n\nPast interests and context:\n{context}"

        response = await invoke_claude(
            system_prompt=system,
            messages=[{"role": "user", "content": request.user_message}],
            max_tokens=_MAX_TOKENS_LIFE,
            temperature=_TEMPERATURE_LIFE,
        )

        return ModuleResponse(content=response)
