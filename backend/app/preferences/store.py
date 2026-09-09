import json
import logging
from datetime import UTC, datetime

from sqlalchemy import text

from app.config import settings
from app.db.client import get_session
from app.models.preferences import PreferencesUpdate, UserPreferences

logger = logging.getLogger(__name__)


async def get_preferences() -> UserPreferences:
    async with get_session() as session:
        result = await session.execute(
            text("SELECT * FROM user_preferences WHERE user_id = :uid"),
            {"uid": settings.user_id},
        )
        row = result.mappings().first()

    if not row:
        raise RuntimeError("User preferences row not found — run migration 0002")

    data = dict(row)
    data["extra"] = data.get("extra") or {}
    return UserPreferences(**data)


async def update_preferences(patch: PreferencesUpdate) -> UserPreferences:
    updates = patch.model_dump(exclude_none=True)
    if not updates:
        return await get_preferences()

    updates["updated_at"] = datetime.now(UTC).isoformat()

    if "extra" in updates:
        updates["extra"] = json.dumps(updates["extra"])

    if "learning_focus_areas" in updates:
        updates["learning_focus_areas"] = list(updates["learning_focus_areas"])
    if "life_focus_areas" in updates:
        updates["life_focus_areas"] = list(updates["life_focus_areas"])

    assignments = ", ".join(f"{k} = :{k}" for k in updates)
    updates["_uid"] = settings.user_id

    async with get_session() as session:
        await session.execute(
            text(f"UPDATE user_preferences SET {assignments} WHERE user_id = :_uid"),  # noqa: S608
            updates,
        )

    logger.info("Updated user preferences: %s", list(patch.model_dump(exclude_none=True).keys()))
    return await get_preferences()
