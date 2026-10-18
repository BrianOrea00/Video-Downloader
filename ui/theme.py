# ui/theme.py
"""Qt design system: semantic colour tokens + a QSS stylesheet.

Palette and layout tokens come from ``docs/ui-prototype.html`` (arisu-pink,
PHASES.md §4). Two themes — dark and light — share the same token names so
widgets never reference a raw hex value.
"""
from __future__ import annotations

import re
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

# ---- UI scale ---------------------------------------------------------------
# Every pixel size in the app derives from BASE_* multiplied by UI_SCALE, so the
# whole interface grows or shrinks together. Change UI_SCALE only; do not hardcode
# pixel values in widget code.
BASE_UI_SCALE = 1.0   # design size
DEFAULT_UI_SCALE = 1.5  # shipped default = 50% larger than the 1x design size
BASE_FONT_SIZE = 13   # QSS px for body text
BASE_FONT_PT = 10     # QFont point size


def set_ui_scale(scale: float) -> None:
    """Set the global UI scale (1.0 = design size, 2.0 = double)."""
    _tokens["scale"] = max(0.5, float(scale))


def repolish(widget) -> None:
    """Re-apply the stylesheet after a dynamic property changed.

    Qt only re-evaluates property selectors such as ``[collapsed="true"]`` when
    the widget is unpolished and polished again.
    """
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def ui_scale() -> float:
    return _tokens["scale"]


def px(base: int) -> int:
    """Scale a design-time pixel value (``1x``) to the active UI scale.

    Zero and negative values pass through unchanged so ``px(0)`` stays ``0``.
    """
    if base <= 0:
        return base
    return max(1, round(base * _tokens["scale"]))


def font_size() -> int:
    """Body font size in QSS pixels."""
    return px(BASE_FONT_SIZE)


def font_pt() -> int:
    """Body font point size for ``QFont``."""
    return max(1, round(BASE_FONT_PT * _tokens["scale"]))


# Scale-dependent widget metrics, all in design-time (1x) pixels.
METRICS = {
    "sidebar_width": 240,
    "sidebar_collapsed_width": 68,
    "topbar_height": 56,
    "logo_mark": 22,
    "shelf": 3,           # storage meter bar height
    "row_tile_w": 40,
    "row_tile_h": 28,
    "row_thumb_w": 96,
    "row_thumb_h": 54,
    "row_action": 28,
    "row_progress": 4,
    "search_width": 220,
    "grid_icon_w": 160,
    "grid_icon_h": 90,
    "grid_cell_w": 200,
    "grid_cell_h": 150,
    "label_column": 240,  # settings label column
    "min_window_w": 900,
    "min_window_h": 600,
}

# Tracks the active theme/scale so widget code can pull values on demand.
_tokens = {"scale": BASE_UI_SCALE, "theme": "dark"}

# QSS template. ``@{n}`` is a design-time pixel value scaled by :func:`px`;
# ``$name`` is a colour token from :data:`TOKENS`. Hairline borders stay 1px.
_QSS_RAW = """
    QWidget {
        background: $bg;
        color: $text;
        font-size: $size;
    }
    QMainWindow, #Content { background: $bg; }

    /* ---------- sidebar ---------- */
    #Sidebar { background: $sidebar; border-right: 1px solid $border; }
    #LogoMark {
        background: $accent; color: $bg_dark; border-radius: @{5}px;
        font-weight: 700; font-size: @{12}px;
    }
    #LogoTitle { font-size: @{13}px; font-weight: 700; color: $text; }
    #LogoSub { font-size: @{10}px; color: $muted; }
    #SectionLabel {
        font-size: @{9}px; letter-spacing: @{1}px; color: $muted;
        padding: @{4}px @{8}px;
    }
    QPushButton#NavButton {
        text-align: left; padding: @{8}px @{10}px; margin: @{1}px 0;
        border: 0; border-radius: @{6}px;
        background: transparent; color: $text; font-size: @{12}px;
    }
    QPushButton#NavButton:hover { background: $hover; }
    QPushButton#NavButton:checked {
        background: $accent; color: $bg_dark; font-weight: 600;
    }
    /* collapsed rail: glyph only, centred, larger for legibility */
    QPushButton#NavButton[collapsed="true"] {
        text-align: center; padding: @{12}px 0; font-size: @{16}px;
    }
    QPushButton#BurgerButton {
        border: 0; background: transparent; color: $gray_light;
        padding: @{6}px @{8}px; border-radius: @{6}px; font-size: @{15}px;
    }
    QPushButton#BurgerButton:hover { background: $hover; color: $text; }
    QPushButton#BurgerButton:focus { border: 1px solid $accent; }
    #StorageHead { font-size: @{10}px; color: $gray_light; }
    #Track { background: $border; border-radius: @{2}px; }
    #TrackFill { background: $accent; border-radius: @{2}px; }

    /* ---------- top bar ---------- */
    #TopBar { background: $topbar; border-bottom: 1px solid $border; }
    #PageTitle { font-size: @{15}px; font-weight: 700; color: $text; }
    #Badge {
        border: 1px solid $border; border-radius: @{4}px;
        padding: @{2}px @{8}px; color: $accent; font-size: @{11}px;
    }

    /* ---------- buttons ---------- */
    QPushButton {
        border: 1px solid $border; border-radius: @{6}px;
        background: $card; color: $text; padding: @{7}px @{14}px;
        font-size: @{12}px;
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
        background: $bg; border: 1px solid $border; border-radius: @{6}px;
        color: $text; padding: @{9}px @{12}px;
    }
    QLineEdit:focus { border-color: $accent; }
    QLineEdit:disabled { color: $muted; }
    QComboBox, QSpinBox {
        background: $bg; border: 1px solid $border; border-radius: @{6}px;
        color: $text; padding: @{7}px @{10}px;
    }
    QComboBox:focus, QSpinBox:focus { border-color: $accent; }
    QComboBox:disabled, QSpinBox:disabled { color: $muted; }
    QComboBox QAbstractItemView {
        background: $popup; border: 1px solid $border; color: $text;
        selection-background-color: $hover; outline: 0;
    }
    QCheckBox { color: $text; spacing: @{8}px; }
    QCheckBox::indicator { width: @{14}px; height: @{14}px; }

    /* ---------- cards / containers ---------- */
    #Card {
        background: $card; border: 1px solid $border; border-radius: @{10}px;
    }
    QStackedWidget { background: transparent; }
    QScrollArea { background: transparent; border: 0; }
    QScrollArea > QWidget > QWidget { background: transparent; }
    #FieldLabel {
        font-size: @{10}px; letter-spacing: @{1}px; color: $muted;
    }
    #FormName { font-size: @{12}px; color: $text; }
    #FormHelp { font-size: @{11}px; color: $gray_light; }

    /* ---------- queue page ---------- */
    QPushButton#Pill {
        border: 1px solid $border; border-radius: @{14}px; background: $bg;
        color: $gray_light; padding: @{5}px @{14}px;
    }
    QPushButton#Pill:hover { background: $hover; }
    QPushButton#Pill:checked {
        border-color: $accent; color: $accent; background: $hover;
    }
    #Chip {
        background: $card; border: 1px solid $border; border-radius: @{4}px;
        color: $gray_light; padding: @{4}px @{10}px; font-size: @{11}px;
    }
    #Row { background: $card; border: 1px solid $border; border-radius: @{8}px; }
    #RowActive { border: 1px solid $accent; }
    #RowTile {
        background: $bg; border: 1px solid $border; border-radius: @{4}px;
        color: $gray_light;
    }
    QProgressBar#RowProgress {
        background: $border; border: 0; border-radius: @{2}px; height: @{4}px;
    }
    QProgressBar#RowProgress::chunk { background: $accent; border-radius: @{2}px; }

    /* ---------- media lists ---------- */
    QListWidget { background: transparent; border: 0; outline: 0; }
    QListWidget::item { color: $text; padding: @{6}px; border-radius: @{6}px; }
    QListWidget::item:selected { background: $hover; color: $text; }
    #StatusLine { color: $gray_light; font-size: @{11}px; }

    /* ---------- scrollbars ---------- */
    QScrollBar:vertical { background: transparent; width: @{10}px; margin: 0; }
    QScrollBar::handle:vertical {
        background: $border; border-radius: @{5}px; min-height: @{24}px;
    }
    QScrollBar::handle:vertical:hover { background: $muted; }
    QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
    QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
    """

_PX_RE = re.compile(r"@\{(\d+)\}")


def stylesheet(theme: str) -> str:
    """QSS for ``"dark"`` or ``"light"`` at the active UI scale."""
    tokens = dict(TOKENS.get(theme, TOKENS["dark"]))
    body = _PX_RE.sub(lambda m: str(px(int(m.group(1)))), _QSS_RAW)
    return Template(body).substitute(size=f"{font_size()}px", **tokens)


def current_theme() -> str:
    return _tokens["theme"]


def color(key: str) -> str:
    """Resolve a semantic token against the currently applied theme."""
    return TOKENS[_tokens["theme"]].get(key, "#ff00ff")


def resolve_font() -> QFont:
    """Monocraft when installed, otherwise the platform monospace face."""
    families = set(QFontDatabase.families())
    family = UI_FONT if UI_FONT in families else FALLBACK_FONT
    return QFont(family, font_pt())


def apply_theme(app: QApplication, theme: str) -> None:
    """Apply the palette, font and scale to the running application."""
    _tokens["theme"] = theme
    app.setFont(resolve_font())
    app.setStyleSheet(stylesheet(theme))
