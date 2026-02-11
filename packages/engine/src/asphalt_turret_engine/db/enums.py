from enum import Enum

class CameraEnum(str, Enum):
    front = "front"
    rear = "rear"
    unknown = "unknown"

class ModeEnum(str, Enum):
    continuous = "continuous"
    event = "event"
    manual = "manual"
    motion = "motion"
    parking = "parking"
    sos = "sos"
    unknown = "unknown"

class ArtifactKindEnum(str, Enum):
    thumb = "thumb"
    contact_sheet = "contact_sheet"
    frame_extract = "frame_extract"

class JobTypeEnum(str, Enum):
    clip_import = "clip_import"
    clip_probe = "clip_probe"
    hash = "hash"
    thumb = "thumb"
    contact_sheet = "contact_sheet"
    import_batch = "import_batch"
    probe_batch = "probe_batch"
    import_file = "import_file"
    probe_clip = "probe_clip"

class JobStateEnum(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    canceled = "canceled"

class SDFileImportStateEnum(str, Enum):
    new = "new"
    changed = "changed"
    imported = "imported"
    ignored = "ignored"
    pending = "pending"

class MetadataStatusEnum(str, Enum):
    pending = "pending"      # Not yet probed
    extracted = "extracted"  # Successfully probed
    failed = "failed"        # Probe failed
    partial = "partial"      # Some metadata extracted, some failed