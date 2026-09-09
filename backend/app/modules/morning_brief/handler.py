import logging

from app.models.orchestrator import Intent, ModuleRequest, ModuleResponse
from app.modules.base import ModuleHandler
from app.modules.morning_brief.aggregator import aggregate_brief_data
from app.modules.morning_brief.formatter import format_brief
from app.modules.morning_brief.scheduler import get_next_run_time, start_scheduler

logger = logging.getLogger(__name__)


class MorningBriefModule(ModuleHandler):
    @property
    def name(self) -> str:
        return "morning_brief"

    @property
    def supported_intents(self) -> list[Intent]:
        return [Intent.BRIEF_GENERATE, Intent.BRIEF_CONFIGURE]

    async def handle(self, request: ModuleRequest) -> ModuleResponse:
        if request.intent == Intent.BRIEF_GENERATE:
            return await self._handle_generate(request)
        if request.intent == Intent.BRIEF_CONFIGURE:
            return await self._handle_configure(request)
        return ModuleResponse(content="I couldn't handle that brief request.")

    async def _handle_generate(self, request: ModuleRequest) -> ModuleResponse:
        prefs: dict = {}
        try:
            from app.preferences.store import get_preferences
            prefs_obj = await get_preferences()
            prefs = prefs_obj.model_dump()
        except Exception:
            pass

        data = await aggregate_brief_data(prefs=prefs)
        brief = await format_brief(data)

        next_run = get_next_run_time()
        footer = f"\n\n_Next scheduled brief: {next_run}_" if next_run else ""

        return ModuleResponse(
            content=brief + footer,
            structured=data,
        )

    async def _handle_configure(self, request: ModuleRequest) -> ModuleResponse:
        from app.models.preferences import PreferencesUpdate
        from app.preferences.store import update_preferences

        patch = PreferencesUpdate(
            brief_cron=request.parameters.get("cron"),
            brief_timezone=request.parameters.get("timezone"),
            brief_include_learning=request.parameters.get("include_learning"),
            brief_include_life=request.parameters.get("include_life"),
            brief_tone=request.parameters.get("tone"),
        )
        prefs = await update_preferences(patch)
        await start_scheduler()

        return ModuleResponse(
            content=(
                f"Morning brief updated:\n"
                f"- Schedule: `{prefs.brief_cron}` ({prefs.brief_timezone})\n"
                f"- Learning nudge: {'on' if prefs.brief_include_learning else 'off'}\n"
                f"- Life nudge: {'on' if prefs.brief_include_life else 'off'}\n"
                f"- Tone: {prefs.brief_tone}"
            ),
        )
