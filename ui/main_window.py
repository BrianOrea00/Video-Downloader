# ui/main_window.py
"""Application shell: sidebar + top bar + stacked pages."""
from __future__ import annotations

import shutil

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import persistence
from persistence import save_settings
from queue_manager import QueueManager
from ui import icons
from ui.pages.music_page import MusicPage
from ui.pages.queue_page import QueuePage
from ui.pages.settings_page import SettingsPage
from ui.pages.videos_page import VideosPage
from ui.sidebar import Sidebar
from ui.theme import (
    DEFAULT_FAMILY,
    DEFAULT_MODE,
    METRICS,
    MODES,
    THEMES,
    apply_theme,
    flip_mode,
    px,
)

TITLES = {
    "queue": "Download Queue",
    "videos": "Video Library",
    "music": "Music Library",
    "settings": "Settings",
}


class MainWindow(QMainWindow):
    def __init__(self, settings: dict) -> None:
        super().__init__()
        self.settings = settings
        self.family = settings.get("theme_family", DEFAULT_FAMILY)
        self.mode = settings.get("theme", DEFAULT_MODE)

        self.setWindowTitle("Video Downloader")
        # Minimums stay in device pixels: scaling them as well made the window
        # demand 1350x900 at the shipped 1.5 scale and clip on a 1366 laptop.
        min_w = METRICS["min_window_w"]
        min_h = METRICS["min_window_h"]
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen is not None else None
        if available is not None:
            min_w = min(min_w, max(320, int(available.width() * 0.9)))
            min_h = min(min_h, max(240, int(available.height() * 0.9)))
        self.setMinimumSize(min_w, min_h)
        start_w, start_h = px(1200), px(700)
        if available is not None:
            start_w = min(start_w, available.width())
            start_h = min(start_h, available.height())
        self.resize(max(min_w, start_w), max(min_h, start_h))

        central = QWidget()
        self.setCentralWidget(central)
        row = QHBoxLayout(central)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.navigate.connect(self.show_page)
        self.sidebar.collapsed_changed.connect(self._on_sidebar_collapsed)
        self.sidebar.set_collapsed(bool(self.settings.get("sidebar_collapsed", False)),
                                   notify=False)
        row.addWidget(self.sidebar)

        content = QWidget()
        content.setObjectName("Content")
        column = QVBoxLayout(content)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(self._build_topbar())

        self.stack = QStackedWidget()
        self.manager = QueueManager(store=persistence, history_loader=persistence.load_history)
        self.queue_page = QueuePage(self.manager, self.settings)
        self.queue_page.count_changed.connect(self.set_badge)
        self.videos_page = VideosPage(self.settings)
        self.music_page = MusicPage(self.settings)
        self.settings_page = SettingsPage(self.settings)
        self.pages: dict[str, QWidget] = {
            "queue": self.queue_page,
            "videos": self.videos_page,
            "music": self.music_page,
            "settings": self.settings_page,
        }
        self.queue_page.download_completed.connect(self._refresh_current)
        self.settings_page.settings_changed.connect(self.queue_page.apply_defaults)
        self.settings_page.theme_changed.connect(self.set_theme)
        for page in self.pages.values():
            self.stack.addWidget(page)
        column.addWidget(self.stack, 1)
        row.addWidget(content, 1)

        # Application-wide keys; page-local ones live on the pages themselves.
        QShortcut(QKeySequence("Ctrl+T"), self, activated=self.toggle_theme)
        QShortcut(QKeySequence.Find, self, activated=self._focus_search)

        self._restore_window_state()
        last_page = self.settings.get("last_page", "queue")
        self.show_page(last_page if last_page in self.pages else "queue")

    def _restore_window_state(self) -> None:
        """Bring back size, maximised state and page, then keep them on screen."""
        geometry = self.settings.get("window_geometry")
        if geometry:
            self.restoreGeometry(QByteArray.fromBase64(geometry.encode("ascii")))
            self._clamp_to_screen()
        state = self.settings.get("window_state")
        if state:
            self.restoreState(QByteArray.fromBase64(state.encode("ascii")))

    def _clamp_to_screen(self) -> None:
        screen = QGuiApplication.screenAt(self.frameGeometry().center())
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        frame = self.frameGeometry()
        if available.contains(frame):
            return
        width = min(frame.width(), available.width())
        height = min(frame.height(), available.height())
        x = min(max(frame.x(), available.x()), available.right() - width + 1)
        y = min(max(frame.y(), available.y()), available.bottom() - height + 1)
        self.setGeometry(x, y, width, height)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        self.settings["window_geometry"] = bytes(
            self.saveGeometry().toBase64()).decode("ascii")
        self.settings["window_state"] = bytes(
            self.saveState().toBase64()).decode("ascii")
        save_settings(self.settings)
        super().closeEvent(event)

    # -- top bar -----------------------------------------------------------
    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(px(METRICS["topbar_height"]))
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(px(20), 0, px(20), 0)
        layout.setSpacing(px(12))

        self.title_label = QLabel(TITLES["queue"])
        self.title_label.setObjectName("PageTitle")

        self.badge = QLabel("0 items")
        self.badge.setObjectName("Badge")
        self.badge.setAccessibleName("Queued items")
        self.badge.setVisible(False)   # only shown when something is queued

        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("ThemeButton")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self.toggle_theme)
        self._sync_theme_button()

        layout.addWidget(self.title_label)
        layout.addStretch(1)
        layout.addWidget(self.badge)
        layout.addWidget(self.theme_btn)
        return bar

    # -- navigation --------------------------------------------------------
    def show_page(self, key: str) -> None:
        page = self.pages.get(key)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        self.title_label.setText(TITLES.get(key) or getattr(page, "title", ""))
        self.sidebar.set_active(key)
        self.current_key = key
        self.settings["last_page"] = key
        self._update_storage()

    def _update_storage(self) -> None:
        """Free space for the download folder, refreshed on page change.

        Not polled: the number only moves after a download or a folder change.
        """
        path = self.settings.get("download_path") or ""
        if not path:
            self.sidebar.set_storage("No folder", 0.0)
            return
        try:
            usage = shutil.disk_usage(path)
        except OSError:
            self.sidebar.set_storage("Unavailable", 0.0, path)
            return
        free_gb = usage.free / (1024 ** 3)
        self.sidebar.set_storage(f"{free_gb:.1f} GB free", usage.used / usage.total, path)

    def _refresh_current(self) -> None:
        self._update_storage()
        page = self.pages.get(getattr(self, "current_key", "queue"))
        refresh = getattr(page, "refresh", None)
        if callable(refresh):
            refresh()

    # -- sidebar -----------------------------------------------------------
    def _on_sidebar_collapsed(self, collapsed: bool) -> None:
        self.settings["sidebar_collapsed"] = collapsed
        save_settings(self.settings)

    # -- theme -------------------------------------------------------------
    def set_theme(self, family: str, mode: str) -> None:
        """Apply and persist a theme choice (top bar toggle or settings page)."""
        self.family = family if family in THEMES else DEFAULT_FAMILY
        self.mode = mode if mode in MODES else DEFAULT_MODE
        self.settings["theme_family"] = self.family
        self.settings["theme"] = self.mode
        save_settings(self.settings)
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, self.family, self.mode)
        self.settings_page.sync_theme_controls(self.family, self.mode)
        self._refresh_current()
        self._sync_theme_button()
        self.sidebar.refresh_icons()

    def toggle_theme(self) -> None:
        """Quick toggle: keep the family, flip dark/light."""
        self.set_theme(self.family, flip_mode(self.mode))

    def _sync_theme_button(self) -> None:
        """The label states the action; the icon shows the current mode."""
        asset = "moon" if self.mode == "dark" else "sun"
        text = "Light" if self.mode == "dark" else "Dark"
        hint = "Switch to light mode" if self.mode == "dark" else "Switch to dark mode"
        self.theme_btn.setIcon(icons.icon(asset, 16, "gray_light"))
        self.theme_btn.setIconSize(QSize(px(16), px(16)))
        self.theme_btn.setText(f"  {text}")
        self.theme_btn.setAccessibleName(hint)

    # -- badge -------------------------------------------------------------
    def set_badge(self, count: int) -> None:
        self.badge.setText(f"{count} item" if count == 1 else f"{count} items")
        self.badge.setVisible(count > 0)

    def _focus_search(self) -> None:
        """Ctrl+F: the library search on media pages, the URL field elsewhere."""
        search = getattr(self.stack.currentWidget(), "search", None)
        if search is not None:
            search.setFocus()
            search.selectAll()
            return
        self.queue_page.url_input.setFocus()
        self.queue_page.url_input.selectAll()
