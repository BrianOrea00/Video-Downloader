# ui/main_window.py
"""Application shell: sidebar + top bar + stacked pages."""
from __future__ import annotations

from PySide6.QtCore import Qt
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

from persistence import save_settings
import persistence
from queue_manager import QueueManager
from ui.pages.music_page import MusicPage
from ui.pages.queue_page import QueuePage
from ui.pages.settings_page import SettingsPage
from ui.pages.videos_page import VideosPage
from ui.sidebar import Sidebar
from ui.theme import METRICS, apply_theme, px

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
        self.theme = settings.get("theme", "dark")

        self.setWindowTitle("Video Downloader")
        # Scale the window with the UI, but never demand more than the screen has.
        min_w = px(METRICS["min_window_w"])
        min_h = px(METRICS["min_window_h"])
        screen = QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            min_w = min(min_w, max(320, int(available.width() * 0.9)))
            min_h = min(min_h, max(240, int(available.height() * 0.9)))
        self.setMinimumSize(min_w, min_h)
        self.resize(max(min_w, px(1200)), max(min_h, px(700)))

        central = QWidget()
        self.setCentralWidget(central)
        row = QHBoxLayout(central)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.navigate.connect(self.show_page)
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
        for page in self.pages.values():
            self.stack.addWidget(page)
        column.addWidget(self.stack, 1)
        row.addWidget(content, 1)

        self.show_page("queue")

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

    def _refresh_current(self) -> None:
        page = self.pages.get(getattr(self, "current_key", "queue"))
        refresh = getattr(page, "refresh", None)
        if callable(refresh):
            refresh()

    # -- theme -------------------------------------------------------------
    def toggle_theme(self) -> None:
        self.theme = "light" if self.theme == "dark" else "dark"
        self.settings["theme"] = self.theme
        save_settings(self.settings)
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, self.theme)
        self._refresh_current()
        self._sync_theme_button()

    def _sync_theme_button(self) -> None:
        # Label states the action, matching the prototype's "☾ Light".
        if self.theme == "dark":
            text = "\u263e Light"
            hint = "Switch to light theme"
        else:
            text = "\u2600 Dark"
            hint = "Switch to dark theme"
        self.theme_btn.setText(text)
        self.theme_btn.setAccessibleName(hint)

    # -- badge -------------------------------------------------------------
    def set_badge(self, count: int) -> None:
        self.badge.setText(f"{count} item" if count == 1 else f"{count} items")
