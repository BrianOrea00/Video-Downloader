# ui/pages/queue_page.py
"""Download Console page: add URL, preview, live per-row progress, start/stop.

Mirrors ``docs/ui-prototype.html`` (#page-queue). State lives in
:class:`queue_manager.QueueManager`; downloads run in :class:`queue_runner.QueueRunner`.
"""
from __future__ import annotations

import logging
import os
from urllib.parse import urlparse

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QSize,
    Qt,
    QThread,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import QDesktopServices, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import thumb_cache
from config import RESOLUTIONS
from downloader import Downloader
from models import DownloadItem, DownloadStatus
from persistence import save_history
from queue_manager import QueueManager
from queue_runner import QueueRunner
from ui import icons
from ui import theme as ui_theme
from ui.theme import METRICS, px, repolish
from url_validator import validate_url
from utils import ffmpeg_available

logger = logging.getLogger(__name__)

STATUS_META = {
    DownloadStatus.PENDING: ("Pending", "muted"),
    DownloadStatus.DOWNLOADING: ("Downloading", "accent"),
    DownloadStatus.PAUSED: ("Paused", "warning"),
    DownloadStatus.COMPLETED: ("Completed", "success"),
    DownloadStatus.FAILED: ("Failed", "error"),
}
# Rough video bitrate per resolution (kbps) for the "Will download" estimate.
RESOLUTION_KBPS = {
    "144": 120, "240": 300, "360": 600,
    "480": 1200, "720": 2500, "1080": 4500,
}
AUDIO_KBPS = 192
AUDIO_TRACK_KBPS = 128
# Visual grouping only: downloading first, runnable next in run order, done
# last. Sorting pending and paused separately would misrepresent run order.
STATUS_RANK = {
    DownloadStatus.DOWNLOADING: 0,
    DownloadStatus.PENDING: 1,
    DownloadStatus.PAUSED: 1,
    DownloadStatus.COMPLETED: 2,
    DownloadStatus.FAILED: 2,
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


class ElidedLabel(QLabel):
    """Single-line label that elides in the middle instead of forcing width.

    The full text stays available as the tooltip and through :meth:`fullText`.
    """

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(parent)
        self._full = ""
        self.setWordWrap(False)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setText(text)

    def setText(self, text: str) -> None:
        self._full = text or ""
        self.setToolTip(self._full)
        self._render_elided()

    def fullText(self) -> str:
        return self._full

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._render_elided()

    def _render_elided(self) -> None:
        if not self._full:
            return
        width = self.width()
        if width <= 0:
            super().setText(self._full)
            return
        super().setText(self.fontMetrics().elidedText(self._full, Qt.ElideMiddle, width))


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


class PreviewThumbWorker(QThread):
    """Fetches a preview thumbnail off the GUI thread; emits raw image bytes."""

    fetched = Signal(object)  # bytes | None

    def __init__(self, thumb_url: str, parent=None) -> None:
        super().__init__(parent)
        self._url = thumb_url

    def run(self) -> None:
        self.fetched.emit(thumb_cache.fetch(self._url))


class QueueRow(QFrame):
    """One queue line: tile, title, chips, progress, stats, actions."""

    open_folder = Signal(object)
    cancel = Signal(object)
    resume = Signal(object)
    remove = Signal(object)
    play = Signal(object)
    pressed = Signal(object)
    move_up = Signal(object)
    move_down = Signal(object)

    def __init__(self, item: DownloadItem, parent=None) -> None:
        super().__init__(parent)
        self.item = item
        self._selected = False
        self._active = False
        self._can_up = True
        self._can_down = True
        self.setObjectName("Row")
        self.setCursor(Qt.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(px(12), px(10), px(12), px(10))
        row.setSpacing(px(12))

        self.tile = QLabel()
        self.tile.setObjectName("RowTile")
        self.tile.setFixedSize(px(METRICS["row_tile_w"]), px(METRICS["row_tile_h"]))
        self.tile.setAlignment(Qt.AlignCenter)
        row.addWidget(self.tile)

        main = QVBoxLayout()
        main.setSpacing(px(3))
        self.title_label = ElidedLabel()
        main.addWidget(self.title_label)

        meta = QHBoxLayout()
        meta.setSpacing(px(6))
        self.res_chip = _chip("")
        meta.addWidget(self.res_chip)
        self.status_label = QLabel()
        meta.addWidget(self.status_label)
        meta.addStretch(1)
        main.addLayout(meta)

        self.reason = ElidedLabel("")
        self.reason.setVisible(False)
        main.addWidget(self.reason)

        self.progress = QProgressBar()
        self.progress.setObjectName("RowProgress")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)   # Qt defaults to -1, which animates as a flash
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(px(METRICS["row_progress"]))
        main.addWidget(self.progress)

        self.stats = QLabel("")
        self.stats.setStyleSheet(
            f"{ui_theme.mono_css()} color: {ui_theme.color('gray_light')};"
            f" font-size: {ui_theme.px(11)}px;"
        )
        self.stats.setVisible(False)
        main.addWidget(self.stats)

        row.addLayout(main, 1)

        self.actions = QHBoxLayout()
        self.actions.setSpacing(px(6))
        row.addLayout(self.actions)

        self.update_item(item)

    def set_selected(self, selected: bool) -> None:
        """Selection is visual only; it drives the Delete shortcut."""
        if self._selected == selected:
            return
        self._selected = selected
        self._apply_state()

    def _apply_state(self) -> None:
        """One owner for the row's dynamic object name.

        Object names are exclusive, so selection has to be merged here rather
        than set by two independent call sites.
        """
        name = "RowSelected" if self._selected else ("RowActive" if self._active else "Row")
        if self.objectName() != name:
            self.setObjectName(name)
            repolish(self)

    def update_item(self, item: DownloadItem) -> None:
        """Repaint an existing row in place; keeps focus instead of rebuilding."""
        self.item = item
        active = item.status is DownloadStatus.DOWNLOADING
        self._active = active
        self._apply_state()

        self.tile.setPixmap(icons.pixmap(
            "music" if item.audio_only else "video", 16,
            "muted" if item.status is DownloadStatus.COMPLETED else "gray_light",
        ))
        self.title_label.setText(item.title)
        style = f"color: {ui_theme.color('muted')};" if item.status is DownloadStatus.COMPLETED else ""
        self.title_label.setStyleSheet(style)
        self.res_chip.setText("MP3" if item.audio_only else f"{item.resolution}p")

        label, token = STATUS_META.get(item.status, STATUS_META[DownloadStatus.PENDING])
        self.status_label.setText(f"\u25cf {label}")
        self.status_label.setStyleSheet(
            f"color: {ui_theme.color(token)}; font-size: {ui_theme.px(10)}px;"
        )

        failed = item.status is DownloadStatus.FAILED and bool(item.message)
        self.reason.setVisible(failed)
        if failed:
            self.reason.setText(item.message)
            self.reason.setStyleSheet(
                f"color: {ui_theme.color('error')}; font-size: {ui_theme.px(10)}px;"
            )

        self.progress.setVisible(active)
        if not active:
            self.stats.setVisible(False)

        self._rebuild_actions()

    def _rebuild_actions(self) -> None:
        while self.actions.count():
            child = self.actions.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        item = self.item
        if item.status is DownloadStatus.COMPLETED and item.filename:
            self.actions.addWidget(self._text_button(
                "Play", "Play file", lambda: self.play.emit(self.item)))
        self.actions.addWidget(self._icon_button(
            "folder", "Open folder", lambda: self.open_folder.emit(self.item)))
        if item.status is DownloadStatus.DOWNLOADING:
            self.actions.addWidget(self._icon_button(
                "x", "Cancel this download", lambda: self.cancel.emit(self.item)))
        if item.status is DownloadStatus.PAUSED:
            self.actions.addWidget(self._text_button(
                "Resume", "Resume download", lambda: self.resume.emit(self.item)))
        if item.status is DownloadStatus.FAILED:
            self.actions.addWidget(self._text_button(
                "Retry", "Retry download", lambda: self.resume.emit(self.item)))
        if item.status in (DownloadStatus.PENDING, DownloadStatus.PAUSED):
            self.move_up_btn = self._icon_button(
                "arrow-move-up", "Move up", lambda: self.move_up.emit(self.item))
            self.move_down_btn = self._icon_button(
                "arrow-move-down", "Move down", lambda: self.move_down.emit(self.item))
            self.actions.addWidget(self.move_up_btn)
            self.actions.addWidget(self.move_down_btn)
        self.actions.addWidget(self._text_button(
            "Remove", "Remove from queue (the file is kept)",
            lambda: self.remove.emit(self.item)))
        self.set_move_enabled(self._can_up, self._can_down)

    def set_move_enabled(self, up: bool, down: bool) -> None:
        """Called by the page, which is the only place that knows the order."""
        self._can_up = up
        self._can_down = down
        if hasattr(self, "move_up_btn"):
            self.move_up_btn.setEnabled(up)
        if hasattr(self, "move_down_btn"):
            self.move_down_btn.setEnabled(down)

    def _icon_button(self, asset: str, tip: str, slot) -> QPushButton:
        button = QPushButton()
        button.setIcon(icons.icon(asset, 16, "text"))
        button.setIconSize(QSize(px(16), px(16)))
        button.setFixedSize(px(METRICS["row_action"]), px(METRICS["row_action"]))
        button.setToolTip(tip)
        button.setAccessibleName(tip)
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(slot)
        return button

    def _text_button(self, text: str, tip: str, slot) -> QPushButton:
        button = QPushButton(text)
        button.setToolTip(tip)
        button.setAccessibleName(tip)
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(slot)
        return button

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.LeftButton:
            self.pressed.emit(self.item)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self.item.status is DownloadStatus.COMPLETED and self.item.filename:
            self.play.emit(self.item)
        super().mouseDoubleClickEvent(event)

    def _progress_animation(self) -> QPropertyAnimation:
        animation = getattr(self, "_progress_anim", None)
        if animation is None:
            animation = QPropertyAnimation(self.progress, b"value", self)
            animation.setDuration(150)   # short: it reports, it does not perform
            animation.setEasingCurve(QEasingCurve.Linear)
            self._progress_anim = animation
        return animation

    def set_progress(self, percent: float, data: dict) -> None:
        self.progress.setVisible(True)
        self.stats.setVisible(True)
        target = int(max(0.0, min(100.0, percent)))
        if ui_theme.motion_enabled() and self.progress.value() != target:
            animation = self._progress_animation()
            animation.stop()
            animation.setStartValue(self.progress.value())
            animation.setEndValue(target)
            animation.start()
        else:
            self.progress.setValue(target)
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
        self._empty_box: QWidget | None = None
        self._preview_info: dict | None = None
        self._preview_url: str | None = None
        self._info_worker: InfoWorker | None = None
        self._thumb_workers: set[ThumbWorker] = set()
        self._preview_workers: set[PreviewThumbWorker] = set()
        self._last_sanitized: str | None = None
        self._selected: DownloadItem | None = None
        self._last_clipboard = ""

        self.manager.load()
        self._build()

        self.runner.progress.connect(self._on_progress)
        self.runner.item_finished.connect(self._on_item_finished)
        self.runner.item_info.connect(self._on_item_info)
        self.runner.run_finished.connect(self._on_run_finished)

        self.refresh()
        self._wire_shortcuts()

        self._clipboard_timer = QTimer(self)
        self._clipboard_timer.timeout.connect(self._poll_clipboard)
        self._apply_clipboard_settings()

    def _wire_shortcuts(self) -> None:
        """Keyboard parity: every primary action has a key.

        The shortcuts use the default ``WindowShortcut`` context, so a modal
        dialog (which is its own window) does not let them fire underneath.
        """
        self.url_input.returnPressed.connect(self.add_to_queue)
        for sequence, slot in (
            ("Ctrl+Return", self.start),
            ("Ctrl+Enter", self.start),
            ("Ctrl+.", self.stop),
            ("Esc", self._escape),
            ("Delete", self._delete_selected),
        ):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(slot)

        # Explicit order: the URL field, then its actions, then the options,
        # then the queue controls. Rows follow in visual order.
        chain = (
            self.url_input, self.paste_btn, self.add_btn, self.audio_pill,
            self.browse_btn, self.start_btn, self.stop_btn, self.clear_btn,
        )
        for first, second in zip(chain, chain[1:], strict=False):
            QWidget.setTabOrder(first, second)

    def _clear_input(self) -> None:
        self.url_input.clear()
        self._hide_preview()
        self.url_input.setFocus()

    def _escape(self) -> None:
        """Esc drops the row selection first, then the URL field."""
        if self._selected is not None:
            self._set_selected(None)
        else:
            self._clear_input()

    def _set_selected(self, item: DownloadItem | None) -> None:
        self._selected = item
        for row in self._rows.values():
            row.set_selected(item is not None and row.item is item)

    def _delete_selected(self) -> None:
        """Delete removes the selected row; the file on disk is untouched."""
        item = self._selected
        if item is None:
            self._notify("Select a row first \u2014 click it, then press Delete.")
            return
        if item.status is DownloadStatus.DOWNLOADING:
            self._notify("Stop that download before removing it.", "error")
            return
        if self._confirm_remove(item):
            self._set_selected(None)
            self.remove_item(item)

    def _ask(self, title: str, text: str, accept_label: str) -> bool:
        """Decision prompt with named buttons, so the choice is never Yes/No."""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle(title)
        box.setText(text)
        accept = box.addButton(accept_label, QMessageBox.AcceptRole)
        cancel = box.addButton("Cancel", QMessageBox.RejectRole)
        box.setDefaultButton(cancel)
        box.exec()
        return box.clickedButton() is accept

    def _confirm_remove(self, item: DownloadItem) -> bool:
        """Destructive, so it is the one place a modal is still right."""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Remove from queue")
        box.setText(f"Remove \u201c{item.title}\u201d from the queue?")
        box.setInformativeText("The downloaded file is kept on disk.")
        remove = box.addButton("Remove", QMessageBox.DestructiveRole)
        box.addButton("Cancel", QMessageBox.RejectRole)
        box.setDefaultButton(box.buttons()[-1])
        box.exec()
        return box.clickedButton() is remove

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        container = QWidget()
        scroll.setWidget(container)
        # Fluid like the Videos/Music/Settings pages: the column fills the
        # viewport instead of a fixed content width, and long text elides.
        col = QVBoxLayout(container)
        col.setContentsMargins(px(24), px(20), px(24), px(20))
        col.setSpacing(px(16))

        col.addWidget(self._build_input_card())
        col.addWidget(self._build_banner())

        self.chips_row = QHBoxLayout()
        self.chips_row.setSpacing(px(8))
        col.addLayout(self.chips_row)

        self.active_section = self._section("Active")
        col.addWidget(self.active_section)
        self.active_list = QVBoxLayout()
        self.active_list.setSpacing(px(8))
        col.addLayout(self.active_list)

        self.queue_section = self._section("Queue")
        col.addWidget(self.queue_section)
        self.queue_list = QVBoxLayout()
        self.queue_list.setSpacing(px(8))
        col.addLayout(self.queue_list)

        col.addLayout(self._build_actions())
        col.addStretch(1)

    def _section(self, text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setObjectName("FieldLabel")
        return label

    def _build_banner(self) -> QWidget:
        """Inline status line: success and routine information never modal."""
        self.banner = QFrame()
        self.banner.setObjectName("Card")
        self.banner.setVisible(False)
        layout = QHBoxLayout(self.banner)
        layout.setContentsMargins(px(12), px(8), px(12), px(8))
        layout.setSpacing(px(8))
        self.banner_label = QLabel("")
        self.banner_label.setWordWrap(True)
        self.banner_label.setAccessibleName("Status message")
        layout.addWidget(self.banner_label, 1)
        dismiss = QPushButton("Dismiss")
        dismiss.clicked.connect(lambda: self.banner.setVisible(False))
        layout.addWidget(dismiss)
        self._banner_timer = QTimer(self)
        self._banner_timer.setSingleShot(True)
        self._banner_timer.timeout.connect(lambda: self.banner.setVisible(False))
        return self.banner

    def _notify(self, text: str, level: str = "info") -> None:
        token = {"info": "text_2", "error": "error", "success": "success"}[level]
        self.banner_label.setText(text)
        self.banner_label.setStyleSheet(
            f"color: {ui_theme.color(token)}; font-size: {ui_theme.px(11)}px;"
        )
        self.banner.setVisible(True)
        self._banner_timer.start(8000)

    def _build_input_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(px(14), px(14), px(14), px(14))
        layout.setSpacing(px(12))

        field = QLabel("ADD URL")
        field.setObjectName("FieldLabel")
        layout.addWidget(field)

        input_row = QHBoxLayout()
        input_row.setSpacing(px(8))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://youtube.com/watch?v=...")
        self.url_input.setClearButtonEnabled(True)
        self.url_input.textChanged.connect(self._on_url_changed)
        input_row.addWidget(self.url_input, 1)

        self.paste_btn = QPushButton("Paste")
        self.paste_btn.clicked.connect(self.paste)
        input_row.addWidget(self.paste_btn)

        self.add_btn = QPushButton("Add to Queue")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.clicked.connect(self.add_to_queue)
        input_row.addWidget(self.add_btn)
        layout.addLayout(input_row)

        self.validity_label = QLabel("")
        self.validity_label.setObjectName("FormHelp")
        self.validity_label.setWordWrap(True)
        self.validity_label.setVisible(False)
        layout.addWidget(self.validity_label)

        pills = QHBoxLayout()
        pills.setSpacing(px(6))
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
        layout.addLayout(pills)

        path_row = QHBoxLayout()
        path_row.setSpacing(px(8))
        self.path_label = ElidedLabel(
            self.settings.get("download_path") or "Select download folder\u2026"
        )
        self.path_label.setStyleSheet(
            f"{ui_theme.mono_css()} color: {ui_theme.color('muted')};"
            f" font-size: {ui_theme.px(11)}px;"
        )
        path_row.addWidget(self.path_label, 1)
        self.audio_pill = QPushButton("Audio Only")
        self.audio_pill.setObjectName("Pill")
        self.audio_pill.setCheckable(True)
        self.audio_pill.setCursor(Qt.PointingHandCursor)
        self.audio_pill.toggled.connect(lambda _=False: self._update_preview_meta())
        self._ffmpeg = ffmpeg_available()
        self.audio_pill.setChecked(
            self._ffmpeg and bool(self.settings.get("default_audio_only", False))
        )
        if not self._ffmpeg:
            self.audio_pill.setEnabled(False)
            self.audio_pill.setToolTip(
                "ffmpeg was not found on PATH. Audio-only and MP4 merging need it."
            )
        path_row.addWidget(self.audio_pill)
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse)
        path_row.addWidget(self.browse_btn)
        layout.addLayout(path_row)

        self.preview = QFrame()
        self.preview.setObjectName("PreviewCard")
        self.preview.setVisible(False)
        self.preview_layout = QHBoxLayout(self.preview)
        self.preview_layout.setContentsMargins(px(10), px(10), px(10), px(10))
        self.preview_layout.setSpacing(px(12))
        layout.addWidget(self.preview)
        return card

    def _build_actions(self) -> QHBoxLayout:
        actions = QHBoxLayout()
        actions.setSpacing(px(8))
        self.start_btn = QPushButton("Start Queue")
        self.start_btn.setObjectName("PrimaryButton")
        self.start_btn.clicked.connect(self.start)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("DangerButton")
        self.stop_btn.setIcon(icons.icon("player-pause", 16, "error"))
        self.stop_btn.setIconSize(QSize(px(16), px(16)))
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop)
        self.clear_btn = QPushButton("Clear Completed")
        self.clear_btn.clicked.connect(self.clear_completed)
        actions.addWidget(self.start_btn)
        actions.addWidget(self.stop_btn)
        actions.addWidget(self.clear_btn)
        actions.addStretch(1)
        hint = QLabel("Enter adds \u00b7 Ctrl+\u21b5 starts")
        hint.setObjectName("FormHelp")
        actions.addWidget(hint)
        return actions

    # -- input handlers ----------------------------------------------------
    def _set_validity(self, message: str, key: str | None) -> None:
        """Inline validation text, so validity is never colour-only."""
        if not message or key is None:
            self.validity_label.clear()
            self.validity_label.setVisible(False)
            self.url_input.setAccessibleDescription("")
            return
        self.validity_label.setText(message)
        self.validity_label.setStyleSheet(
            f"color: {ui_theme.color(key)}; font-size: {ui_theme.px(11)}px;"
        )
        self.validity_label.setVisible(True)
        self.url_input.setAccessibleDescription(message)

    def _on_url_changed(self, text: str) -> None:
        text = text.strip()
        if not text:
            self._hide_preview()
            self.url_input.setStyleSheet("")
            self._set_validity("", None)
            self._last_sanitized = None
            return
        result = validate_url(text)
        host = urlparse(result["sanitized"]).hostname or "supported site"
        if result["valid"]:
            self._last_sanitized = result["sanitized"]
            self.url_input.setStyleSheet(f"border: 1px solid {ui_theme.color('success')};")
            self._set_validity(f"\u2713 Recognised link \u2014 {host}", "success")
            self._fetch_preview(result["sanitized"])
        else:
            self._last_sanitized = None
            self.url_input.setStyleSheet(f"border: 1px solid {ui_theme.color('error')};")
            self._set_validity(
                "\u2715 Not a supported link \u2014 paste a YouTube or yt-dlp-supported URL",
                "error",
            )
            self._hide_preview()

    def set_resolution(self, res: str) -> None:
        self._res = res
        button = self._res_buttons.get(res)
        if button is not None:
            button.setChecked(True)
        self._update_preview_meta()

    def apply_defaults(self) -> None:
        """Re-apply values from Settings that affect the input bar."""
        res = self.settings.get("default_resolution", "720")
        if res in self._res_buttons:
            self.set_resolution(res)
        self.audio_pill.setChecked(
            self._ffmpeg and bool(self.settings.get("default_audio_only", False))
        )
        self._apply_clipboard_settings()

    # -- clipboard auto-detection ------------------------------------------
    def _apply_clipboard_settings(self) -> None:
        """Arm or disarm the poller from the current settings, immediately."""
        interval = int(self.settings.get("clipboard_interval", 1000) or 1000)
        self._clipboard_timer.setInterval(max(250, interval))
        if self.settings.get("auto_clipboard", False):
            self._clipboard_timer.start()
        else:
            self._clipboard_timer.stop()

    def _poll_clipboard(self) -> None:
        """Fill the URL field when a supported link is copied.

        Skipped while the user is typing in the field or a preview fetch is in
        flight, and every distinct clipboard value is only considered once.
        """
        from PySide6.QtWidgets import QApplication

        text = (QApplication.clipboard().text() or "").strip()
        if not text or text == self._last_clipboard:
            return
        # Do not remember a value we skipped on purpose, or the link copied
        # while the field had focus would never be picked up afterwards.
        if self.url_input.hasFocus():
            return
        if self._info_worker is not None and self._info_worker.isRunning():
            return
        self._last_clipboard = text
        result = validate_url(text)
        if not result["valid"] or result["sanitized"] == self._last_sanitized:
            return
        self.url_input.setText(result["sanitized"])
        self._notify("Filled the link from your clipboard.")

    def paste(self) -> None:
        from PySide6.QtWidgets import QApplication

        text = (QApplication.clipboard().text() or "").strip()
        if text:
            self.url_input.setText(text)
        else:
            self._notify("Clipboard is empty.")

    def browse(self) -> None:
        start = self.settings.get("download_path") or ""
        folder = QFileDialog.getExistingDirectory(self, "Select download folder", start)
        if folder:
            self.settings["download_path"] = folder
            self.path_label.setText(folder)
            self.path_label.setStyleSheet(f"color: {ui_theme.color('text')}; font-size: {ui_theme.px(11)}px;")

    # -- link preview ------------------------------------------------------
    def _fetch_preview(self, url: str) -> None:
        if self._info_worker is not None and self._info_worker.isRunning():
            return
        self.add_btn.setEnabled(False)
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
        self.add_btn.setEnabled(True)
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
        spinner = QProgressBar()
        spinner.setRange(0, 0)   # indeterminate busy indicator
        spinner.setTextVisible(False)
        spinner.setFixedWidth(px(60))
        spinner.setFixedHeight(px(4))
        self.preview_layout.addWidget(spinner)
        label = QLabel(text)
        label.setStyleSheet(f"color: {ui_theme.color('muted')};")
        self.preview_layout.addWidget(label, 1)
        self.preview.setVisible(True)

    def _show_preview(self, info) -> None:
        if not info:
            self._hide_preview()

    def _hide_preview(self) -> None:
        self.add_btn.setEnabled(True)
        self.preview.setVisible(False)
        self._clear_layout(self.preview_layout)
        self._preview_info = None
        self._preview_url = None

    def _render_preview(self, info: dict) -> None:
        self._clear_layout(self.preview_layout)
        duration = _fmt_duration(info.get("duration"))

        thumb = QLabel()
        thumb.setObjectName("RowTile")
        thumb.setFixedSize(px(METRICS["row_thumb_w"]), px(METRICS["row_thumb_h"]))
        thumb.setAlignment(Qt.AlignCenter)
        thumb.setPixmap(icons.pixmap("player-play", 20, "muted"))
        self.preview_layout.addWidget(thumb)
        self._load_preview_thumb(info, thumb)
        if duration:
            badge = QLabel(duration, thumb)
            badge.setObjectName("Chip")
            badge.setStyleSheet(
                f"{ui_theme.mono_css()} font-size: {ui_theme.px(10)}px;"
                f" padding: 0 {ui_theme.px(4)}px;"
            )
            badge.adjustSize()
            badge.move(
                thumb.width() - badge.width() - px(4),
                thumb.height() - badge.height() - px(4),
            )

        body = QVBoxLayout()
        body.setSpacing(px(4))
        title = ElidedLabel(info.get("title", "Unknown"))
        title.setStyleSheet("font-weight: 600;")
        body.addWidget(title)
        chips = QHBoxLayout()
        chips.setSpacing(px(6))
        channel = info.get("uploader") or info.get("channel")
        if channel:
            chips.addWidget(_chip(channel))
        views = _fmt_views(info.get("view_count"))
        if views:
            chips.addWidget(_chip(views))
        chips.addStretch(1)
        body.addLayout(chips)

        self.preview_meta = QLabel("")
        self.preview_meta.setObjectName("FormHelp")
        self.preview_meta.setStyleSheet(
            f"{ui_theme.mono_css()} font-size: {ui_theme.px(11)}px;"
            f" color: {ui_theme.color('gray_light')};"
        )
        body.addWidget(self.preview_meta)
        self._update_preview_meta()

        self.preview_layout.addLayout(body, 1)
        self.preview.setVisible(True)

    def _update_preview_meta(self) -> None:
        """State the target format and its rough size from the selected pill."""
        meta = getattr(self, "preview_meta", None)
        if meta is None:
            return
        seconds = (self._preview_info or {}).get("duration") or 0
        if self.audio_pill.isChecked():
            target = "MP3"
            kbps = AUDIO_KBPS
        else:
            target = f"{self._res}p MP4"
            kbps = RESOLUTION_KBPS.get(self._res, 2500) + AUDIO_TRACK_KBPS
        size = _fmt_size(seconds * kbps * 1000 / 8) if seconds else ""
        meta.setText(f"Will download: {target}" + (f" \u00b7 ~{size}" if size else ""))

    def _load_preview_thumb(self, info: dict, tile: QLabel) -> None:
        """Fetch the preview thumbnail off-thread and paint it into ``tile``."""
        thumb_url = info.get("thumbnail")
        if not thumb_url:
            return
        preview_url = self._preview_url
        worker = PreviewThumbWorker(thumb_url, self)

        def apply(data) -> None:
            # Ignore a late result for a URL the user has already replaced.
            if preview_url is None or preview_url != self._preview_url or not data:
                return
            pixmap = QPixmap()
            if not pixmap.loadFromData(data):
                return
            scaled = pixmap.scaled(
                tile.width(), tile.height(),
                Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation,
            )
            tile.setPixmap(scaled)

        worker.fetched.connect(apply)
        worker.finished.connect(lambda w=worker: self._release_preview_worker(w))
        self._preview_workers.add(worker)
        worker.start()

    def _release_preview_worker(self, worker: PreviewThumbWorker) -> None:
        self._preview_workers.discard(worker)
        worker.deleteLater()

    # -- queue actions -----------------------------------------------------
    def add_to_queue(self) -> None:
        url = self._last_sanitized or self.url_input.text().strip()
        if not url:
            self._notify("Please enter a video URL.", "error")
            self.url_input.setFocus()
            return
        path = self.settings.get("download_path") or ""
        if not path:
            self._notify("Please select a download folder.", "error")
            return
        if self.audio_pill.isChecked() and not self._ffmpeg:
            self._notify(
                "Audio-only downloads need ffmpeg on your PATH. "
                "Install ffmpeg, or clear the Audio Only pill to download video.",
                "error",
            )
            return

        duplicate_kind, duplicate = self.manager.find_duplicate(url)
        if duplicate_kind == "queue":
            if not self._ask(
                "Duplicate URL",
                f"This URL is already in the queue (status: {duplicate.get('status')}).",
                "Add anyway",
            ):
                self.url_input.clear()
                return
        elif duplicate_kind == "history":
            if not self._ask(
                "Previously downloaded",
                "This URL was already downloaded.",
                "Download again",
            ):
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
            self._notify("No pending downloads in the queue.")
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

    def _move_item(self, item: DownloadItem, delta: int) -> None:
        if self.manager.move(item, delta):
            self.refresh()

    def _index_of(self, item: DownloadItem) -> int | None:
        for index, candidate in enumerate(self.manager.snapshot()):
            if candidate is item:
                return index
        return None

    def _set_status(self, item: DownloadItem, status: DownloadStatus) -> None:
        if status is DownloadStatus.PENDING:
            item.message = ""
        if status is DownloadStatus.PENDING and item.status is DownloadStatus.PAUSED:
            index = self._index_of(item)
            if index is not None:
                self.manager.resume(index)

    def play_item(self, item: DownloadItem) -> None:
        target = os.path.join(item.path, item.filename) if item.filename else ""
        if not target or not os.path.exists(target):
            self._notify("That file is no longer in the download folder.", "error")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(target))

    def open_folder(self, item: DownloadItem) -> None:
        import subprocess
        import sys

        path = item.path
        if not path or not os.path.exists(path):
            self._notify("Download folder does not exist yet.", "error")
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
            item.message = ""
            logger.info("Download paused: %s", item.title)
        else:
            item.message = message or "Download failed"
            self.manager.mark_failed(item)
            logger.error("Download failed: %s - %s", item.title, item.message)
        self.refresh()

    def _on_run_finished(self) -> None:
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.refresh()

    def _on_item_info(self, item: DownloadItem, info: dict) -> None:
        """Cache the video thumbnail once a download reports its info."""
        filename = thumb_cache.final_filename(info)
        if filename and item.filename != filename:
            item.filename = filename
            self.manager.save()
        thumb_url = info.get("thumbnail")
        if not (filename and thumb_url):
            return
        worker = ThumbWorker(item.path, filename, thumb_url, self)
        worker.finished.connect(lambda w=worker: self._thumb_workers.discard(w))
        self._thumb_workers.add(worker)
        worker.start()

    # -- rendering ---------------------------------------------------------
    def refresh(self) -> None:
        snapshot = self.manager.snapshot()
        items = [
            item for _, item in sorted(
                enumerate(snapshot),
                key=lambda pair: (STATUS_RANK.get(pair[1].status, 2), pair[0]),
            )
        ]
        alive = {id(item) for item in items}

        # Keyed update: rows that survive keep their identity, focus and row
        # widgets; only rows whose items disappeared are destroyed.
        for key in list(self._rows):
            if key not in alive:
                row = self._rows.pop(key)
                row.setParent(None)
                row.deleteLater()

        if self._selected is not None and id(self._selected) not in alive:
            self._selected = None

        active = [i for i in items if i.status is DownloadStatus.DOWNLOADING]
        rest = [i for i in items if i.status is not DownloadStatus.DOWNLOADING]

        for layout, group in ((self.active_list, active), (self.queue_list, rest)):
            for item in group:
                row = self._rows.get(id(item))
                if row is None:
                    row = self._make_row(item)
                else:
                    row.update_item(item)
                layout.removeWidget(row)   # re-add to apply the new order
                layout.addWidget(row)

        movable = [item for item in rest if item.status in (
            DownloadStatus.PENDING, DownloadStatus.PAUSED)]
        for position, item in enumerate(movable):
            row = self._rows.get(id(item))
            if row is not None:
                row.set_move_enabled(position > 0, position < len(movable) - 1)

        # An empty section is noise: hide its heading along with it.
        self.active_section.setVisible(bool(active))
        self.queue_section.setVisible(bool(rest))

        if items:
            if self._empty_box is not None:
                self.queue_list.removeWidget(self._empty_box)
                self._empty_box.setVisible(False)
        else:
            if self._empty_box is None:
                self._empty_box = self._empty_state()
            self.queue_list.removeWidget(self._empty_box)
            self.queue_list.addWidget(self._empty_box)
            self._empty_box.setVisible(True)

        self._update_chips()
        running = self.runner.is_running()
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)

    def _empty_state(self) -> QWidget:
        box = QFrame()
        box.setObjectName("Card")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(px(16), px(16), px(16), px(16))
        layout.setSpacing(px(8))
        icon_label = QLabel()
        icon_label.setPixmap(icons.pixmap("download", 24, "muted"))
        layout.addWidget(icon_label)
        text = QLabel("No downloads yet \u2014 paste a link above to get started.")
        text.setWordWrap(True)
        text.setStyleSheet(f"color: {ui_theme.color('muted')};")
        layout.addWidget(text)
        add_link = QPushButton("Add a link")
        add_link.clicked.connect(self._focus_url)
        layout.addWidget(add_link, 0, Qt.AlignLeft)
        return box

    def _focus_url(self) -> None:
        self.url_input.setFocus()
        self.url_input.selectAll()

    def _make_row(self, item: DownloadItem) -> QueueRow:
        row = QueueRow(item)
        if ui_theme.motion_enabled():
            fade = QGraphicsOpacityEffect(row)
            fade.setOpacity(0.0)
            row.setGraphicsEffect(fade)
            animation = QPropertyAnimation(fade, b"opacity", row)
            animation.setDuration(120)
            animation.setStartValue(0.0)
            animation.setEndValue(1.0)
            animation.finished.connect(lambda r=row: r.setGraphicsEffect(None))
            animation.start()
        row.pressed.connect(self._set_selected)
        row.move_up.connect(lambda item: self._move_item(item, -1))
        row.move_down.connect(lambda item: self._move_item(item, 1))
        row.open_folder.connect(self.open_folder)
        row.play.connect(self.play_item)
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
