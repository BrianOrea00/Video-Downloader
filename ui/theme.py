# ui/theme.py
"""Qt design system: semantic colour tokens + a QSS stylesheet.

Palette and layout tokens come from ``docs/ui-prototype.html`` (arisu-pink,
PHASES.md §4). Two themes — dark and light — share the same token names so
widgets never reference a raw hex value.
"""
from __future__ import annotations

from string import Template

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

# Semantic tokens per theme. Keys are shared across both themes.
TOKENS: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#0a0710",
        "bg_dark": "#05030a",
        "sidebar": "#08050e",
        "topbar": "#0c0814",
        "card": "#0f0b17",
        "popup": "#130e1c",
        "hover": "#1f192b",
        "border": "#2a1f3a",
        "text": "#f8f2ff",
        "text_2": "#c9c3d4",
        "muted": "#6b5b7e",
        "gray_light": "#8a7f9a",
        "accent": "#ff79c6",
        "pink_dim": "#e35aa5",
        "info": "#bd93f9",
        "success": "#50fa7b",
        "error": "#ff5555",
        "warning": "#ffb86c",
        "paused": "#f1fa8c",
        "track": "#3d3448",
    },
    "light": {
        "bg": "#fdfaff",
        "bg_dark": "#f7f2fb",
        "sidebar": "#f2ecfa",
        "topbar": "#fdfaff",
        "card": "#ffffff",
        "popup": "#ffffff",
        "hover": "#ece4f5",
        "border": "#d9cfe6",
        "text": "#2a1e33",
        "text_2": "#6b5b7e",
        "muted": "#8a7f9a",
        "gray_light": "#6b5b7e",
        "accent": "#c1549c",
        "pink_dim": "#a83e80",
        "info": "#7a5bbf",
        "success": "#3ec96a",
        "error": "#e34c4c",
        "warning": "#e8833c",
        "paused": "#c9a227",
        "track": "#d9cfe6",
    },
}

UI_FONT = "Monocraft"
FALLBACK_FONT = "monospace"
FONT_SIZE = 13

# Tracks the active theme so widget code can pull token colours on demand.
_active = {"theme": "dark"}

_QSS = Template(
    """
    QWidget {
        background: $bg;
        color: $text;
        font-size: ${size}px;
    }
    QMainWindow, #Content { background: $bg; }

    /* ---------- sidebar ---------- */
    #Sidebar { background: $sidebar; border-right: 1px solid $border; }
    #LogoMark {
        background: $accent; color: $bg_dark; border-radius: 5px;
        font-weight: 700; font-size: 12px;
    }
    #LogoTitle { font-size: 13px; font-weight: 700; color: $text; }
    #LogoSub { font-size: 10px; color: $muted; }
    #SectionLabel {
        font-size: 9px; letter-spacing: 1px; color: $muted; padding: 4px 8px;
    }
    QPushButton#NavButton {
        text-align: left; padding: 8px 10px; margin: 1px 0;
        border: 0; border-radius: 6px;
        background: transparent; color: $text; font-size: 12px;
    }
    QPushButton#NavButton:hover { background: $hover; }
    QPushButton#NavButton:checked {
        background: $accent; color: $bg_dark; font-weight: 600;
    }
    #StorageHead { font-size: 10px; color: $gray_light; }
    #Track { background: $border; border-radius: 2px; }
    #TrackFill { background: $accent; border-radius: 2px; }

    /* ---------- top bar ---------- */
    #TopBar { background: $topbar; border-bottom: 1px solid $border; }
    #PageTitle { font-size: 15px; font-weight: 700; color: $text; }
    #Badge {
        border: 1px solid $border; border-radius: 4px;
        padding: 2px 8px; color: $accent; font-size: 11px;
    }

    /* ---------- buttons ---------- */
    QPushButton {
        border: 1px solid $border; border-radius: 6px;
        background: $card; color: $text; padding: 7px 14px; font-size: 12px;
    }
    QPushButton:hover { background: $hover; }
    QPushButton:focus { border: 1px solid $accent; }
    QPushButton:disabled { color: $muted; background: $bg; }
    QPushButton#PrimaryButton {
        background: $accent; color: $bg_dark;
        border-color: transparent; font-weight: 600;
    }
    QPushButton#PrimaryButton:hover { background: $pink_dim; }
    QPushButton#DangerButton {
        background: transparent; color: $error; border-color: $error;
    }
    QPushButton#DangerButton:hover { background: $card; }

    /* ---------- inputs ---------- */
    QLineEdit {
        background: $bg; border: 1px solid $border; border-radius: 6px;
        color: $text; padding: 9px 12px;
    }
    QLineEdit:focus { border-color: $accent; }
    QLineEdit:disabled { color: $muted; }

    /* ---------- cards / containers ---------- */
    #Card {
        background: $card; border: 1px solid $border; border-radius: 10px;
    }
    QStackedWidget { background: transparent; }
    QScrollArea { background: transparent; border: 0; }
    QScrollArea > QWidget > QWidget { background: transparent; }
    #FieldLabel {
        font-size: 10px; letter-spacing: 1px; color: $muted;
    }

    /* ---------- queue page ---------- */
    QPushButton#Pill {
        border: 1px solid $border; border-radius: 14px; background: $bg;
        color: $gray_light; padding: 5px 14px;
    }
    QPushButton#Pill:hover { background: $hover; }
    QPushButton#Pill:checked {
        border-color: $accent; color: $accent; background: $hover;
    }
    #Chip {
        background: $card; border: 1px solid $border; border-radius: 4px;
        color: $gray_light; padding: 4px 10px; font-size: 11px;
    }
    #Row { background: $card; border: 1px solid $border; border-radius: 8px; }
    #RowActive { border: 1px solid $accent; }
    #RowTile {
        background: $bg; border: 1px solid $border; border-radius: 4px;
        color: $gray_light;
    }
    QProgressBar#RowProgress {
        background: $border; border: 0; border-radius: 2px; height: 4px;
    }
    QProgressBar#RowProgress::chunk { background: $accent; border-radius: 2px; }

    /* ---------- media lists ---------- */
    QListWidget { background: transparent; border: 0; outline: 0; }
    QListWidget::item { color: $text; padding: 6px; border-radius: 6px; }
    QListWidget::item:selected { background: $hover; color: $text; }
    #StatusLine { color: $gray_light; font-size: 11px; }

    /* ---------- scrollbars ---------- */
    QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
    QScrollBar::handle:vertical {
        background: $border; border-radius: 5px; min-height: 24px;
    }
    QScrollBar::handle:vertical:hover { background: $muted; }
    QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
    QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
    """
)


def stylesheet(theme: str) -> str:
    """Return the QSS for ``"dark"`` or ``"light"``."""
    tokens = TOKENS.get(theme, TOKENS["dark"])
    return _QSS.substitute(size=FONT_SIZE, **tokens)


def current_theme() -> str:
    return _active["theme"]


def color(key: str) -> str:
    """Resolve a semantic token against the currently applied theme."""
    return TOKENS[_active["theme"]].get(key, "#ff00ff")


def resolve_font() -> QFont:
    """Monocraft when installed, otherwise the platform monospace face."""
    families = set(QFontDatabase.families())
    family = UI_FONT if UI_FONT in families else FALLBACK_FONT
    return QFont(family, 10)


def apply_theme(app: QApplication, theme: str) -> None:
    """Apply the palette and font to the running application."""
    _active["theme"] = theme
    app.setFont(resolve_font())
    app.setStyleSheet(stylesheet(theme))
