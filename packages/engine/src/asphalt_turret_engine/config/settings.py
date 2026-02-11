from pathlib import Path
from pydantic_settings import BaseSettings
import os
import sys

def get_base_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", "~")) / "asphalt-turret"
    return base.expanduser()

class Settings(BaseSettings):
    # Base directory
    base_dir: Path = get_base_dir()


    # FFProbe configuration
    ffprobe_timeout_s: int = 30    # Timeout for probing
    
    # Probe version tracking (increment when probe logic changes)
    probe_version: int = 1

    # FFProbe executable path
    @property
    def ffprobe_path(self) -> str:
        """Get the ffprobe executable path."""
        path = self.base_dir / "bin" / "ffprobe.exe"
        return str(path)

    # Database
    @property
    def database_url(self) -> str:
        """SQLite database path."""
        db_path = self.base_dir / "asphalt-turret.db"
        return f"sqlite:///{db_path}"
    
    # Data directories
    @property
    def repository_dir(self) -> Path:
        """Repository for organized clips."""
        return self.base_dir / "data" / "repository"
    
    @property
    def incoming_dir(self) -> Path:
        """Staging area for imports."""
        return self.base_dir / "data" / "incoming"
    
    # Optional: Allow override via environment variable
    class Config:
        env_prefix = "ASPHALT_"
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def ensure_directories(self):
        """Create all required directories if they don't exist."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.repository_dir.mkdir(parents=True, exist_ok=True)
        self.incoming_dir.mkdir(parents=True, exist_ok=True)

settings = Settings()