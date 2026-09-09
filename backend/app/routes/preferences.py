from fastapi import APIRouter

from app.models.preferences import PreferencesUpdate, UserPreferences
from app.preferences.store import get_preferences, update_preferences

router = APIRouter()


@router.get("", response_model=UserPreferences)
async def read_preferences() -> UserPreferences:
    return await get_preferences()


@router.patch("", response_model=UserPreferences)
async def patch_preferences(update: PreferencesUpdate) -> UserPreferences:
    return await update_preferences(update)
