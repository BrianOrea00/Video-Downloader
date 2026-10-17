# main.py
"""PySide6 entry point (Phase 8 port)."""
import sys

from PySide6.QtWidgets import QApplication

from logger import logger
from persistence import load_settings
from ui.main_window import MainWindow
from ui.theme import DEFAULT_UI_SCALE, apply_theme, set_ui_scale


def main() -> int:
    logger.info("Starting Video Downloader")
    app = QApplication(sys.argv)
    app.setApplicationName("Video Downloader")

    settings = load_settings()
    set_ui_scale(float(settings.get("ui_scale", DEFAULT_UI_SCALE)))
    apply_theme(app, settings.get("theme", "dark"))

    window = MainWindow(settings)
    window.show()

    code = app.exec()
    logger.info("Application closed")
    return code


if __name__ == "__main__":
    sys.exit(main())
