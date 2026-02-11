from __future__ import annotations

import os
import re
import ctypes
from ctypes import wintypes
from typing import TypedDict, List, Optional

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# Windows drive types
DRIVE_REMOVABLE = 2

_VOLUME_GUID_RE = re.compile(r"Volume\{([0-9a-fA-F-]+)\}", re.IGNORECASE)


class VolumeInfo(TypedDict):
    drive_root: str
    volume_label: str
    filesystem: str
    serial_hex: str
    volume_uid: str
    volume_guid: Optional[str]
    is_removable: bool


def _get_drive_type(drive_root: str) -> int:
    kernel32.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetDriveTypeW.restype = wintypes.UINT
    return int(kernel32.GetDriveTypeW(drive_root))


def _get_volume_info(drive_root: str) -> Optional[tuple[str, str, str]]:
    """
    Returns (volume_label, filesystem, serial_hex) for the given drive root or None if not readable.
    """
    volume_name = ctypes.create_unicode_buffer(261)
    fs_name = ctypes.create_unicode_buffer(261)
    serial = wintypes.DWORD(0)

    kernel32.GetVolumeInformationW.argtypes = [
        wintypes.LPCWSTR,                 # lpRootPathName
        wintypes.LPWSTR,                  # lpVolumeNameBuffer
        wintypes.DWORD,                   # nVolumeNameSize
        ctypes.POINTER(wintypes.DWORD),   # lpVolumeSerialNumber
        ctypes.c_void_p,                  # lpMaximumComponentLength (unused)
        ctypes.c_void_p,                  # lpFileSystemFlags (unused)
        wintypes.LPWSTR,                  # lpFileSystemNameBuffer
        wintypes.DWORD,                   # nFileSystemNameSize
    ]
    kernel32.GetVolumeInformationW.restype = wintypes.BOOL

    ok = kernel32.GetVolumeInformationW(
        drive_root,
        volume_name,
        len(volume_name),
        ctypes.byref(serial),
        None,
        None,
        fs_name,
        len(fs_name),
    )
    if not ok:
        return None

    serial_hex = f"{int(serial.value):08X}"
    return (volume_name.value or "", fs_name.value or "", serial_hex)


def _get_volume_guid(drive_root: str) -> Optional[str]:
    """
    Returns something like: "\\\\?\\Volume{GUID}\\"
    """
    buf = ctypes.create_unicode_buffer(256)

    kernel32.GetVolumeNameForVolumeMountPointW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        wintypes.DWORD,
    ]
    kernel32.GetVolumeNameForVolumeMountPointW.restype = wintypes.BOOL

    ok = kernel32.GetVolumeNameForVolumeMountPointW(drive_root, buf, len(buf))
    if not ok:
        return None

    return buf.value or None


def _extract_guid_id(volume_guid_path: str) -> Optional[str]:
    """
    From "\\\\?\\Volume{GUID}\\", return "GUID" (lowercase).
    """
    m = _VOLUME_GUID_RE.search(volume_guid_path)
    if not m:
        return None
    return m.group(1).lower()


def list_removable_volumes() -> List[VolumeInfo]:
    """
    Windows-only. Enumerate mounted *removable* volumes and return drive + label + identity.
    """
    drives = os.listdrives()
    results: List[VolumeInfo] = []

    for d in drives:
        dtype = _get_drive_type(d)
        if dtype != DRIVE_REMOVABLE:
            continue

        info = _get_volume_info(d)
        if info is None:
            continue

        label, fs, serial_hex = info

        guid_path = _get_volume_guid(d)
        guid_id = _extract_guid_id(guid_path) if guid_path else None

        if serial_hex != "00000000":
            volume_uid = f"winvol:{serial_hex}"
        elif guid_id:
            volume_uid = f"winvolguid:{guid_id}"
        else:
            # last resort (not stable if drive letter changes)
            volume_uid = f"winvolfallback:{d.lower().rstrip('\\')}"

        results.append(
            {
                "drive_root": d,
                "volume_label": label,
                "filesystem": fs,
                "serial_hex": serial_hex,
                "volume_uid": volume_uid,
                "volume_guid": guid_path,
                "is_removable": True,
            }
        )

    results.sort(key=lambda x: x["drive_root"])
    return results

def resolve_drive_root(volume_uid: str) -> Optional[str]:
    """
    Given a volume UID, return the corresponding drive root (e.g., "E:\\") if found.
    """
    vols = list_removable_volumes()
    match = next((v for v in vols if v["volume_uid"] == volume_uid), None)
    if not match:
        return None
    return match["drive_root"] if match else None