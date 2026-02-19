from pathlib import Path
from functools import lru_cache

from asphalt_turret_engine.config.bootstrap_settings import BootstrapSettings
from asphalt_turret_engine.services.settings_service import SettingsService

bootstrap = BootstrapSettings()

@lru_cache(maxsize=1)
def get_settings_service() -> SettingsService:
    return SettingsService(bootstrap)

class SettingsFacade:
    def effective(self) -> dict:
        return get_settings_service().effective()

    def ensure_directories(self):
        eff = self.effective()
        Path(eff["base_dir"]).mkdir(parents=True, exist_ok=True)
        Path(eff["repository_dir"]).mkdir(parents=True, exist_ok=True)
        Path(eff["incoming_dir"]).mkdir(parents=True, exist_ok=True)
        Path(eff["thumbnails_dir"]).mkdir(parents=True, exist_ok=True)

    def __getattr__(self, name: str):
        eff = self.effective()
        if name in eff:
            return eff[name]
        raise AttributeError(name)

settings = SettingsFacade()