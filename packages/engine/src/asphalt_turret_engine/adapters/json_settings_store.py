import json
from pathlib import Path
from datetime import datetime

from asphalt_turret_engine.config.user_settings import UserSettings

class JsonSettingsStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self, create_if_missing: bool = True) -> "UserSettings":
        # Ensure folder exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # If missing, return defaults and optionally materialize them to disk
        if not self.path.exists():
            settings = UserSettings()
            if create_if_missing:
                self.save(settings)
            return settings

        # If present, try to parse/validate
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            settings = UserSettings.model_validate(data)
            return settings
        except Exception:
            # Corrupt or incompatible: quarantine + recreate defaults
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            bad = self.path.with_suffix(f".bad-{ts}.json")
            try:
                self.path.replace(bad)
            except Exception:
                pass

            settings = UserSettings()
            if create_if_missing:
                self.save(settings)
            return settings

    def save(self, settings: "UserSettings") -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
        tmp.replace(self.path)  # atomic on Windows