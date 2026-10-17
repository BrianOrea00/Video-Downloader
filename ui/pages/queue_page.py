# ui/pages/queue_page.py
"""Download Console page: add URL, preview, live per-row progress, start/stop.

Mirrors ``docs/ui-prototype.html`` (#page-queue). State lives in
:class:`queue_manager.QueueManager`; downloads run in :class:`queue_runner.QueueRunner`.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from config import RESOLUTIONS
from downloader import Downloader
from models import DownloadItem, DownloadStatus
from persistence import save_history
from queue_manager import QueueManager
from queue_runner import QueueRunner
from url_validator import validate_url
import thumb_cache
from ui import theme as ui_theme

logger = logging.getLogger(__name__)

STATUS_META = {
    DownloadStatus.PENDING: ("Pending", "muted"),
    DownloadStatus.DOWNLOADING: ("Downloading", "accent"),
    DownloadStatus.PAUSED: ("Paused", "warning"),
    DownloadStatus.COMPLETED: ("Completed", "success"),
    DownloadStatus.FAILED: ("Failed", "error"),
}
STATUS_ORDER = {
    DownloadStatus.PENDING: 0,
    DownloadStatus.PAUSED: 1,
    DownloadStatus.DOWNLOADING: 2,
    DownloadStatus.COMPLETED: 4,
    DownloadStatus.FAILED: 5,
}


def _fmt_duration(seconds) -> str:
    try:
        total = int(seconds)
    except (TypeError, ValueError):
        return ""
    if total <= 0:
        return ""
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def _fmt_views(count) -> str:
    try:
        value = int(count)
    except (TypeError, ValueError):
        return ""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M views"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K views"
    return f"{value} views"


def _fmt_size(num_bytes) -> str:
    try:
        value = float(num_bytes)
    except (TypeError, ValueError):
        return ""
    if value <= 0:
        return ""
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return ""


def _chip(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("Chip")
    return label


class InfoWorker(QThread):
    """Fetches yt-dlp metadata off the GUI thread."""

    fetched = Signal(object)  # dict | None

    def __init__(self, url: str, cookie_settings: dict, parent=None) -> None:
        super().__init__(parent)
        self._url = url
        self._cookie = cookie_settings

    def run(self) -> None:
        try:
            info = Downloader().get_info(self._url, self._cookie)
        except Exception as exc:  # noqa: BLE001 - report as "could not fetch"
            logger.error("Info fetch failed for %s: %s", self._url, exc)
            info = None
        self.fetched.emit(info)


class ThumbWorker(QThread):
    """Fetches a thumbnail off the GUI thread and caches it beside the file."""

    def __init__(self, download_path: str, filename: str, thumb_url: str, parent=None) -> None:
        super().__init__(parent)
        self._path = download_path
        self._filename = filename
        self._url = thumb_url

    def run(self) -> None:
        data = thumb_cache.fetch(self._url)
        if data:
            thumb_cache.store(self._path, self._filename, data)


class QueueRow(QFrame):
    """One queue line: tile, title, chips, progress, stats, actions."""

    open_folder = Signal(object)
    cancel = Signal(object)
    resume = Signal(object)
    remove = Signal(object)

    def __init__(self, item: DownloadItem, parent=None) -> None:
        super().__init__(parent)
        self.item = item
        self.setObjectName("Row")
        if item.status is DownloadStatus.DOWNLOADING:
            self.setObjectName("RowActive")

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(12)

        tile = QLabel("\u266a" if item.audio_only else "\u25bc")
        tile.setObjectName("RowTile")
        tile.setFixedSize(40, 28)
        tile.setAlignment(Qt.AlignCenter)
        row.addWidget(tile)

        main = QVBoxLayout()
        main.setSpacing(3)
        self.title_label = QLabel(item.title[:80])
        if item.status is DownloadStatus.COMPLETED:
            self.title_label.setStyleSheet(f"color: {ui_theme.color('muted')};")
        main.addWidget(self.title_label)

        meta = QHBoxLayout()
        meta.setSpacing(6)
        res_text = "MP3" if item.audio_only else f"{item.resolution}p"
        meta.addWidget(_chip(res_text))
        label, token = STATUS_META.get(item.status, STATUS_META[DownloadStatus.PENDING])
        status = QLabel(f"\u25cf {label}")
        status.setStyleSheet(f"color: {ui_theme.color(token)}; font-size: 10px;")
        meta.addWidget(status)
        meta.addStretch(1)
        main.addLayout(meta)

        self.progress = QProgressBar()
        self.progress.setObjectName("RowProgress")
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.setVisible(item.status is DownloadStatus.DOWNLOADING)
        main.addWidget(self.progress)

        self.stats = QLabel("")
        self.stats.setStyleSheet(f"color: {ui_theme.color('gray_light')}; font-size: 11px;")
        self.stats.setVisible(item.status is DownloadStatus.DOWNLOADING)
        main.addWidget(self.stats)

        row.addLayout(main, 1)

        actions = QHBoxLayout()
        actions.setSpacing(6)
        actions.addWidget(self._icon_button("\U0001f4c1", "Open folder", lambda: self.open_folder.emit(self.item)))
        if item.status is DownloadStatus.DOWNLOADING:
            actions.addWidget(self._icon_button("\u2715", "Cancel", lambda: self.cancel.emit(self.item)))
        if item.status is DownloadStatus.PAUSED:
            actions.addWidget(self._icon_button("\u21bb", "Resume", lambda: self.resume.emit(self.item)))
        if item.status is not DownloadStatus.DOWNLOADING:
            actions.addWidget(self._icon_button("\U0001f5d1", "Delete", lambda: self.remove.emit(self.item)))
        row.addLayout(actions)

    def _icon_button(self, glyph: str, tip: str, slot) -> QPushButton:
        button = QPushButton(glyph)
        button.setFixedSize(28, 28)
        button.setToolTip(tip)
        button.setAccessibleName(tip)
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(slot)
        return button

    def set_progress(self, percent: float, data: dict) -> None:
        self.progress.setVisible(True)
        self.stats.setVisible(True)
        self.progress.setValue(int(max(0.0, min(100.0, percent))))
        parts = [f"{percent:.0f}%"]
        if data.get("_speed_str"):
            parts.append(data["_speed_str"])
        if data.get("_eta_str"):
            parts.append(f"ETA {data['_eta_str']}")
        if data.get("_downloaded_bytes_str") and data.get("_total_bytes_str"):
            parts.append(f"{data['_downloaded_bytes_str']} / {data['_total_bytes_str']}")
        self.stats.setText("   ".join(parts))


class QueuePage(QWidget):
    count_changed = Signal(int)  # pending + paused items, for the shell badge
    download_completed = Signal()  # a file finished, so media pages may re-scan

    def __init__(self, manager: QueueManager, settings: dict, parent=None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.settings = settings
        self.runner = QueueRunner(self)
        self._rows: dict[int, QueueRow] = {}
        self._preview_info: dict | None = None
        self._preview_url: str | None = None
        self._info_worker: InfoWorker | None = None
        self._thumb_workers: set[ThumbWorker] = set()
        self._last_sanitized: str | None = None

        self.manager.load()
        self._build()

        self.runner.progress.connect(self._on_progress)
        self.runner.item_finished.connect(self._on_item_finished)
        self.runner.item_info.connect(self._on_item_info)
        self.runner.run_finished.connect(self._on_run_finished)

        self.refresh()

    # -- construction ------------------------------------------------------
    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        container = QWidget()
        scroll.setWidget(container)
        col = QVBoxLayout(container)
        col.setContentsMargins(24, 20, 24, 20)
        col.setSpacing(16)

        col.addWidget(self._build_input_card())

        self.chips_row = QHBoxLayout()
        self.chips_row.setSpacing(8)
        col.addLayout(self.chips_row)

        col.addWidget(self._section("Active"))
        self.active_list = QVBoxLayout()
        self.active_list.setSpacing(8)
        col.addLayout(self.active_list)

        col.addWidget(self._section("Queue"))
        self.queue_list = QVBoxLayout()
        self.queue_list.setSpacing(8)
        col.addLayout(self.queue_list)

        col.addLayout(self._build_actions())
        col.addStretch(1)

    def _section(self, text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setObjectName("FieldLabel")
        return label

    def _build_input_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        field = QLabel("ADD URL")
        field.setObjectName("FieldLabel")
        layout.addWidget(field)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://youtube.com/watch?v=...")
        self.url_input.setClearButtonEnabled(True)
        self.url_input.textChanged.connect(self._on_url_changed)
        input_row.addWidget(self.url_input, 1)

        paste_btn = QPushButton("Paste")
        paste_btn.clicked.connect(self.paste)
        input_row.addWidget(paste_btn)

        add_btn = QPushButton("Add to Queue")
        add_btn.setObjectName("PrimaryButton")
        add_btn.clicked.connect(self.add_to_queue)
        input_row.addWidget(add_btn)
        layout.addLayout(input_row)

        pills = QHBoxLayout()
        pills.setSpacing(6)
        self._res_group = QButtonGroup(self)
        self._res_group.setExclusive(True)
        self._res = self.settings.get("default_resolution", "720")
        if self._res not in RESOLUTIONS:
            self._res = "720"
        self._res_buttons: dict[str, QPushButton] = {}
        for res in RESOLUTIONS:
            pill = QPushButton(f"{res}p")
            pill.setObjectName("Pill")
            pill.setCheckable(True)
            pill.setCursor(Qt.PointingHandCursor)
            pill.setChecked(res == self._res)
            pill.clicked.connect(lambda _=False, r=res: self.set_resolution(r))
            self._res_group.addButton(pill)
            self._res_buttons[res] = pill
            pills.addWidget(pill)
        pills.addStretch(1)
        self.audio_pill = QPushButton("Audio Only")
        self.audio_pill.setObjectName("Pill")
        self.audio_pill.setCheckable(True)
        self.audio_pill.setCursor(Qt.PointingHandCursor)
        self.audio_pill.setChecked(bool(self.settings.get("default_audio_only", False)))
        pills.addWidget(self.audio_pill)
        layout.addLayout(pills)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self.path_label = QLabel(self.settings.get("download_path") or "Select download folder\u2026")
        self.path_label.setStyleSheet(f"color: {ui_theme.color('muted')}; font-size: 11px;")
        self.path_label.setWordWrap(False)
        path_row.addWidget(self.path_label, 1)
        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse)
        path_row.addWidget(browse)
        layout.addLayout(path_row)

        self.preview = QFrame()
        self.preview.setObjectName("Card")
        self.preview.setVisible(False)
        self.preview_layout = QHBoxLayout(self.preview)
        self.preview_layout.setContentsMargins(10, 10, 10, 10)
        self.preview_layout.setSpacing(12)
        layout.addWidget(self.preview)
        return card

    def _build_actions(self) -> QHBoxLayout:
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.start_btn = QPushButton("Start Queue")
        self.start_btn.setObjectName("PrimaryButton")
        self.start_btn.clicked.connect(self.start)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("DangerButton")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop)
        clear_btn = QPushButton("Clear Completed")
        clear_btn.clicked.connect(self.clear_completed)
        actions.addWidget(self.start_btn)
        actions.addWidget(self.stop_btn)
        actions.addWidget(clear_btn)
        actions.addStretch(1)
        return actions

    # -- input handlers ----------------------------------------------------
    def _on_url_changed(self, text: str) -> None:
        text = text.strip()
        if not text:
            self._hide_preview()
            self.url_input.setStyleSheet("")
            self._last_sanitized = None
            return
        result = validate_url(text)
        if result["valid"]:
            self._last_sanitized = result["sanitized"]
            self.url_input.setStyleSheet(f"border: 1px solid {ui_theme.color('success')};")
            self._fetch_preview(result["sanitized"])
        else:
            self._last_sanitized = None
            self.url_input.setStyleSheet(f"border: 1px solid {ui_theme.color('error')};")
            self._hide_preview()

    def set_resolution(self, res: str) -> None:
        self._res = res
        button = self._res_buttons.get(res)
        if button is not None:
            button.setChecked(True)

    def apply_defaults(self) -> None:
        """Re-apply default resolution/audio from settings to the input bar."""
        res = self.settings.get("default_resolution", "720")
        if res in self._res_buttons:
            self.set_resolution(res)
        self.audio_pill.setChecked(bool(self.settings.get("default_audio_only", False)))

    def paste(self) -> None:
        from PySide6.QtWidgets import QApplication

        text = (QApplication.clipboard().text() or "").strip()
        if text:
            self.url_input.setText(text)
        else:
            QMessageBox.information(self, "Clipboard", "Clipboard is empty.")

    def browse(self) -> None:
        start = self.settings.get("download_path") or ""
        folder = QFileDialog.getExistingDirectory(self, "Select download folder", start)
        if folder:
            self.settings["download_path"] = folder
            self.path_label.setText(folder)
            self.path_label.setStyleSheet(f"color: {ui_theme.color('text')}; font-size: 11px;")

    # -- link preview ------------------------------------------------------
    def _fetch_preview(self, url: str) -> None:
        if self._info_worker is not None and self._info_worker.isRunning():
            return
        self._show_preview_state("Fetching video info\u2026")
        cookie_settings = {
            "cookie_method": self.settings.get("cookie_method", "none"),
            "cookie_browser": self.settings.get("cookie_browser", "chrome"),
            "cookie_file_path": self.settings.get("cookie_file_path", ""),
        }
        self._info_worker = InfoWorker(url, cookie_settings, self)
        self._info_worker.fetched.connect(lambda info, u=url: self._on_preview_fetched(u, info))
        self._info_worker.start()

    def _on_preview_fetched(self, url: str, info) -> None:
        if info is None:
            self._preview_info = None
            self._preview_url = None
            self._show_preview_state("Could not fetch video info.")
            return
        self._preview_info = info
        self._preview_url = url
        self._render_preview(info)

    def _show_preview_state(self, text: str) -> None:
        self._clear_layout(self.preview_layout)
        label = QLabel(text)
        label.setStyleSheet(f"color: {ui_theme.color('muted')};")
        self.preview_layout.addWidget(label)
        self.preview_layout.addStretch(1)
        self.preview.setVisible(True)

    def _show_preview(self, info) -> None:
        if not info:
            self._hide_preview()

    def _hide_preview(self) -> None:
        self.preview.setVisible(False)
        self._clear_layout(self.preview_layout)
        self._preview_info = None
        self._preview_url = None

    def _render_preview(self, info: dict) -> None:
        self._clear_layout(self.preview_layout)
        duration = _fmt_duration(info.get("duration"))

        thumb = QLabel("\u25b6")
        thumb.setObjectName("RowTile")
        thumb.setFixedSize(96, 54)
        thumb.setAlignment(Qt.AlignCenter)
        self.preview_layout.addWidget(thumb)

        body = QVBoxLayout()
        body.setSpacing(4)
        title = QLabel(info.get("title", "Unknown"))
        title.setStyleSheet("font-weight: 600;")
        body.addWidget(title)
        chips = QHBoxLayout()
        chips.setSpacing(6)
        channel = info.get("uploader") or info.get("channel")
        if channel:
            chips.addWidget(_chip(channel))
        if duration:
            chips.addWidget(_chip(duration))
        views = _fmt_views(info.get("view_count"))
        if views:
            chips.addWidget(_chip(views))
        size = _fmt_size(info.get("filesize_approx") or info.get("filesize"))
        if size:
            chips.addWidget(_chip(f"~{size}"))
        chips.addStretch(1)
        body.addLayout(chips)
        self.preview_layout.addLayout(body, 1)
        self.preview.setVisible(True)

    # -- queue actions -----------------------------------------------------
    def add_to_queue(self) -> None:
        url = self._last_sanitized or self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter a video URL.")
            return
        path = self.settings.get("download_path") or ""
        if not path:
            QMessageBox.warning(self, "Missing folder", "Please select a download folder.")
            return

        duplicate_kind, duplicate = self.manager.find_duplicate(url)
        if duplicate_kind == "queue":
            if QMessageBox.question(
                self, "Duplicate URL",
                f"This URL is already in the queue (status: {duplicate.get('status')}).\n\nAdd again?",
            ) != QMessageBox.Yes:
                self.url_input.clear()
                return
        elif duplicate_kind == "history":
            if QMessageBox.question(
                self, "Previously downloaded",
                "This URL was already downloaded.\n\nDownload again?",
            ) != QMessageBox.Yes:
                self.url_input.clear()
                return

        if self._preview_info is not None and self._preview_url == url:
            title = self._preview_info.get("title", "Unknown")
        else:
            title = url[:50]

        item = DownloadItem(
            url=url,
            path=path,
            resolution=self._res,
            audio_only=self.audio_pill.isChecked(),
            title=title,
        )
        self.manager.add(item)
        logger.info("Added to queue: %s", title[:50])
        self.url_input.clear()
        self.refresh()

    def start(self) -> None:
        items = self.manager.runnable_items()
        if not items:
            QMessageBox.information(self, "Queue empty", "No pending downloads in queue.")
            return
        self.manager.mark_running(items)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.runner.start(items, self.settings)
        self.refresh()

    def stop(self) -> None:
        self.runner.stop()
        count = self.manager.pause_all_running()
        logger.info("Stopped queue; paused %d item(s)", count)
        self._on_run_finished()
        self.refresh()

    def clear_completed(self) -> None:
        self.manager.clear_completed()
        self.refresh()

    def resume_item(self, item: DownloadItem) -> None:
        self._set_status(item, DownloadStatus.PENDING)
        if not self.runner.is_running():
            self.start()
        else:
            self.refresh()

    def remove_item(self, item: DownloadItem) -> None:
        index = self._index_of(item)
        if index is not None:
            self.manager.remove(index)
        self.refresh()

    def _index_of(self, item: DownloadItem) -> int | None:
        for index, candidate in enumerate(self.manager.snapshot()):
            if candidate is item:
                return index
        return None

    def _set_status(self, item: DownloadItem, status: DownloadStatus) -> None:
        if status is DownloadStatus.PENDING and item.status is DownloadStatus.PAUSED:
            index = self._index_of(item)
            if index is not None:
                self.manager.resume(index)

    def open_folder(self, item: DownloadItem) -> None:
        import os
        import subprocess
        import sys

        path = item.path
        if not path or not os.path.exists(path):
            QMessageBox.information(self, "Folder", "Download folder does not exist yet.")
            return
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])  # noqa: S603, S607
        else:
            subprocess.Popen(["xdg-open", path])  # noqa: S603, S607

    # -- runner callbacks --------------------------------------------------
    def _on_progress(self, item: DownloadItem, data: dict) -> None:
        row = self._rows.get(id(item))
        if row is not None:
            row.set_progress(float(data.get("_percent", 0.0)), data)

    def _on_item_finished(self, item: DownloadItem, message: str) -> None:
        lower = (message or "").lower()
        if "completed" in lower:
            self.manager.mark_completed(item)
            save_history({
                "url": item.url,
                "resolution": item.resolution if not item.audio_only else "Audio Only",
                "status": message,
            })
            logger.info("Download completed: %s", item.title)
            self.download_completed.emit()
        elif "cancel" in lower or "stop" in lower:
            self.manager.mark_paused(item)
            logger.info("Download paused: %s", item.title)
        else:
            self.manager.mark_failed(item)
            logger.error("Download failed: %s - %s", item.title, message)
        self.refresh()

    def _on_run_finished(self) -> None:
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.refresh()

    def _on_item_info(self, item: DownloadItem, info: dict) -> None:
        """Cache the video thumbnail once a download reports its info."""
        filename = thumb_cache.final_filename(info)
        thumb_url = info.get("thumbnail")
        if not (filename and thumb_url):
            return
        worker = ThumbWorker(item.path, filename, thumb_url, self)
        worker.finished.connect(lambda w=worker: self._thumb_workers.discard(w))
        self._thumb_workers.add(worker)
        worker.start()

    # -- rendering ---------------------------------------------------------
    def refresh(self) -> None:
        self._rows.clear()
        self._clear_layout(self.active_list)
        self._clear_layout(self.queue_list)

        items = sorted(self.manager.snapshot(), key=lambda i: STATUS_ORDER.get(i.status, 3))
        active = [i for i in items if i.status is DownloadStatus.DOWNLOADING]
        rest = [i for i in items if i.status is not DownloadStatus.DOWNLOADING]

        for item in active:
            self.active_list.addWidget(self._make_row(item))
        for item in rest:
            self.queue_list.addWidget(self._make_row(item))

        if not items:
            empty = QLabel("No downloads yet \u2014 paste a link above to get started.")
            empty.setStyleSheet(f"color: {ui_theme.color('muted')};")
            self.queue_list.addWidget(empty)

        self._update_chips()
        running = self.runner.is_running()
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)

    def _make_row(self, item: DownloadItem) -> QueueRow:
        row = QueueRow(item)
        row.open_folder.connect(self.open_folder)
        row.cancel.connect(lambda i: self.stop())
        row.resume.connect(self.resume_item)
        row.remove.connect(self.remove_item)
        self._rows[id(item)] = row
        return row

    def _update_chips(self) -> None:
        self._clear_layout(self.chips_row)
        stats = self.manager.stats()
        for label, value in (
            ("Total", stats["total"]),
            ("Pending", stats["pending"] + stats["paused"]),
            ("Active", stats["downloading"]),
            ("Done", stats["completed"]),
        ):
            chip = QLabel(f"{label}: {value}")
            chip.setObjectName("Chip")
            self.chips_row.addWidget(chip)
        self.chips_row.addStretch(1)
        self.count_changed.emit(stats["pending"] + stats["paused"])

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            child = layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                # Reparent immediately: deleteLater() alone defers removal, so
                # stale rows would overlap the ones rebuilt on the next refresh.
                widget.setParent(None)
                widget.deleteLater()
            else:
                nested = child.layout()
                if nested is not None:
                    QueuePage._clear_layout(nested)
