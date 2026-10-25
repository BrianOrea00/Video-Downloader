# ui/theme.py
"""Qt design system: semantic colour tokens + a QSS stylesheet.

Three theme families — ``arisu`` (the original arisu-pink, from
``docs/ui-prototype.html`` / PHASES.md §4), ``saas`` (blue on white) and
``arch`` (Arch Linux blue) — each with a ``dark`` and a ``light`` mode. Every
palette shares the same token names so widgets never reference a raw hex value.
"""
from __future__ import annotations

import re
from string import Template

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

# Semantic tokens per theme. Keys are shared across both themes.
THEMES: dict[str, dict[str, dict[str, str]]] = {
    # The original palette: arisu-pink (the user's nvim colorscheme).
    "arisu": {
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
            "muted": "#9284a6",
            "gray_light": "#8a7f9a",
            "accent": "#ff79c6",
            "accent_dim": "#e35aa5",
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
            "muted": "#6b5b7e",
            "gray_light": "#6b5b7e",
            "accent": "#9c3676",
            "accent_dim": "#83305f",
            "info": "#6a3fb5",
            "success": "#1a7f37",
            "error": "#b42323",
            "warning": "#9a5410",
            "paused": "#7a5c00",
            "track": "#d9cfe6",
        },
    },
    # Blue on white SaaS look. The accent is dark enough to stay legible as the
    # fill of a primary button in light mode.
    "saas": {
        "dark": {
            "bg": "#0b1220",
            "bg_dark": "#070d18",
            "sidebar": "#0a1020",
            "topbar": "#0d1526",
            "card": "#111a2e",
            "popup": "#16203a",
            "hover": "#1b2740",
            "border": "#263451",
            "text": "#f5f8ff",
            "text_2": "#c3cde0",
            "muted": "#8593ad",
            "gray_light": "#9aa7bd",
            "accent": "#3b82f6",
            "accent_dim": "#2f6fd8",
            "info": "#60a5fa",
            "success": "#34d399",
            "error": "#f87171",
            "warning": "#fbbf24",
            "paused": "#facc15",
            "track": "#223049",
        },
        "light": {
            "bg": "#f8fafc",
            "bg_dark": "#f1f5f9",
            "sidebar": "#eef2f7",
            "topbar": "#ffffff",
            "card": "#ffffff",
            "popup": "#ffffff",
            "hover": "#e8eef7",
            "border": "#d3dced",
            "text": "#0f172a",
            "text_2": "#475569",
            "muted": "#5b6a7d",
            "gray_light": "#5b6a7d",
            "accent": "#2563eb",
            "accent_dim": "#1d4ed8",
            "info": "#2563eb",
            "success": "#15803d",
            "error": "#dc2626",
            "warning": "#b45309",
            "paused": "#a16207",
            "track": "#dbe3f0",
        },
    },
    # Arch Linux blue #1793D1. Light mode darkens the accent so the button text
    # stays legible; dark mode keeps the official shade.
    "arch": {
        "dark": {
            "bg": "#0b0f14",
            "bg_dark": "#06090c",
            "sidebar": "#0a0e13",
            "topbar": "#0d1218",
            "card": "#11171f",
            "popup": "#151c26",
            "hover": "#1b242f",
            "border": "#26313d",
            "text": "#e8f1f8",
            "text_2": "#b6c6d4",
            "muted": "#7d90a1",
            "gray_light": "#8d9fb0",
            "accent": "#1793d1",
            "accent_dim": "#127cb0",
            "info": "#33b1ff",
            "success": "#4ade80",
            "error": "#f87171",
            "warning": "#fbbf24",
            "paused": "#facc15",
            "track": "#1d2833",
        },
        "light": {
            "bg": "#f9fbfd",
            "bg_dark": "#eef4f9",
            "sidebar": "#eaf2f8",
            "topbar": "#ffffff",
            "card": "#ffffff",
            "popup": "#ffffff",
            "hover": "#e3eef7",
            "border": "#cadbe8",
            "text": "#0f1720",
            "text_2": "#46586a",
            "muted": "#5c6f80",
            "gray_light": "#5c6f80",
            "accent": "#0e73a8",
            "accent_dim": "#0b5c88",
            "info": "#0e73a8",
            "success": "#15803d",
            "error": "#dc2626",
            "warning": "#b45309",
            "paused": "#a16207",
            "track": "#d5e3ee",
        },
    },
}

THEME_LABELS = {
    "arisu": "Arisu Pink",
    "saas": "SaaS Blue",
    "arch": "Arch Blue",
}
MODES = ("dark", "light")
MODE_LABELS = {"dark": "Dark", "light": "Light"}
DEFAULT_FAMILY = "arisu"
DEFAULT_MODE = "dark"

# Two type roles. ``ui`` reads as prose (titles, labels, buttons, help text);
# ``mono`` aligns numbers and identifiers (sizes, speeds, ETA, durations, paths).
MONO_FONT = "Monocraft"          # bundled in the release build
UI_FONT_CANDIDATES = (
    "Inter", "Noto Sans", "Segoe UI", "SF Pro Text", "Ubuntu", "DejaVu Sans",
)
FALLBACK_MONO = "monospace"

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
    _state["scale"] = max(0.5, float(scale))


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
    return _state["scale"]


def px(base: int) -> int:
    """Scale a design-time pixel value (``1x``) to the active UI scale.

    Zero and negative values pass through unchanged so ``px(0)`` stays ``0``.
    """
    if base <= 0:
        return base
    return max(1, round(base * _state["scale"]))


def font_size() -> int:
    """Body font size in QSS pixels."""
    return px(BASE_FONT_SIZE)


def font_pt() -> int:
    """Body font point size for ``QFont``."""
    return max(1, round(BASE_FONT_PT * _state["scale"]))


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

# Tracks the active scale and theme so widget code can pull values on demand.
_state = {"scale": BASE_UI_SCALE, "family": DEFAULT_FAMILY, "mode": DEFAULT_MODE}

# QSS template. ``@{n}`` is a design-time pixel value scaled by :func:`px`;
# ``$name`` is a colour token from :data:`THEMES`. Hairline borders stay 1px.
_QSS_RAW = """
    QWidget {
        color: $text;
        font-size: $size;
    }
    QMainWindow, #Content, QStackedWidget, QScrollArea { background: $bg; }
    QScrollArea > QWidget > QWidget { background: transparent; }
    QLabel, QCheckBox { background: transparent; }

    /* ---------- sidebar ---------- */
    #Sidebar { background: $sidebar; border-right: 1px solid $border; }
    #LogoMark {
        background: $accent; color: $bg_dark; border-radius: @{5}px;
        font-weight: 700; font-size: @{12}px;
    }
    #LogoTitle { font-size: @{13}px; font-weight: 700; color: $text; }
    #LogoSub { font-family: "$mono"; font-size: @{10}px; color: $muted; }
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
    #StorageHead { font-family: "$mono"; font-size: @{10}px; color: $gray_light; }
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
    QPushButton:focus { border: 2px solid $accent; padding: @{6}px @{13}px; }
    QPushButton:disabled { color: $muted; background: $bg; }
    QPushButton#NavButton:focus { border: 1px solid $accent; }
    QPushButton#PrimaryButton {
        background: $accent; color: $bg_dark;
        border-color: transparent; font-weight: 600;
    }
    QPushButton#PrimaryButton:hover { background: $accent_dim; }
    QPushButton#PrimaryButton:focus { border: 2px solid $text; }
    QPushButton#PrimaryButton:disabled {
        background: $bg; color: $muted; border-color: $border;
    }
    QPushButton#DangerButton {
        background: transparent; color: $error; border-color: $error;
    }
    QPushButton#DangerButton:hover { background: $card; }
    QPushButton#DangerButton:disabled {
        background: transparent; color: $muted; border-color: $border;
    }

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
    QScrollArea { border: 0; }
    #FieldLabel {
        font-size: @{10}px; letter-spacing: @{1}px; color: $muted;
    }
    #FormName { font-size: @{12}px; color: $text; }
    #FormHelp { font-size: @{11}px; color: $gray_light; }
    #PathLabel { font-family: "$mono"; font-size: @{11}px; color: $gray_light; }

    /* ---------- queue page ---------- */
    QPushButton#Pill {
        border: 1px solid $border; border-radius: @{14}px; background: $bg;
        color: $gray_light; padding: @{5}px @{14}px;
    }
    QPushButton#Pill:hover { background: $hover; }
    QPushButton#Pill:checked {
        border-color: $accent; color: $accent; background: $hover;
    }
    QPushButton#Pill:disabled {
        border-color: $border; color: $muted; background: $bg;
    }
    #Chip {
        background: $card; border: 1px solid $border; border-radius: @{4}px;
        color: $gray_light; padding: @{4}px @{10}px; font-size: @{11}px;
    }
    #Row { background: $card; border: 1px solid $border; border-radius: @{8}px; }
    #PreviewCard {
        background: $bg; border: 1px solid $border; border-radius: @{8}px;
    }
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
    QListWidget:focus { border: 1px solid $accent; }
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


def family_names() -> list[str]:
    """Theme families in display order."""
    return list(THEMES)


def tokens(family: str | None = None, mode: str | None = None) -> dict[str, str]:
    """Colour tokens for a family/mode.

    Omitted arguments read the *active* theme, not the built-in defaults, so a
    bare ``tokens()`` and :func:`stylesheet` always agree with :func:`apply_theme`.
    """
    family = family if family in THEMES else _state["family"]
    mode = mode if mode in THEMES[family] else _state["mode"]
    return THEMES[family][mode]


def stylesheet(family: str | None = None, mode: str | None = None) -> str:
    """QSS for a family/mode at the active UI scale."""
    body = _PX_RE.sub(lambda m: str(px(int(m.group(1)))), _QSS_RAW)
    return Template(body).substitute(size=f"{font_size()}px",
                                     mono=mono_family(),
                                     **tokens(family, mode))


def current_family() -> str:
    return _state["family"]


def current_mode() -> str:
    return _state["mode"]


def flip_mode(mode: str | None = None) -> str:
    """The opposite mode, defaulting to the active one."""
    current = mode if mode in MODES else _state["mode"]
    return "light" if current == "dark" else "dark"


def color(key: str) -> str:
    """Resolve a semantic token against the active family and mode."""
    return tokens(_state["family"], _state["mode"]).get(key, "#ff00ff")


def ui_family() -> str:
    """System UI sans, preferring the faces a release build bundles."""
    families = set(QFontDatabase.families())
    for name in UI_FONT_CANDIDATES:
        if name in families:
            return name
    return QFontDatabase.systemFont(QFontDatabase.GeneralFont).family()


def mono_family() -> str:
    """Monocraft when installed, otherwise the platform monospace face."""
    families = set(QFontDatabase.families())
    return MONO_FONT if MONO_FONT in families else FALLBACK_MONO


def mono_css() -> str:
    """Inline ``font-family`` declaration for the mono role."""
    return f'font-family: "{mono_family()}";'


def resolve_font() -> QFont:
    """The application font: the prose role, never the mono face."""
    return QFont(ui_family(), font_pt())


def apply_theme(app: QApplication, family: str | None = None,
                mode: str | None = None) -> None:
    """Apply a palette, the font and the scale to the running application.

    An omitted argument keeps the current value; an unrecognised one falls back
    to the default. ``apply_theme(app, "light")`` is still accepted and reads as
    a mode, since no family is called ``"light"``.
    """
    if family in MODES and family not in THEMES:
        family, mode = None, family
    if family is None:
        family = _state["family"]
    elif family not in THEMES:
        family = DEFAULT_FAMILY
    if mode is None:
        mode = _state["mode"]
    elif mode not in MODES:
        mode = DEFAULT_MODE
    _state["family"] = family
    _state["mode"] = mode
    app.setFont(resolve_font())
    app.setStyleSheet(stylesheet())
