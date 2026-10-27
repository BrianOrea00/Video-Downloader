# docs/make_screenshots.py
"""Render the README screenshots offscreen, with seeded sample data.

Run it from the repository root:

    QT_QPA_PLATFORM=offscreen python docs/make_screenshots.py

The script never touches your real data directory: it points
``VIDEO_DOWNLOADER_DATA_DIR`` at a temporary folder, writes a small fake
library and queue there, then grabs the window. Files in the library are
sparse, so the reported sizes look real without costing disk space.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA = Path(tempfile.mkdtemp(prefix="vd-screenshots-"))
os.environ["VIDEO_DOWNLOADER_DATA_DIR"] = str(DATA)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import config  # noqa: E402  (must see the env override above)
import persistence  # noqa: E402
import thumb_cache  # noqa: E402

SHOTS = ROOT / "docs" / "screenshots"
LIBRARY = DATA / "Downloads"
SIZE = (1440, 900)

VIDEOS = [
    ("Blender Open Movie - Spring.mp4", 640_000_000, "#4f7cff", "#9b5cff"),
    ("Krita 5.2 Release Trailer.mp4", 96_000_000, "#ff7a4f", "#ffb44f"),
    ("Creative Coding - Particles in 12 Minutes.mp4", 210_000_000, "#2fc4a8", "#3f8cff"),
    ("Inkscape Basics - Full Course.mp4", 1_180_000_000, "#f2547d", "#8f4fff"),
]
MUSIC = [
    ("Aurora Fields.mp3", 9_400_000, "#3f8cff", "#2fc4a8"),
    ("Night Drive.mp3", 7_100_000, "#7a5cff", "#f2547d"),
    ("Slow Sunday.mp3", 6_300_000, "#ffb44f", "#ff7a4f"),
]

QUEUE = [
    ("Krita 5.2 Release Trailer", "completed", "Download completed successfully!"),
    ("Aurora Fields", "completed", "Download completed successfully!"),
    ("Creative Coding - Particles in 12 Minutes", "pending", ""),
    ("Inkscape Basics - Full Course", "pending", ""),
]


def _sparse(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.truncate(size)


def _thumbnail(folder: Path, filename: str, start: str, end: str) -> None:
    """A gradient tile stands in for cover art we cannot ship."""
    image = QPixmap(480, 270)
    gradient = QLinearGradient(QPointF(0, 0), QPointF(480, 270))
    gradient.setColorAt(0.0, QColor(start))
    gradient.setColorAt(1.0, QColor(end))
    image.fill(QColor(start))
    painter = QPainter(image)
    painter.fillRect(QRectF(0, 0, 480, 270), gradient)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(0, 0, 0, 40))
    painter.drawEllipse(QPointF(240, 135), 44, 44)
    painter.end()
    target = thumb_cache.thumb_path(str(folder), filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(target), "JPEG", 85)


def seed() -> None:
    for name, size, start, end in VIDEOS:
        _sparse(LIBRARY / name, size)
        _thumbnail(LIBRARY, name, start, end)
    for name, size, start, end in MUSIC:
        _sparse(LIBRARY / name, size)
        _thumbnail(LIBRARY, name, start, end)

    settings = dict(config.DEFAULT_SETTINGS)
    settings.update({
        "download_path": str(LIBRARY),
        "ui_scale": 1.25,
        "last_page": "queue",
    })
    persistence.save_settings(settings)

    items = []
    for index, (title, status, message) in enumerate(QUEUE):
        items.append({
            "url": f"https://www.youtube.com/watch?v=sample{index}",
            "path": str(LIBRARY),
            "resolution": "720",
            "audio_only": title == "Aurora Fields",
            "title": title,
            "status": status,
            "date_added": "2026-10-26 09:41:12",
            "message": message,
            "filename": f"{title}.{'mp3' if title == 'Aurora Fields' else 'mp4'}",
        })
    persistence.save_queue(items)
    for entry in items[:2]:
        persistence.save_history({
            "url": entry["url"],
            "title": entry["title"],
            "filename": entry["filename"],
        })


def settle(app: QApplication, seconds: float = 0.35) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)


def main() -> int:
    app = QApplication(sys.argv)   # QPixmap needs a GUI application first
    seed()
    from ui.main_window import MainWindow
    from ui.theme import apply_theme, set_motion, set_ui_scale

    settings = persistence.load_settings()
    set_ui_scale(float(settings.get("ui_scale", 1.25)))
    set_motion(True)
    apply_theme(app, settings.get("theme_family", "arisu"), settings.get("theme", "dark"))

    window = MainWindow(settings)
    window.resize(*SIZE)
    window.show()
    settle(app)

    SHOTS.mkdir(parents=True, exist_ok=True)
    for key in ("queue", "videos", "music", "settings"):
        window.show_page(key)
        window.stack.currentWidget().update()
        settle(app, 0.6)
        path = SHOTS / f"{key}.png"
        window.grab().save(str(path), "PNG")
        print(f"{key}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
