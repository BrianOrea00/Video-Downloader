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

from PySide6.QtCore import QSize, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import thumb_cache
from persistence import save_settings
from ui import icons
from ui.theme import METRICS, px
from utils import resource_path

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
                        "mtime": stat.st_mtime,
                        "size_bytes": stat.st_size,
                    }
                    if self._kind == "music":
                        title, artist, duration = _audio_metadata(filepath, name)
                        entry.update(title=title, artist=artist, duration=duration)
                    entries.append(entry)
            except OSError as exc:
                logger.error("Scan failed for %s: %s", folder, exc)
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
        outer.setContentsMargins(px(24), px(20), px(24), px(20))
        outer.setSpacing(px(12))

        header = QFrame()
        header.setObjectName("Card")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(px(14), px(12), px(14), px(12))
        header_layout.setSpacing(px(8))

        self.path_label = QLabel("No download folder selected")
        self.path_label.setObjectName("PathLabel")
        header_layout.addWidget(self.path_label, 1)

        self.sort = QComboBox()
        for label, key in (("Newest", "newest"), ("Oldest", "oldest"),
                           ("Largest", "largest"), ("Name", "name")):
            self.sort.addItem(label, key)
        index = self.sort.findData(self.settings.get("library_sort", "newest"))
        if index >= 0:
            self.sort.setCurrentIndex(index)
        self.sort.setAccessibleName("Sort order")
        self.sort.currentIndexChanged.connect(self._on_sort_changed)
        header_layout.addWidget(self.sort)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search\u2026")
        self.search.setFixedWidth(px(METRICS["search_width"]))
        self.search.setAccessibleName("Search the library")
        self.search.textChanged.connect(self._apply_filter)
        header_layout.addWidget(self.search)

        refresh = QPushButton()
        refresh.setIcon(icons.icon("refresh", 16, "text"))
        refresh.setIconSize(QSize(px(16), px(16)))
        refresh.setToolTip("Refresh")
        refresh.setAccessibleName("Refresh")
        refresh.clicked.connect(self.refresh)
        header_layout.addWidget(refresh)

        # Selection actions stay visible; the context menu is a shortcut, not
        # the only way to reach them.
        self.play_btn = self._action_button("player-play", "Play", self._play_selected)
        self.reveal_btn = self._action_button("folder", "Show in folder", self._reveal_selected)
        self.delete_btn = self._action_button("trash", "Delete", self._delete_selected)
        for button in (self.play_btn, self.reveal_btn, self.delete_btn):
            header_layout.addWidget(button)
        outer.addWidget(header)

        self.list = QListWidget()
        # Long names elide with an ellipsis; the full name stays in the tooltip.
        self.list.setTextElideMode(Qt.ElideRight)
        self.list.setIconSize(
            QSize(px(METRICS["grid_icon_w"]), px(METRICS["grid_icon_h"])))
        if self.icon_mode:
            self.list.setViewMode(QListWidget.IconMode)
            self.list.setResizeMode(QListWidget.Adjust)
            self.list.setMovement(QListWidget.Static)
            self.list.setGridSize(
                QSize(px(METRICS["grid_cell_w"]), px(METRICS["grid_cell_h"])))
            self.list.setWordWrap(False)
        self.list.itemDoubleClicked.connect(self._play_item)
        self.list.itemSelectionChanged.connect(self._sync_actions)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context_menu)

        self.body = QStackedWidget()
        self.body.addWidget(self.list)
        self.body.addWidget(self._empty_panel())
        outer.addWidget(self.body, 1)

        self.status = QLabel("")
        self.status.setObjectName("StatusLine")
        outer.addWidget(self.status)
        self._sync_actions()

    def _action_button(self, asset: str, tip: str, slot) -> QPushButton:
        button = QPushButton()
        button.setIcon(icons.icon(asset, 16, "text"))
        button.setIconSize(QSize(px(16), px(16)))
        button.setToolTip(tip)
        button.setAccessibleName(tip)
        button.clicked.connect(slot)
        return button

    def _empty_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(px(8))
        asset = "video" if self.kind == "video" else "music"
        icon_label = QLabel()
        icon_label.setPixmap(icons.pixmap(asset, 32, "muted"))
        icon_label.setAlignment(Qt.AlignCenter)
        title = QLabel(self.empty_title)
        title.setObjectName("FieldLabel")
        title.setAlignment(Qt.AlignCenter)
        self._empty_hint = QLabel(self.empty_hint)
        self._empty_hint.setObjectName("FormHelp")
        self._empty_hint.setAlignment(Qt.AlignCenter)
        self._empty_hint.setWordWrap(True)
        layout.addWidget(icon_label)
        layout.addWidget(title)
        layout.addWidget(self._empty_hint)
        return panel

    # -- sorting -----------------------------------------------------------
    def _on_sort_changed(self) -> None:
        self.settings["library_sort"] = self.sort.currentData()
        save_settings(self.settings)
        self._render()

    def _sorted_entries(self) -> list[dict]:
        key = self.sort.currentData() or "newest"
        entries = list(self._entries)
        if key == "oldest":
            entries.sort(key=lambda e: e.get("mtime", 0.0))
        elif key == "largest":
            entries.sort(key=lambda e: e.get("size_bytes", 0), reverse=True)
        elif key == "name":
            entries.sort(key=lambda e: (e.get("title") or e["name"]).lower())
        else:
            entries.sort(key=lambda e: e.get("mtime", 0.0), reverse=True)
        return entries

    # -- scanning ----------------------------------------------------------
    def refresh(self) -> None:
        folder = self.settings.get("download_path") or ""
        if not folder or not os.path.isdir(folder):
            self.path_label.setText(folder or "No download folder selected")
            self._entries = []
            self._render()
            return
        self.path_label.setText(folder)
        self._set_status("Scanning\u2026")
        self._worker = ScanWorker(folder, self.extensions, self.kind, self)
        self._worker.scanned.connect(self._on_scanned)
        self._worker.start()

    def _on_scanned(self, folder: str, entries: list) -> None:
        if folder != (self.settings.get("download_path") or ""):
            return
        self._entries = entries
        self._render()

    # -- rendering ---------------------------------------------------------
    def _apply_filter(self, _text: str) -> None:
        self._render()

    def _set_status(self, text: str) -> None:
        self.status.setText(text)

    def _render(self) -> None:
        term = self.search.text().lower().strip()
        self.list.clear()
        shown = 0
        total = 0
        for entry in self._sorted_entries():
            haystack = f"{entry.get('title', '')} {entry.get('artist', '')} {entry['name']}".lower()
            if term and term not in haystack:
                continue
            self.list.addItem(self._make_item(entry))
            shown += 1
            total += entry.get("size_bytes", 0)

        self.body.setCurrentIndex(0 if shown else 1)
        folder = self.settings.get("download_path") or ""
        if not folder:
            self._empty_hint.setText("Select a download folder in the Queue tab.")
        else:
            self._empty_hint.setText(self.empty_hint)

        if not folder:
            self._set_status("No download folder selected.")
        elif shown:
            noun = "video" if self.kind == "video" else "track"
            plural = "" if shown == 1 else "s"
            self._set_status(f"{shown} {noun}{plural} \u00b7 {fmt_size(total)}")
        elif term:
            self._set_status(f"No match for \u201c{self.search.text().strip()}\u201d.")
        else:
            self._set_status("Folder is empty.")
        self._sync_actions()

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
        name = "assets/video.png" if self.kind == "video" else "assets/music.png"
        asset = resource_path(name)
        pixmap = QPixmap(asset)
        return pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation) if not pixmap.isNull() else QPixmap()

    # -- lifecycle ---------------------------------------------------------
    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().showEvent(event)
        self.refresh()

    # -- actions -----------------------------------------------------------
    def _selected_path(self) -> str:
        item = self.list.currentItem()
        return (item.data(Qt.UserRole) or "") if item is not None else ""

    def _sync_actions(self) -> None:
        enabled = bool(self._selected_path())
        for button in (self.play_btn, self.reveal_btn, self.delete_btn):
            button.setEnabled(enabled)

    def _play_item(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.UserRole)
        if path:
            self._play(path)

    def _play_selected(self) -> None:
        path = self._selected_path()
        if path:
            self._play(path)

    def _reveal_selected(self) -> None:
        path = self._selected_path()
        if path:
            self._reveal(path)

    def _delete_selected(self) -> None:
        path = self._selected_path()
        if path:
            self._delete(path)

    def _context_menu(self, pos) -> None:
        item = self.list.itemAt(pos)
        if item is None or item.data(Qt.UserRole) is None:
            return
        path = item.data(Qt.UserRole)
        menu = QMenu(self)
        play = menu.addAction("Play")
        reveal = menu.addAction("Show in folder")
        delete = menu.addAction("Delete")
        chosen = menu.exec(self.list.mapToGlobal(pos))
        if chosen is play:
            self._play(path)
        elif chosen is reveal:
            self._reveal(path)
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
            self._set_status(f"Playing: {Path(path).name}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Play failed", str(exc))

    def _reveal(self, path: str) -> None:
        folder = os.path.dirname(path)
        if not os.path.isdir(folder):
            QMessageBox.warning(self, "Missing folder", "That folder no longer exists.")
            self.refresh()
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def _delete(self, path: str) -> None:
        name = Path(path).name
        confirm = QMessageBox.question(
            self, "Delete file", f"Delete '{name}'?\n\nThis cannot be undone.",
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            os.remove(path)
            self.refresh()
        except OSError as exc:
            QMessageBox.warning(self, "Delete failed", str(exc))

