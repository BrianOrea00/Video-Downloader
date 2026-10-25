# ui/pages/settings_page.py
"""Settings form: download mode, defaults, general, cookies."""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config import RESOLUTIONS
from downloader import Downloader
from persistence import save_settings
from ui.theme import (
    DEFAULT_FAMILY,
    DEFAULT_MODE,
    METRICS,
    MODE_LABELS,
    MODES,
    THEME_LABELS,
    family_names,
    px,
)
from utils import ffmpeg_available

logger = logging.getLogger(__name__)

TITLE = "Settings"
BROWSERS = ["chrome", "firefox", "edge", "brave", "opera", "safari"]
PROBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


class CookieTestWorker(QThread):
    """Runs the cookie test off the GUI thread."""

    done = Signal(bool, str)  # (ok, message)

    def __init__(self, cookie_settings: dict, parent=None) -> None:
        super().__init__(parent)
        self._cookie = cookie_settings

    def run(self) -> None:
        try:
            info = Downloader().get_info(PROBE_URL, self._cookie)
            if not info:
                self.done.emit(False, "Cookie test failed: no data returned.")
            else:
                self.done.emit(True, f"Cookie test passed: {info.get('title', 'unknown')[:40]}")
        except Exception as exc:  # noqa: BLE001
            self.done.emit(False, f"Cookie test failed: {exc}")


def _desc(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("FormHelp")
    label.setWordWrap(True)
    return label


class SettingsPage(QWidget):
    settings_changed = Signal()
    theme_changed = Signal(str, str)  # (family, mode)

    def __init__(self, settings: dict, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._test_worker: CookieTestWorker | None = None
        self._build()

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
        col.setContentsMargins(px(24), px(20), px(24), px(20))
        col.setSpacing(px(16))

        col.addWidget(self._download_card())
        col.addWidget(self._general_card())
        col.addWidget(self._cookies_card())
        col.addWidget(self._appearance_card())

        save_row = QHBoxLayout()
        self.status = QLabel("")
        self.status.setObjectName("StatusLine")
        save_row.addWidget(self.status, 1)
        save = QPushButton("Save")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self.save)
        save_row.addWidget(save)
        col.addLayout(save_row)
        col.addStretch(1)

    def _card(self, heading: str) -> tuple[QFrame, QFormLayout]:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(px(16), px(16), px(16), px(16))
        layout.setSpacing(px(10))
        title = QLabel(heading)
        title.setObjectName("FieldLabel")
        layout.addWidget(title)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form.setHorizontalSpacing(px(24))
        form.setVerticalSpacing(px(12))
        layout.addLayout(form)
        return card, form

    def _download_card(self) -> QFrame:
        card, form = self._card("DOWNLOAD")

        self.mode = QComboBox()
        self.mode.addItem("Parallel", "parallel")
        self.mode.addItem("Sequential", "sequential")
        self._select(self.mode, self.settings.get("download_mode", "parallel"))
        self.mode.currentIndexChanged.connect(self._on_mode)
        form.addRow(self._label("Download mode", "Parallel downloads several files at once."), self.mode)

        self.limit = QComboBox()
        for value in (1, 2, 3, 4, 5):
            self.limit.addItem(str(value), value)
        self._select(self.limit, int(self.settings.get("parallel_limit", 2)))
        self.limit.currentIndexChanged.connect(
            lambda: self._set("parallel_limit", self.limit.currentData()))
        form.addRow(self._label("Max parallel downloads", "Used in parallel mode."), self.limit)

        self.resolution = QComboBox()
        for res in RESOLUTIONS:
            self.resolution.addItem(f"{res}p", res)
        self._select(self.resolution, self.settings.get("default_resolution", "720"))
        self.resolution.currentIndexChanged.connect(
            lambda: self._set("default_resolution", self.resolution.currentData()))
        form.addRow(self._label("Default resolution", "Applied to new queue items."), self.resolution)

        self.audio_only = QCheckBox("Enabled")
        self.audio_only.setAccessibleName("Download audio (MP3) by default")
        ffmpeg_ok = ffmpeg_available()
        audio_help = "Default format for new items."
        if not ffmpeg_ok:
            audio_help = "Needs ffmpeg on PATH; it was not found."
            self.audio_only.setEnabled(False)
            self.audio_only.setToolTip(audio_help)
            self.audio_only.setAccessibleDescription(audio_help)
        self.audio_only.setChecked(
            ffmpeg_ok and bool(self.settings.get("default_audio_only", False))
        )
        self.audio_only.toggled.connect(lambda v: self._set("default_audio_only", v))
        form.addRow(self._label("Audio only", audio_help), self.audio_only)
        return card

    def _general_card(self) -> QFrame:
        card, form = self._card("GENERAL")

        self.auto_clipboard = QCheckBox("Enabled")
        self.auto_clipboard.setAccessibleName("Poll the clipboard for YouTube URLs")
        self.auto_clipboard.setChecked(bool(self.settings.get("auto_clipboard", True)))
        self.auto_clipboard.toggled.connect(lambda v: self._set("auto_clipboard", v))
        form.addRow(self._label("Auto clipboard detection", "Paste automatically when a link is copied."),
                    self.auto_clipboard)

        self.interval = QSpinBox()
        self.interval.setRange(500, 10000)
        self.interval.setSingleStep(500)
        self.interval.setSuffix(" ms")
        self.interval.setValue(int(self.settings.get("clipboard_interval", 3000)))
        self.interval.valueChanged.connect(lambda v: self._set("clipboard_interval", v))
        form.addRow(self._label("Clipboard interval", "How often the clipboard is checked."), self.interval)
        return card

    def _cookies_card(self) -> QFrame:
        card, form = self._card("COOKIES")

        self.cookie_method = QComboBox()
        for value, label in (("none", "None"), ("browser", "Browser"), ("file", "cookies.txt")):
            self.cookie_method.addItem(label, value)
        self._select(self.cookie_method, self.settings.get("cookie_method", "none"))
        self.cookie_method.currentIndexChanged.connect(self._on_cookie_method)
        form.addRow(self._label("Cookie source", "For age-restricted or private content."), self.cookie_method)

        self.cookie_browser = QComboBox()
        for browser in BROWSERS:
            self.cookie_browser.addItem(browser.capitalize(), browser)
        self._select(self.cookie_browser, self.settings.get("cookie_browser", "chrome"))
        self.cookie_browser.currentIndexChanged.connect(
            lambda: self._set("cookie_browser", self.cookie_browser.currentData()))
        form.addRow(self._label("Browser", "Used when the source is Browser."), self.cookie_browser)

        file_row = QWidget()
        file_layout = QHBoxLayout(file_row)
        file_layout.setContentsMargins(0, 0, 0, 0)
        self.cookie_file = QLineEdit(self.settings.get("cookie_file_path", ""))
        self.cookie_file.textChanged.connect(lambda t: self._set("cookie_file_path", t))
        file_layout.addWidget(self.cookie_file, 1)
        browse = QPushButton("Browse")
        browse.clicked.connect(self._browse_cookie_file)
        file_layout.addWidget(browse)
        form.addRow(self._label("cookies.txt", "Used when the source is cookies.txt."), file_row)

        test_row = QWidget()
        test_layout = QHBoxLayout(test_row)
        test_layout.setContentsMargins(0, 0, 0, 0)
        self.cookie_status = QLabel("")
        self.cookie_status.setObjectName("StatusLine")
        test_layout.addWidget(self.cookie_status, 1)
        test = QPushButton("Test cookies")
        test.clicked.connect(self._test_cookies)
        test_layout.addWidget(test)
        form.addRow(self._label("Verify", "Fetch a sample video with the saved cookies."), test_row)

        self._sync_cookie_enabled()
        return card

    def _appearance_card(self) -> QFrame:
        card, form = self._card("APPEARANCE")

        self.theme_family = QComboBox()
        for key in family_names():
            self.theme_family.addItem(THEME_LABELS.get(key, key), key)
        self._select(self.theme_family, self.settings.get("theme_family", DEFAULT_FAMILY))
        self.theme_family.currentIndexChanged.connect(self._on_theme_changed)
        form.addRow(self._label("Theme", "Colour family for the whole app."), self.theme_family)

        self.theme_mode = QComboBox()
        for mode in MODES:
            self.theme_mode.addItem(MODE_LABELS.get(mode, mode.title()), mode)
        self._select(self.theme_mode, self.settings.get("theme", DEFAULT_MODE))
        self.theme_mode.currentIndexChanged.connect(self._on_theme_changed)
        form.addRow(self._label("Mode", "Dark or light variant of the theme."), self.theme_mode)
        return card

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _label(name: str, description: str) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(px(2))
        title = QLabel(name)
        layout.addWidget(title)
        layout.addWidget(_desc(description))
        # QFormLayout sizes a row from the field widget by default. A plain QWidget
        # does not advertise heightForWidth, so the wrapped description is ignored
        # and its lines spill into the next row. Opt in explicitly, and give the
        # label column a stable width so the text wraps instead of overflowing.
        policy = box.sizePolicy()
        policy.setHeightForWidth(True)
        box.setSizePolicy(policy)
        box.setMinimumWidth(px(METRICS["label_column"]))
        return box

    @staticmethod
    def _select(combo: QComboBox, value) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _set(self, key: str, value) -> None:
        self.settings[key] = value

    def _on_mode(self) -> None:
        self._set("download_mode", self.mode.currentData())

    def sync_theme_controls(self, family: str, mode: str) -> None:
        """Reflect a theme applied elsewhere (top bar toggle) without re-emitting."""
        for combo, value in ((self.theme_family, family), (self.theme_mode, mode)):
            combo.blockSignals(True)
            self._select(combo, value)
            combo.blockSignals(False)

    def _on_theme_changed(self) -> None:
        """Apply a theme choice immediately, then let the window persist it."""
        family = self.theme_family.currentData()
        mode = self.theme_mode.currentData()
        self.settings["theme_family"] = family
        self.settings["theme"] = mode
        self.theme_changed.emit(family, mode)

    def _on_cookie_method(self) -> None:
        self._set("cookie_method", self.cookie_method.currentData())
        self._sync_cookie_enabled()

    def _sync_cookie_enabled(self) -> None:
        method = self.cookie_method.currentData()
        self.cookie_browser.setEnabled(method == "browser")
        self.cookie_file.setEnabled(method == "file")

    def _browse_cookie_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select cookies.txt", "", "Cookies (*.txt);;All files (*)")
        if path:
            self.cookie_file.setText(path)

    # -- actions -----------------------------------------------------------
    def save(self) -> None:
        save_settings(self.settings)
        self.status.setText("Saved.")
        self.settings_changed.emit()

    def _test_cookies(self) -> None:
        if self._test_worker is not None and self._test_worker.isRunning():
            return
        self.cookie_status.setText("Testing\u2026")
        cookie_settings = {
            "cookie_method": self.settings.get("cookie_method", "none"),
            "cookie_browser": self.settings.get("cookie_browser", "chrome"),
            "cookie_file_path": self.settings.get("cookie_file_path", ""),
        }
        self._test_worker = CookieTestWorker(cookie_settings, self)
        self._test_worker.done.connect(self._on_cookie_result)
        self._test_worker.start()

    def _on_cookie_result(self, ok: bool, message: str) -> None:
        self.cookie_status.setText(message)
        if not ok:
            QMessageBox.warning(self, "Cookie test", message)
