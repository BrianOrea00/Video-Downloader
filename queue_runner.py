# queue_runner.py
"""Background queue execution for the Qt UI.

Runs runnable :class:`~models.DownloadItem` objects through the existing
``Downloader`` engine, on a worker pool, and reports back on Qt signals. The
stop token mirrors the Phase-1 contract: once requested, no new download starts
and every active downloader is cancelled, so nothing is left half-running.
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import QObject, Signal

from downloader import Downloader

logger = logging.getLogger(__name__)


class QueueRunner(QObject):
    """Threaded download executor. All signals are delivered on the GUI thread."""

    progress = Signal(object, dict)       # (DownloadItem, hook data)
    item_finished = Signal(object, str)   # (DownloadItem, message)
    item_info = Signal(object, object)    # (DownloadItem, yt-dlp info dict)
    run_finished = Signal()               # whole batch drained

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._lock = threading.Lock()
        self._active: list[Downloader] = []
        self._stop_event = threading.Event()
        self._running = False
        self._generation = 0

    # -- public API --------------------------------------------------------
    def is_running(self) -> bool:
        return self._running

    def start(self, items: list, settings: dict) -> None:
        """Run ``items`` with the saved parallel/sequential mode."""
        if self._running or not items:
            return
        self._running = True
        self._generation += 1
        generation = self._generation
        self._stop_event = threading.Event()

        mode = settings.get("download_mode", "parallel")
        limit = 1 if mode == "sequential" else max(1, int(settings.get("parallel_limit", 2)))
        cookie_settings = {
            "cookie_method": settings.get("cookie_method", "none"),
            "cookie_browser": settings.get("cookie_browser", "chrome"),
            "cookie_file_path": settings.get("cookie_file_path", ""),
        }

        thread = threading.Thread(
            target=self._run,
            args=(generation, list(items), cookie_settings, limit),
            daemon=True,
        )
        thread.start()

    def stop(self) -> None:
        """Request a stop: reject new work and cancel everything running."""
        self._stop_event.set()
        self._running = False
        with self._lock:
            active = list(self._active)
            self._active.clear()
        for downloader in active:
            downloader.cancel()
        logger.info("Stop requested; cancelled %d active downloader(s)", len(active))

    # -- internals ---------------------------------------------------------
    def _run(self, generation, items, cookie_settings, limit) -> None:
        logger.info("Queue run %d: %d item(s), max %d concurrent", generation, len(items), limit)
        with ThreadPoolExecutor(max_workers=limit) as executor:
            futures = [executor.submit(self._one, generation, item, cookie_settings) for item in items]
            for future in futures:
                try:
                    future.result()
                except Exception as exc:  # noqa: BLE001 - one item must not kill the batch
                    logger.error("Download task raised: %s", exc)
        self._running = False
        self.run_finished.emit()

    def _one(self, generation, item, cookie_settings) -> None:
        if generation != self._generation or self._stop_event.is_set():
            return

        downloader = Downloader()
        with self._lock:
            self._active.append(downloader)

        done = threading.Event()

        def on_progress(data: dict) -> None:
            self.progress.emit(item, data)

        def on_done(message: str) -> None:
            self.item_finished.emit(item, message)
            done.set()

        def on_info(info: dict) -> None:
            self.item_info.emit(item, info)

        try:
            downloader.download(
                item.url,
                item.path,
                item.resolution,
                on_progress,
                on_done,
                audio_only=item.audio_only,
                cookie_settings=cookie_settings,
                max_retries=3,
                stop_event=self._stop_event,
                info_callback=on_info,
            )
            while not done.is_set() and not self._stop_event.is_set():
                done.wait(0.5)
        except Exception as exc:  # noqa: BLE001 - surface as a failure signal
            logger.error("Download failed for %s: %s", item.url, exc)
            self.item_finished.emit(item, f"Error: {exc}")
        finally:
            with self._lock:
                if downloader in self._active:
                    self._active.remove(downloader)
            done.set()
