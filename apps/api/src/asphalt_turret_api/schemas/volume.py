from pydantic import BaseModel

class VolumeResponse(BaseModel):
    drive_root: str
    volume_label: str
    filesystem: str
    serial_hex: str
    volume_uid: str
    volume_guid: str | None
    is_removable: bool