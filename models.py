# models.py
"""Domain models for the download queue.

Pure Python only: no GUI or yt-dlp imports, so the state machine that uses
these types stays unit-testable in isolation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

DATE_FMT = "%Y-%m-%d %H:%M:%S"


class DownloadStatus(str, Enum):
    """Lifecycle of a queued download.

    The values are the exact strings already persisted in ``queue.json`` so the
    on-disk schema is unchanged by the Phase 8 port.
    """

    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

    @classmethod
    def coerce(cls, value: object) -> "DownloadStatus":
        """Return a valid status, defaulting unknown/legacy values to PENDING."""
        try:
            return cls(value)
        except ValueError:
            return cls.PENDING


@dataclass
class DownloadItem:
    """A single queued download."""

    url: str
    path: str
    resolution: str = "720"
    audio_only: bool = False
    title: str = "Unknown"
    status: DownloadStatus = DownloadStatus.PENDING
    date_added: str = ""

    def __post_init__(self) -> None:
        if not self.date_added:
            self.date_added = datetime.now().strftime(DATE_FMT)

    def to_dict(self) -> dict:
        """Serialise to the legacy ``queue.json`` record shape."""
        return {
            "url": self.url,
            "path": self.path,
            "resolution": self.resolution,
            "audio_only": self.audio_only,
            "title": self.title,
            "status": self.status.value,
            "date_added": self.date_added,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DownloadItem":
        """Build an item from a persisted record, tolerating missing keys."""
        return cls(
            url=str(data.get("url", "")),
            path=str(data.get("path", "")),
            resolution=str(data.get("resolution", "720")),
            audio_only=bool(data.get("audio_only", False)),
            title=str(data.get("title", "Unknown")),
            status=DownloadStatus.coerce(data.get("status", DownloadStatus.PENDING.value)),
            date_added=str(data.get("date_added", "")),
        )
