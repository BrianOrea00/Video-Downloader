# ui/sidebar.py
"""Sidebar navigation: logo, nav buttons, storage meter."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# (page key, glyph, label)
NAV_ITEMS = [
    ("queue", "\u2b07", "Queue"),
    ("videos", "\u25b6", "Videos"),
    ("music", "\u266a", "Music"),
]
SYSTEM_ITEMS = [
    ("settings", "\u2699", "Settings"),
]


def _section_label(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setObjectName("SectionLabel")
    return label


class Sidebar(QWidget):
    """Left navigation rail. Emits :attr:`navigate` with a page key."""

    navigate = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(240)
        self._buttons: dict[str, QPushButton] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 16, 12, 12)
        root.setSpacing(2)

        root.addWidget(self._build_logo())
        root.addWidget(_section_label("Library"))
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for key, glyph, label in NAV_ITEMS:
            root.addWidget(self._add_nav(key, glyph, label))

        root.addWidget(_section_label("System"))
        for key, glyph, label in SYSTEM_ITEMS:
            root.addWidget(self._add_nav(key, glyph, label))

        root.addStretch(1)
        root.addWidget(self._build_storage())

    # -- construction helpers ---------------------------------------------
    def _build_logo(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(4, 0, 4, 12)
        layout.setSpacing(8)

        mark = QLabel("\u25bc")
        mark.setObjectName("LogoMark")
        mark.setFixedSize(22, 22)
        mark.setAlignment(Qt.AlignCenter)

        text = QVBoxLayout()
        text.setSpacing(0)
        title = QLabel("Downloader")
        title.setObjectName("LogoTitle")
        subtitle = QLabel("yt-dlp")
        subtitle.setObjectName("LogoSub")
        text.addWidget(title)
        text.addWidget(subtitle)

        layout.addWidget(mark)
        layout.addLayout(text)
        layout.addStretch(1)
        return row

    def _add_nav(self, key: str, glyph: str, label: str) -> QPushButton:
        button = QPushButton(f"{glyph}   {label}")
        button.setObjectName("NavButton")
        button.setCheckable(True)
        button.setCursor(Qt.PointingHandCursor)
        button.setAccessibleName(label)
        button.clicked.connect(lambda _=False, k=key: self.navigate.emit(k))
        self._group.addButton(button)
        self._buttons[key] = button
        return button

    def _build_storage(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(4, 12, 4, 0)
        layout.setSpacing(6)

        head = QWidget()
        head_layout = QHBoxLayout(head)
        head_layout.setContentsMargins(0, 0, 0, 0)
        caption = QLabel("Storage")
        caption.setObjectName("StorageHead")
        self.storage_label = QLabel("0 GB")
        self.storage_label.setObjectName("StorageHead")
        head_layout.addWidget(caption)
        head_layout.addStretch(1)
        head_layout.addWidget(self.storage_label)

        self._track = QFrame()
        self._track.setObjectName("Track")
        self._track.setFixedHeight(3)
        track_layout = QHBoxLayout(self._track)
        track_layout.setContentsMargins(0, 0, 0, 0)
        self._fill = QFrame()
        self._fill.setObjectName("TrackFill")
        self._fill.setFixedHeight(3)
        self._fill.setFixedWidth(0)
        track_layout.addWidget(self._fill)
        track_layout.addStretch(1)

        layout.addWidget(head)
        layout.addWidget(self._track)
        return box

    # -- public API --------------------------------------------------------
    def set_active(self, key: str) -> None:
        button = self._buttons.get(key)
        if button is not None and not button.isChecked():
            button.setChecked(True)

    def set_storage(self, used_label: str, fraction: float) -> None:
        """Update the storage readout and bar (``fraction`` in 0.0..1.0)."""
        self.storage_label.setText(used_label)
        width = int(self._track.width() * max(0.0, min(1.0, fraction)))
        self._fill.setFixedWidth(max(2, width))
