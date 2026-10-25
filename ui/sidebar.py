# ui/sidebar.py
"""Sidebar navigation: logo, nav buttons, storage meter."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui import icons
from ui.theme import METRICS, px, repolish

# (page key, icon asset, label)
NAV_ITEMS = [
    ("queue", "download", "Queue"),
    ("videos", "video", "Videos"),
    ("music", "music", "Music"),
]
SYSTEM_ITEMS = [
    ("settings", "settings", "Settings"),
]

def _section_label(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setObjectName("SectionLabel")
    return label



class Sidebar(QWidget):
    """Left navigation rail. Emits :attr:`navigate` with a page key."""

    navigate = Signal(str)
    collapsed_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None, collapsed: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(px(METRICS["sidebar_width"]))
        self._buttons: dict[str, QPushButton] = {}
        self._items: dict[str, tuple[str, str]] = {}  # key -> (glyph, label)
        self._sections: list[QLabel] = []
        self._collapsed = False

        root = QVBoxLayout(self)
        root.setContentsMargins(px(12), px(16), px(12), px(12))
        root.setSpacing(px(2))

        root.addWidget(self._build_logo())
        root.addWidget(self._section("Library"))
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for key, glyph, label in NAV_ITEMS:
            root.addWidget(self._add_nav(key, glyph, label))

        root.addWidget(self._section("System"))
        for key, glyph, label in SYSTEM_ITEMS:
            root.addWidget(self._add_nav(key, glyph, label))

        root.addStretch(1)
        root.addWidget(self._build_storage())

    # -- construction helpers ---------------------------------------------
    def _build_logo(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(px(4), 0, px(4), px(12))
        layout.setSpacing(px(8))

        self.burger = QPushButton()
        self.burger.setIcon(icons.icon("list-details", 18, "gray_light"))
        self.burger.setIconSize(QSize(px(18), px(18)))
        self.burger.setObjectName("BurgerButton")
        self.burger.setCheckable(True)
        self.burger.setCursor(Qt.PointingHandCursor)
        self.burger.setToolTip("Collapse sidebar")
        self.burger.setAccessibleName("Collapse sidebar")
        self.burger.clicked.connect(self.toggle_collapsed)

        self._mark = QLabel()
        self._mark.setObjectName("LogoMark")
        self._mark.setFixedSize(px(METRICS["logo_mark"]), px(METRICS["logo_mark"]))
        self._mark.setAlignment(Qt.AlignCenter)
        self._mark.setPixmap(icons.pixmap("download", 14, "bg_dark"))

        self._logo_text = QWidget()
        text = QVBoxLayout(self._logo_text)
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(px(0))
        title = QLabel("Downloader")
        title.setObjectName("LogoTitle")
        subtitle = QLabel("yt-dlp")
        subtitle.setObjectName("LogoSub")
        text.addWidget(title)
        text.addWidget(subtitle)

        layout.addWidget(self.burger)
        layout.addWidget(self._mark)
        layout.addWidget(self._logo_text)
        layout.addStretch(1)
        return row

    def _section(self, text: str) -> QLabel:
        """A heading that disappears when the rail is collapsed."""
        label = _section_label(text)
        self._sections.append(label)
        return label

    def _add_nav(self, key: str, asset: str, label: str) -> QPushButton:
        """``asset`` is an icon name resolved by :mod:`ui.icons`."""
        button = QPushButton()
        button.setObjectName("NavButton")
        button.setCheckable(True)
        button.setCursor(Qt.PointingHandCursor)
        button.setAccessibleName(label)
        button.clicked.connect(lambda _=False, k=key: self.navigate.emit(k))
        button.toggled.connect(lambda _=False, k=key: self._paint_nav(k))
        self._group.addButton(button)
        self._buttons[key] = button
        self._items[key] = (asset, label)
        self._paint_nav(key)
        return button

    def _build_storage(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(px(4), px(12), px(4), 0)
        layout.setSpacing(px(6))

        self._storage_head = QWidget()
        head = self._storage_head
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
        self._track.setFixedHeight(px(METRICS["shelf"]))
        track_layout = QHBoxLayout(self._track)
        track_layout.setContentsMargins(0, 0, 0, 0)
        self._fill = QFrame()
        self._fill.setObjectName("TrackFill")
        self._fill.setFixedHeight(px(METRICS["shelf"]))
        self._fill.setFixedWidth(0)
        track_layout.addWidget(self._fill)
        track_layout.addStretch(1)

        layout.addWidget(head)
        layout.addWidget(self._track)
        return box

    # -- collapse ----------------------------------------------------------
    @property
    def collapsed(self) -> bool:
        return self._collapsed

    def toggle_collapsed(self) -> None:
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool, notify: bool = True) -> None:
        """Show glyph-only nav when ``collapsed``, icon + text otherwise."""
        collapsed = bool(collapsed)
        self._collapsed = collapsed
        self.setFixedWidth(px(METRICS[
            "sidebar_collapsed_width" if collapsed else "sidebar_width"]))

        self._mark.setVisible(not collapsed)
        self._logo_text.setVisible(not collapsed)
        self._storage_head.setVisible(not collapsed)
        for label in self._sections:
            label.setVisible(not collapsed)

        self.burger.setChecked(collapsed)
        hint = "Expand sidebar" if collapsed else "Collapse sidebar"
        self.burger.setToolTip(hint)
        self.burger.setAccessibleName(hint)

        for key in self._buttons:
            self._paint_nav(key)

        if notify:
            self.collapsed_changed.emit(collapsed)

    def _paint_nav(self, key: str) -> None:
        """Render one nav button for the current rail state."""
        asset, label = self._items[key]
        button = self._buttons[key]
        size = 18 if self._collapsed else 16
        token = "bg_dark" if button.isChecked() else "text"
        button.setIcon(icons.icon(asset, size, token))
        button.setIconSize(QSize(px(size), px(size)))
        button.setText("" if self._collapsed else f"   {label}")
        button.setProperty("collapsed", "true" if self._collapsed else "false")
        # Tooltip only earns its place once the text is gone.
        button.setToolTip("" if not self._collapsed else label)
        repolish(button)

    # -- public API --------------------------------------------------------
    def refresh_icons(self) -> None:
        """Re-tint icons after a theme switch (the PNGs are black)."""
        self.burger.setIcon(icons.icon("list-details", 18, "gray_light"))
        for key in self._buttons:
            self._paint_nav(key)

    def set_active(self, key: str) -> None:
        button = self._buttons.get(key)
        if button is not None and not button.isChecked():
            button.setChecked(True)

    def set_storage(self, used_label: str, fraction: float) -> None:
        """Update the storage readout and bar (``fraction`` in 0.0..1.0)."""
        self.storage_label.setText(used_label)
        width = int(self._track.width() * max(0.0, min(1.0, fraction)))
        self._fill.setFixedWidth(max(2, width))
