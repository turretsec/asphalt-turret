from re import U
from fastapi import APIRouter, Depends
from fastapi.background import P
from pathlib import Path

from asphalt_turret_engine.config.user_settings import UserSettingsPatch
from asphalt_turret_engine.services.settings_service import SettingsService
from asphalt_turret_engine.config.bootstrap_settings import BootstrapSettings

router = APIRouter(prefix="/api/settings", tags=["settings"])

def get_settings_service() -> SettingsService:
    return SettingsService(BootstrapSettings())

def _jsonify(v):
    return str(v) if isinstance(v, Path) else v

@router.get("")
def get_settings(service: SettingsService = Depends(get_settings_service)):
    """
    Get effective settings (merged defaults + user overrides).
    """
    eff = service.effective()
    return {
        "user": service.user.model_dump(),
        "effective": {k: _jsonify(v) for k, v in eff.items()},
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
        "effective": {k: _jsonify(v) for k, v in service.effective().items()},
    }
