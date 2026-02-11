from pydantic import BaseModel
from datetime import datetime

from asphalt_turret_engine.db.enums import CameraEnum, ModeEnum, MetadataStatusEnum

class ClipResponse(BaseModel):
    id: int
    file_hash: str
    repo_path: str
    original_filename: str | None
    camera: CameraEnum
    mode: ModeEnum
    recorded_at: datetime | None
    duration_s: float | None
    codec: str | None
    width: int | None
    height: int | None
    fps: float | None
    imported_at: datetime
    probe_version: int | None
    probed_at: datetime | None
    metadata_status: MetadataStatusEnum
    metadata_error: str | None
    metadata_json: str | None