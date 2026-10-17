# ui/pages/media_page.py
"""Shared media browser for the Videos (grid) and Music (list) pages.

Both pages scan the download folder off the GUI thread, support search,
play, and delete. Videos render as an icon-mode grid with real thumbnails;
Music renders as a metadata list backed by mutagen.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import thumb_cache

logger = logging.getLogger(__name__)

VIDEO_EXT = (".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v")
AUDIO_EXT = (".mp3", ".m4a", ".ogg", ".flac", ".wav")


def fmt_size(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def _audio_metadata(filepath: str, filename: str) -> tuple[str, str, str]:
    """Return (title, artist, duration) using mutagen; never raises."""
    title = os.path.splitext(filename)[0]
    artist = "Unknown Artist"
    duration_str = ""
    try:
        import mutagen

        audio = mutagen.File(filepath)
        if audio is not None:
            tags = audio.tags or {}
            for key, value in tags.items():
                lowered = str(key).lower()
                if "title" in lowered and title == os.path.splitext(filename)[0]:
                    title = str(value[0]) if isinstance(value, list) else str(value)
                elif "artist" in lowered:
                    artist = str(value[0]) if isinstance(value, list) else str(value)
            length = getattr(audio.info, "length", 0)
            if length and length > 0:
                minutes, seconds = divmod(int(length), 60)
                duration_str = f"{minutes}:{seconds:02d}"
    except Exception as exc:  # noqa: BLE001 - metadata is best-effort
        logger.error("Metadata read failed for %s: %s", filename, exc)
    return title, artist, duration_str


class ScanWorker(QThread):
    """Scans a folder for media files off the GUI thread."""

    scanned = Signal(str, list)  # (folder, entries)

    def __init__(self, folder: str, extensions: tuple[str, ...], kind: str, parent=None) -> None:
        super().__init__(parent)
        self._folder = folder
        self._extensions = extensions
        self._kind = kind

    def run(self) -> None:
        entries: list[dict] = []
        folder = self._folder
        if folder and os.path.isdir(folder):
            try:
                for name in sorted(os.listdir(folder)):
                    if not name.lower().endswith(self._extensions):
                        continue
                    filepath = os.path.join(folder, name)
                    if not os.path.isfile(filepath):
                        continue
                    stat = os.stat(filepath)
                    entry = {
                        "name": name,
                        "path": filepath,
                        "size": fmt_size(stat.st_size),
                        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
                        "size_bytes": stat.st_size,
                    }
                    if self._kind == "music":
                        title, artist, duration = _audio_metadata(filepath, name)
                        entry.update(title=title, artist=artist, duration=duration)
                    entries.append(entry)
            except OSError as exc:
                logger.error("Scan failed for %s: %s", folder, exc)
        if self._kind == "music":
            entries.sort(key=lambda e: e["title"].lower())
        else:
            entries.sort(key=lambda e: e["size_bytes"], reverse=True)
        self.scanned.emit(folder, entries)


class MediaBrowser(QWidget):
    """Base list/grid page. Subclasses set the title, extensions and mode."""

    extensions: tuple[str, ...] = ()
    kind = "video"
    icon_mode = False
    empty_title = "Nothing found"
    empty_hint = "Download something to get started."

    def __init__(self, settings: dict, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._entries: list[dict] = []
        self._worker: ScanWorker | None = None
        self._build()
        self.refresh()

    # -- construction ------------------------------------------------------
    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(12)

        header = QFrame()
        header.setObjectName("Card")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 12, 14, 12)
        header_layout.setSpacing(8)

        self.path_label = QLabel("No download folder selected")
        self.path_label.setStyleSheet("font-size: 11px;")
        header_layout.addWidget(self.path_label, 1)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search\u2026")
        self.search.setFixedWidth(220)
        self.search.textChanged.connect(self._apply_filter)
        header_layout.addWidget(self.search)

        refresh = QPushButton("\u21bb")
        refresh.setToolTip("Refresh")
        refresh.setAccessibleName("Refresh")
        refresh.clicked.connect(self.refresh)
        header_layout.addWidget(refresh)
        outer.addWidget(header)

        self.list = QListWidget()
        self.list.setIconSize(QSize(160, 90))
        if self.icon_mode:
            self.list.setViewMode(QListWidget.IconMode)
            self.list.setResizeMode(QListWidget.Adjust)
            self.list.setMovement(QListWidget.Static)
            self.list.setGridSize(QSize(200, 150))
            self.list.setWordWrap(True)
        self.list.itemDoubleClicked.connect(self._play_item)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context_menu)
        outer.addWidget(self.list, 1)

        self.status = QLabel("Ready")
        self.status.setObjectName("StatusLine")
        outer.addWidget(self.status)

    # -- scanning ----------------------------------------------------------
    def refresh(self) -> None:
        folder = self.settings.get("download_path") or ""
        if not folder or not os.path.isdir(folder):
            self.path_label.setText(folder or "No download folder selected")
            self._entries = []
            self._render()
            self.status.setText("Select a download folder in the Queue tab.")
            return
        self.path_label.setText(folder)
        self.status.setText("Scanning\u2026")
        self._worker = ScanWorker(folder, self.extensions, self.kind, self)
        self._worker.scanned.connect(self._on_scanned)
        self._worker.start()

    def _on_scanned(self, folder: str, entries: list) -> None:
        if folder != (self.settings.get("download_path") or ""):
            return
        self._entries = entries
        self._render()
        self.status.setText(f"Found {len(entries)} file(s)")

    # -- rendering ---------------------------------------------------------
    def _apply_filter(self, _text: str) -> None:
        self._render()

    def _render(self) -> None:
        term = self.search.text().lower().strip()
        self.list.clear()
        shown = 0
        for entry in self._entries:
            haystack = f"{entry.get('title', '')} {entry.get('artist', '')} {entry['name']}".lower()
            if term and term not in haystack:
                continue
            self.list.addItem(self._make_item(entry))
            shown += 1
        if shown == 0:
            placeholder = QListWidgetItem(f"{self.empty_title} \u2014 {self.empty_hint}")
            placeholder.setFlags(Qt.NoItemFlags)
            self.list.addItem(placeholder)

    def _make_item(self, entry: dict) -> QListWidgetItem:
        if self.kind == "music":
            text = f"{entry['title']}  \u00b7  {entry['artist']}  \u00b7  {entry.get('duration') or '--'}  \u00b7  {entry['size']}"
        else:
            text = entry["name"]
        item = QListWidgetItem(text)
        item.setData(Qt.UserRole, entry["path"])
        item.setToolTip(f"{entry['name']}\n{entry['size']} \u00b7 {entry['modified']}")
        item.setIcon(QIcon(self._icon_for(entry)))
        return item

    def _icon_for(self, entry: dict) -> QPixmap:
        if self.kind == "video":
            thumb = thumb_cache.local_path(self.settings.get("download_path", ""), entry["name"])
            if thumb:
                pixmap = QPixmap(thumb)
                if not pixmap.isNull():
                    return pixmap.scaled(160, 90, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        asset = "assets/video.png" if self.kind == "video" else "assets/music.png"
        pixmap = QPixmap(asset)
        return pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation) if not pixmap.isNull() else QPixmap()

    # -- lifecycle ---------------------------------------------------------
    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().showEvent(event)
        self.refresh()

    # -- actions -----------------------------------------------------------
    def _play_item(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.UserRole)
        if path:
            self._play(path)

    def _context_menu(self, pos) -> None:
        item = self.list.itemAt(pos)
        if item is None or item.data(Qt.UserRole) is None:
            return
        path = item.data(Qt.UserRole)
        menu = QMenu(self)
        play = menu.addAction("Play")
        delete = menu.addAction("Delete")
        chosen = menu.exec(self.list.mapToGlobal(pos))
        if chosen is play:
            self._play(path)
        elif chosen is delete:
            self._delete(path)

    def _play(self, path: str) -> None:
        if not os.path.exists(path):
            QMessageBox.warning(self, "Missing file", "That file no longer exists.")
            self.refresh()
            return
        try:
            from utils import detect_vlc

            vlc = detect_vlc()
            if vlc:
                subprocess.Popen([vlc, path])  # noqa: S603
            elif sys.platform == "win32":
                os.startfile(path)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])  # noqa: S603, S607
            else:
                subprocess.Popen(["xdg-open", path])  # noqa: S603, S607
            self.status.setText(f"Playing: {Path(path).name}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Play failed", str(exc))

    def _delete(self, path: str) -> None:
        name = Path(path).name
        confirm = QMessageBox.question(
            self, "Delete file", f"Delete '{name}'?\n\nThis cannot be undone.",
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            os.remove(path)
            self.status.setText(f"Deleted: {name}")
            self.refresh()
        except OSError as exc:
            QMessageBox.warning(self, "Delete failed", str(exc))
