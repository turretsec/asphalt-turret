import hashlib
from datetime import datetime

def meta_fingerprint(rel_path: str, size_bytes: int, mtime: "datetime") -> str:
    # deterministic, cheap, stable
    s = f"{rel_path}|{size_bytes}|{mtime.isoformat()}"
    return hashlib.sha256(s.encode("utf-8")).hexdigest()