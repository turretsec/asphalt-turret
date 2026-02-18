from dataclasses import dataclass
from typing import Any

from asphalt_turret_engine.adapters.json_settings_store import JsonSettingsStore
from asphalt_turret_engine.config.bootstrap_settings import BootstrapSettings
from asphalt_turret_engine.config.user_settings import UserSettings, UserSettingsPatch

RESTART_KEYS = {"repository_dir", "incoming_dir"}

@dataclass
class SettingsUpdateResult:
    changed_keys: list[str]
    restart_required: bool

class SettingsService:
    def __init__(self, bootstrap: BootstrapSettings):
        self.bootstrap = bootstrap
        self.store = JsonSettingsStore(bootstrap.user_settings_path)
        self.user = self.store.load()

    def effective(self) -> dict[str, Any]:
        # Merge defaults + derived paths + user overrides
        base = self.bootstrap.base_dir
        probe_version = self.bootstrap.probe_version

        repository_dir = self.user.repository_dir or (base / "data" / "repository")
        incoming_dir = self.user.incoming_dir or (base / "data" / "incoming")
        thumbnails_dir = base / "data" / "thumbnails"

        return {
            "base_dir": base,
            "database_url": self.bootstrap.database_url,
            "probe_version": probe_version,
            "ffprobe_timeout_s": self.user.ffprobe_timeout_s,
            "thumbnail_width": self.user.thumbnail_width,
            "thumbnail_height": self.user.thumbnail_height,
            "thumbnail_quality": self.user.thumbnail_quality,
            "repository_dir": repository_dir,
            "incoming_dir": incoming_dir,
            "thumbnails_dir": thumbnails_dir,
            "ffprobe_path": base / "bin" / "ffprobe.exe",
            "ffmpeg_path": base / "bin" / "ffmpeg.exe",
        }

    def update(self, patch: UserSettingsPatch) -> SettingsUpdateResult:
        data = patch.model_dump(exclude_unset=True)
        changed: list[str] = []

        new_user = self.user.model_copy(deep=True)
        for k, v in data.items():
            if getattr(new_user, k) != v:
                setattr(new_user, k, v)
                changed.append(k)

        if not changed:
            return SettingsUpdateResult(changed_keys=[], restart_required=False)

        # Persist immediately (even if restart required)
        self.user = new_user
        self.store.save(self.user)

        restart_required = any(k in RESTART_KEYS for k in changed)

        # Optional: do “instant apply” side-effects here for specific keys
        # e.g., if thumbnails change: mark thumbnail cache invalidation flag

        return SettingsUpdateResult(changed_keys=changed, restart_required=restart_required)