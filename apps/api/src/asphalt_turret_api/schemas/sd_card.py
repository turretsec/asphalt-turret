from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

from asphalt_turret_engine.db.enums import SDFileImportStateEnum, ModeEnum


class ScanRequest(BaseModel):
    """Request to scan an SD card."""
    volume_uid: str = Field(..., description="Volume UID of the SD card")


class ScanResponse(BaseModel):
    """Result of scanning an SD card."""
    sd_card_id: int
    drive_root: str
    found: int = Field(..., description="Total files found on SD card")
    new: int = Field(..., description="New files added to database")
    updated: int = Field(..., description="Files with updated metadata")
    unchanged: int = Field(..., description="Files that hadn't changed")
    skipped: int = Field(default=0, description="Files skipped due to errors")
    deleted: int = Field(default=0, description="Files removed from database because they no longer exist on SD card")

class SDCardListItem(BaseModel):
    """SD card info for list view."""
    volume_uid: str
    volume_label: Optional[str]
    first_seen_at: datetime
    last_seen_at: datetime
    is_connected: bool = Field(description="Whether card is currently plugged in")
    drive_root: Optional[str] = Field(default=None, description="Current drive path (e.g., 'E:\\' or '/media/sdcard'). Only present if connected.")
    total_files: int = Field(default=0, description="Total files on this card")
    pending_files: int = Field(default=0, description="Files awaiting import")
    
    model_config = {"from_attributes": True}

class SDCardsListResponse(BaseModel):
    """Response for listing SD cards."""
    cards: list[SDCardListItem]
    connected_count: int = Field(description="How many cards are currently connected")
    
class SDCardDetailResponse(BaseModel):
    """Detailed info about a single SD card."""
    volume_uid: str
    volume_label: Optional[str]
    first_seen_at: datetime
    last_seen_at: datetime
    is_connected: bool
    drive_root: Optional[str] = Field(default=None, description="Current drive path. Only present if connected.")
    total_files: int
    pending_files: int
    imported_files: int
    failed_files: int


class SDFileCandidate(BaseModel):
    """A file discovered on an SD card."""
    id: int
    rel_path: str
    size_bytes: int
    mtime: datetime
    import_state: SDFileImportStateEnum
    mode: ModeEnum
    
    model_config = {"from_attributes": True}

class SDFileResponse(BaseModel):
    """A file on an SD card."""
    id: int
    rel_path: str
    size_bytes: int
    mtime: datetime
    import_state: SDFileImportStateEnum
    fingerprint: str = Field(description="File hash/fingerprint")
    last_seen_at: datetime
    
    model_config = {"from_attributes": True}


class SDFilesListResponse(BaseModel):
    """Response for listing SD card files."""
    volume_uid: str
    volume_label: Optional[str]
    total_files: int = Field(description="Total files matching filters")
    returned_files: int = Field(description="Number of files in this response")
    files: list[SDFileResponse]

class TreeNode(BaseModel):
    """Tree node for hierarchical file view."""
    key: str
    label: str
    data: dict
    children: Optional[list["TreeNode"]] = None
    icon: Optional[str] = None