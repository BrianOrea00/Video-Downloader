# main.py
"""PySide6 entry point (Phase 8 port)."""
import os
import sys

from PySide6.QtCore import QLockFile
from PySide6.QtWidgets import QApplication, QMessageBox

import config
from logger import logger
from persistence import load_settings
from ui.main_window import MainWindow
from ui.theme import DEFAULT_FAMILY, DEFAULT_MODE, DEFAULT_UI_SCALE, apply_theme, set_ui_scale


def main() -> int:
    logger.info("Starting Video Downloader")
    app = QApplication(sys.argv)
    app.setApplicationName("Video Downloader")

    # One process per user data directory: two instances would race the
    # queue file and can download the same item twice.
    os.makedirs(config.DATA_DIR, exist_ok=True)
    lock = QLockFile(os.path.join(config.DATA_DIR, "app.lock"))
    if not lock.tryLock(100):
        logger.warning("Another instance holds %s", lock.fileName())
        QMessageBox.information(
            None, "Video Downloader", "Video Downloader is already running."
        )
        return 0

    migrated = config.migrate_legacy_files()
    if migrated:
        logger.info("Migrated %s into %s", ", ".join(migrated), config.DATA_DIR)

    settings = load_settings()
    set_ui_scale(float(settings.get("ui_scale", DEFAULT_UI_SCALE)))
    apply_theme(app,
                settings.get("theme_family", DEFAULT_FAMILY),
                settings.get("theme", DEFAULT_MODE))

    window = MainWindow(settings)
    window.show()

    code = app.exec()
    logger.info("Application closed")
    return code


if __name__ == "__main__":
    sys.exit(main())
