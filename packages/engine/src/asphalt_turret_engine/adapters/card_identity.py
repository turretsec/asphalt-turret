"""
Card identity adapter.

Manages the .at_card_id file on the physical SD card. This file contains a
UUID that we generate on first scan and use on all subsequent scans to
recognise the same physical card even if Windows assigns it a new volume UID.

File location: <drive_root>/.at_card_id
File format:   plain text UUID (e.g. "550e8400-e29b-41d4-a716-446655440000")

Design decisions:
- Hidden by convention (dot-prefix) — won't show in normal file browsers
- Root of the card, not inside a recording directory — Thinkware firmware
  only reads its own subdirectories so this file is invisible to it
- Read-only once written — we never overwrite an existing identity
- Fails silently on read errors — the fallback merge logic handles it
"""
from __future__ import annotations
import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

IDENTITY_FILENAME = ".at_card_id"


def read_card_identity(drive_root: str | Path) -> str | None:
    """
    Read the card identity UUID from the physical card.

    Returns the UUID string if found and valid, None otherwise.
    Never raises — caller treats None as "identity unknown".
    """
    try:
        identity_path = Path(drive_root) / IDENTITY_FILENAME
        if not identity_path.exists():
            return None

        raw = identity_path.read_text(encoding="utf-8").strip()

        # Validate it looks like a UUID before trusting it
        uuid.UUID(raw)
        return raw

    except (ValueError, OSError) as e:
        logger.debug(f"Could not read card identity from {drive_root}: {e}")
        return None


def write_card_identity(drive_root: str | Path, identity: str) -> bool:
    """
    Write a card identity UUID to the physical card.

    Only writes if no identity file exists yet — never overwrites.
    Returns True if written, False if already existed or write failed.
    """
    try:
        identity_path = Path(drive_root) / IDENTITY_FILENAME

        if identity_path.exists():
            logger.debug(f"Card identity file already exists at {identity_path}, skipping write")
            return False

        identity_path.write_text(identity, encoding="utf-8")
        logger.info(f"Wrote card identity {identity} to {identity_path}")
        return True

    except OSError as e:
        logger.warning(f"Could not write card identity to {drive_root}: {e}")
        return False


def ensure_card_identity(drive_root: str | Path) -> str:
    """
    Return the card's identity UUID, creating and writing one if needed.

    This is the main entry point. Call it during scan to get the stable
    identity for the card regardless of what the OS assigned as volume UID.

    Never raises — if the write fails, returns the generated UUID anyway
    so the scan can continue. The identity just won't persist to the card.
    """
    existing = read_card_identity(drive_root)
    if existing:
        return existing

    new_identity = str(uuid.uuid4())
    write_card_identity(drive_root, new_identity)
    return new_identity