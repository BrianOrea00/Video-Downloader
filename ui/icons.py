# ui/icons.py
"""One icon source for the whole UI.

The PNG assets in ``assets/`` are solid black Tabler glyphs, so they are
re-tinted with a theme token before use; a black icon would vanish on the dark
palettes. Sizes come from the UI scale, never from raw pixel values in widgets.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap

from ui import theme
from utils import resource_path

DEFAULT_SIZE = 16

_cache: dict[tuple[str, int, str], QPixmap] = {}


def pixmap(name: str, size: int = DEFAULT_SIZE, color_key: str = "text") -> QPixmap:
    """Tinted pixmap for ``name`` at the active scale, cached per colour."""
    pixels = theme.px(size)
    hex_color = theme.color(color_key)
    key = (name, pixels, hex_color)
    cached = _cache.get(key)
    if cached is not None:
        return cached

    source = QImage(resource_path(f"assets/{name}.png"))
    if source.isNull():
        return QPixmap()

    tinted = QImage(source.size(), QImage.Format_ARGB32)
    tinted.fill(Qt.transparent)
    painter = QPainter(tinted)
    painter.drawImage(0, 0, source)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), QColor(hex_color))
    painter.end()

    scaled = QPixmap.fromImage(
        tinted.scaled(pixels, pixels, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    )
    _cache[key] = scaled
    return scaled


def icon(name: str, size: int = DEFAULT_SIZE, color_key: str = "text") -> QIcon:
    """``QIcon`` wrapper around :func:`pixmap`."""
    return QIcon(pixmap(name, size, color_key))
