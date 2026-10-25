# queue_manager.py
"""Pure-Python queue state machine.

Owns the list of :class:`~models.DownloadItem` objects and every status
transition. No GUI or yt-dlp imports live here, so the Phase-1 behaviour
(start/stop/cancel correctness) can be unit-tested in isolation. Persistence is
injected, so tests run against an in-memory fake.
"""
from __future__ import annotations

import logging
import threading
from collections import Counter
from collections.abc import Callable
from typing import Protocol

from models import DownloadItem, DownloadStatus

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = frozenset({DownloadStatus.PENDING, DownloadStatus.PAUSED})
_RUNNING_OR_QUEUED = frozenset({DownloadStatus.PENDING, DownloadStatus.DOWNLOADING, DownloadStatus.PAUSED})


class QueueStore(Protocol):
    """Persistence boundary for the queue (see ``persistence.py``)."""

    def load_queue(self) -> list[dict]: ...

    def save_queue(self, queue: list[dict]) -> None: ...


class QueueManager:
    """Thread-safe owner of the download queue.

    Every mutating method takes ``_lock`` so download workers and the UI can
    share one instance. Methods that change state persist via the injected
    store before returning.
    """

    def __init__(
        self,
        store: QueueStore,
        history_loader: Callable[[], list[dict]] | None = None,
    ) -> None:
        self._store = store
        self._history_loader = history_loader
        self._lock = threading.RLock()
        self._items: list[DownloadItem] = []

    # -- loading / persistence --------------------------------------------
    def load(self) -> None:
        """Load the queue, rehabilitating items stuck as ``downloading``.

        An item persisted mid-download (e.g. after a crash) is reset to
        ``pending`` so it becomes runnable again instead of being stranded.
        """
        raw = self._store.load_queue()
        items = [DownloadItem.from_dict(row) for row in raw if isinstance(row, dict)]
        changed = False
        for item in items:
            if item.status is DownloadStatus.DOWNLOADING:
                item.status = DownloadStatus.PENDING
                changed = True
        with self._lock:
            self._items = items
        if changed:
            logger.info("Rehabilitated interrupted items to pending")
            self.save()

    def save(self) -> None:
        with self._lock:
            snapshot = [item.to_dict() for item in self._items]
        self._store.save_queue(snapshot)

    def snapshot(self) -> list[DownloadItem]:
        with self._lock:
            return list(self._items)

    def item_at(self, index: int) -> DownloadItem | None:
        with self._lock:
            if 0 <= index < len(self._items):
                return self._items[index]
        return None

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)

    # -- mutation ----------------------------------------------------------
    def add(self, item: DownloadItem) -> DownloadItem:
        with self._lock:
            self._items.append(item)
        self.save()
        return item

    def remove(self, index: int) -> bool:
        with self._lock:
            if not 0 <= index < len(self._items):
                return False
            del self._items[index]
        self.save()
        return True

    def clear_completed(self) -> None:
        with self._lock:
            self._items = [
                item for item in self._items if item.status is not DownloadStatus.COMPLETED
            ]
        self.save()

    # -- duplicate detection ----------------------------------------------
    def find_duplicate(self, url: str) -> tuple[str | None, dict | None]:
        """Return ``("queue"|"history", record)`` if ``url`` was seen before."""
        with self._lock:
            for item in self._items:
                if item.url == url and item.status in _RUNNING_OR_QUEUED:
                    return "queue", item.to_dict()
        if self._history_loader is not None:
            for entry in self._history_loader():
                if entry.get("url") == url:
                    return "history", entry
        return None, None

    # -- status transitions ------------------------------------------------
    def runnable_items(self) -> list[DownloadItem]:
        with self._lock:
            return [item for item in self._items if item.status in ACTIVE_STATUSES]

    def has_running(self) -> bool:
        with self._lock:
            return any(item.status is DownloadStatus.DOWNLOADING for item in self._items)

    def mark_running(self, items: list[DownloadItem] | None = None) -> None:
        """Mark pending/paused items as downloading (guarded double-start)."""
        with self._lock:
            targets = items if items is not None else list(self._items)
            for item in targets:
                if item.status in ACTIVE_STATUSES:
                    item.status = DownloadStatus.DOWNLOADING
        self.save()

    def mark_completed(self, item: DownloadItem) -> None:
        with self._lock:
            item.status = DownloadStatus.COMPLETED
        self.save()

    def mark_paused(self, item: DownloadItem) -> None:
        with self._lock:
            item.status = DownloadStatus.PAUSED
        self.save()

    def mark_failed(self, item: DownloadItem) -> None:
        """Fail an item, but never clobber a pause requested mid-flight."""
        with self._lock:
            if item.status is DownloadStatus.PAUSED:
                return
            item.status = DownloadStatus.FAILED
        self.save()

    def pause_all_running(self) -> int:
        """Pause every running item; return how many were changed."""
        count = 0
        with self._lock:
            for item in self._items:
                if item.status is DownloadStatus.DOWNLOADING:
                    item.status = DownloadStatus.PAUSED
                    count += 1
        if count:
            self.save()
        return count

    def resume(self, index: int) -> bool:
        """Move a paused item back to pending so it can run again."""
        with self._lock:
            if not 0 <= index < len(self._items):
                return False
            item = self._items[index]
            if item.status is not DownloadStatus.PAUSED:
                return False
            item.status = DownloadStatus.PENDING
        self.save()
        return True

    # -- stats -------------------------------------------------------------
    def stats(self) -> dict[str, int]:
        with self._lock:
            counts = Counter(item.status for item in self._items)
            total = len(self._items)
        return {
            "total": total,
            "pending": counts[DownloadStatus.PENDING],
            "downloading": counts[DownloadStatus.DOWNLOADING],
            "completed": counts[DownloadStatus.COMPLETED],
            "failed": counts[DownloadStatus.FAILED],
            "paused": counts[DownloadStatus.PAUSED],
        }
