from re import U
from fastapi import APIRouter, Depends
from fastapi.background import P

from asphalt_turret_engine.config.user_settings import UserSettingsPatch
from asphalt_turret_engine.services.settings_service import SettingsService
from asphalt_turret_engine.config.bootstrap_settings import BootstrapSettings

router = APIRouter(prefix="/api/settings", tags=["settings"])

def get_settings_service() -> SettingsService:
    return SettingsService(BootstrapSettings())

@router.get("")
def get_settings(service: SettingsService = Depends(get_settings_service)):
    """
    Get effective settings (merged defaults + user overrides).
    """
    return {
        "user": service.user,
        "effective": service.effective(),
        "schema": service.user.model_json_schema(),
    }

@router.patch("")
def patch_settings(
    patch: UserSettingsPatch,
    service: SettingsService = Depends(get_settings_service),
):
    """
    Patch user settings.
    """
    result = service.update(patch)
    return {
        "changed_keys": result.changed_keys,
        "restart_required": result.restart_required,
        "user": service.user,
        "effective": service.effective(),
    }
