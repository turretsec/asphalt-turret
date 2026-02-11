from __future__ import annotations
import hashlib
from pathlib import Path


def calculate_file_hash(file_path: Path, algorithm: str = "sha256", chunk_size: int = 8192) -> str:
    """
    Calculate hash of a file by reading in chunks.
    
    Args:
        file_path: Path to file to hash
        algorithm: Hash algorithm (sha256, md5, etc.)
        chunk_size: Bytes to read per chunk (default 8KB)
        
    Returns:
        Hexadecimal hash string
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    hasher = hashlib.new(algorithm)
    
    with file_path.open("rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    
    return hasher.hexdigest()