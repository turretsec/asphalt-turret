from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, field_validator

class UserSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1

    # Media / thumbnails (instant-ish)
    thumbnail_width: int = Field(default=320, ge=64, le=1920, json_schema_extra={
        "label": "Thumbnail width",
        "requires_restart": False,
        "category": "Media",
    })
    thumbnail_height: int = Field(default=180, ge=64, le=1080, json_schema_extra={
        "label": "Thumbnail height",
        "requires_restart": False,
        "category": "Media",
    })
    thumbnail_quality: int = Field(default=85, ge=10, le=100, json_schema_extra={
        "label": "Thumbnail quality",
        "requires_restart": False,
        "category": "Media",
    })

    # Tools (usually instant)
    ffprobe_timeout_s: int = Field(default=30, ge=1, le=300, json_schema_extra={
        "label": "FFprobe timeout (seconds)",
        "requires_restart": False,
        "category": "Tools",
    })

    # Paths (often restart, because watchers/services depend on it)
    repository_dir: Path | None = Field(default=None, json_schema_extra={
        "label": "Repository folder",
        "requires_restart": True,
        "category": "Paths",
    })
    incoming_dir: Path | None = Field(default=None, json_schema_extra={
        "label": "Incoming folder",
        "requires_restart": True,
        "category": "Paths",
    })

    @field_validator("repository_dir", "incoming_dir", mode="before")
    @classmethod
    def empty_string_means_none(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator("repository_dir", "incoming_dir")
    @classmethod
    def normalize_paths(cls, v: Path | None) -> Path | None:
        if v is None:
            return None
        return Path(v).expanduser()

class UserSettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thumbnail_width: int | None = Field(None, ge=64, le=1920)
    thumbnail_height: int | None = Field(None, ge=64, le=1080)
    thumbnail_quality: int | None = Field(None, ge=10, le=100)
    ffprobe_timeout_s: int | None = Field(None, ge=1, le=300)
    repository_dir: Path | None = Field(None)
    incoming_dir: Path | None = Field(None)