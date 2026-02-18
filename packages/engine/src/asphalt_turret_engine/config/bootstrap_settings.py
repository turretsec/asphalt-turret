from pathlib import Path
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

def get_base_dir() -> Path:
    return (Path(os.environ.get("LOCALAPPDATA", "~")) / "asphalt-turret").expanduser()


class BootstrapSettings(BaseSettings):
    base_dir: Path = get_base_dir()
    probe_version: int = 1

    model_config = SettingsConfigDict(
        env_prefix="ASPHALT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def config_dir(self) -> Path:
        return self.base_dir / "config"

    @property
    def user_settings_path(self) -> Path:
        return self.config_dir / "user_settings.json"

    @property
    def database_url(self) -> str:
        db_path = self.base_dir / "asphalt-turret.db"
        return f"sqlite:///{db_path}"