# thumb_cache.py
"""Thumbnail cache for the video grid.

Thumbnails are keyed by the downloaded file's name so the grid can find one
without a history lookup: ``<download_path>/.thumbs/<sha1(filename)>.jpg``.
Writing happens off the GUI thread (see ``ui/pages/queue_page.py``).
"""
from __future__ import annotations

import hashlib
import logging
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

THUMB_DIR = ".thumbs"
FETCH_TIMEOUT = 10


def _digest(filename: str) -> str:
    return hashlib.sha1(filename.encode("utf-8")).hexdigest()


def thumb_path(download_path: str, filename: str) -> Path:
    return Path(download_path) / THUMB_DIR / f"{_digest(filename)}.jpg"


def store(download_path: str, filename: str, data: bytes) -> str | None:
    """Persist thumbnail bytes for ``filename``; return the path written."""
    try:
        target = thumb_path(download_path, filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return str(target)
    except OSError as exc:
        logger.error("Failed to store thumbnail for %s: %s", filename, exc)
        return None


def local_path(download_path: str, filename: str) -> str | None:
    """Return the cached thumbnail path for ``filename`` if it exists."""
    path = thumb_path(download_path, filename)
    return str(path) if path.exists() else None


def fetch(thumb_url: str) -> bytes | None:
    """Download thumbnail bytes. Call from a worker thread, never the GUI thread."""
    if not thumb_url:
        return None
    try:
        with urllib.request.urlopen(thumb_url, timeout=FETCH_TIMEOUT) as response:  # noqa: S310
            return response.read()
    except Exception as exc:  # noqa: BLE001 - thumbnails are best-effort
        logger.error("Thumbnail fetch failed: %s", exc)
        return None


def final_filename(info: dict) -> str | None:
    """Best-effort final file name from a yt-dlp info dict."""
    downloads = info.get("requested_downloads") or []
    if downloads and downloads[0].get("filepath"):
        return Path(downloads[0]["filepath"]).name
    if info.get("filepath"):
        return Path(info["filepath"]).name
    return None
