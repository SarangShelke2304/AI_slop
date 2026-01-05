
import re
import os
import shutil
from pathlib import Path
from datetime import timedelta

def clean_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.
    """
    # Replace invalid chars with underscore
    cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove whitespace
    cleaned = cleaned.strip().replace(' ', '_')
    # Limit length
    return cleaned[:255]

def format_duration(seconds: float) -> str:
    """
    Format seconds to MM:SS string.
    """
    td = timedelta(seconds=int(seconds))
    total_seconds = int(td.total_seconds())
    minutes, secs = divmod(total_seconds, 60)
    return f"{minutes:02d}:{secs:02d}"

def get_file_size_mb(path: str | Path) -> float:
    """
    Get file size in megabytes.
    """
    try:
        size_bytes = os.path.getsize(path)
        return round(size_bytes / (1024 * 1024), 2)
    except OSError:
        return 0.0

def cleanup_temp_files(temp_dir: Path, pattern: str = "*"):
    """
    Remove files in temp directory matching pattern.
    """
    for file_path in temp_dir.glob(pattern):
        try:
            if file_path.is_file():
                file_path.unlink()
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")

def slugify(text: str) -> str:
    """
    Simple slugify for filenames.
    """
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')
