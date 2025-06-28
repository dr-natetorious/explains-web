# src/shared/utils.py
import hashlib
import asyncio
from pathlib import Path
from typing import Any, Callable, TypeVar, Awaitable
from datetime import datetime

T = TypeVar('T')

def get_file_hash(file_path: str) -> str:
    """Calculate SHA-256 hash of a file"""
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception:
        return ""

def ensure_directory(path: str | Path) -> Path:
    """Create directory if it doesn't exist, return Path object"""
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj

def safe_filename(filename: str) -> str:
    """Convert string to safe filename"""
    import re
    return re.sub(r'[^\w\-_.]', '_', filename)

async def retry_async(
    func: Callable[[], Awaitable[T]], 
    max_attempts: int = 3, 
    delay_seconds: float = 1.0
) -> T:
    """Retry an async function with exponential backoff"""
    for attempt in range(max_attempts):
        try:
            return await func()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise e
            await asyncio.sleep(delay_seconds * (2 ** attempt))

def format_timestamp(dt: datetime = None) -> str:
    """Format timestamp for logging/display"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis"""
    return text if len(text) <= max_length else text[:max_length-3] + "..."