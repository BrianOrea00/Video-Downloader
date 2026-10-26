# main.py
"""PySide6 entry point (Phase 8 port)."""
import os
import sys

from PySide6.QtCore import QLockFile
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

import config
import engine
from logger import logger
from persistence import load_settings
from utils import resource_path


def _install_excepthook() -> None:
    """Log uncaught exceptions and surface them instead of dying silently.

    A windowed build has no visible stderr, so a Qt slot exception would
    otherwise just close or freeze the app with no trace for the user.
    """

    def handle(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        logger.critical("Unhandled exception", exc_info=(exc_type, exc, tb))
        try:
            QMessageBox.critical(
                None,
                "Video Downloader",
                f"Something went wrong:\n\n{exc}\n\n"
                "Details were written to the application log.",
            )
        except Exception:  # noqa: BLE001 - never recurse inside the hook
            pass

    sys.excepthook = handle


def main() -> int:
    logger.info("Starting Video Downloader")
    # Before any module imports yt_dlp: a newer engine on disk wins over the
    # bundled copy. Everything under ui/ imports it transitively, so the UI
    # imports below must stay inside main().
    engine.activate()
    from ui.main_window import MainWindow
    from ui.theme import (
        DEFAULT_FAMILY,
        DEFAULT_MODE,
        DEFAULT_UI_SCALE,
        apply_theme,
        set_motion,
        set_ui_scale,
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Video Downloader")
    app.setApplicationVersion(config.APP_VERSION)
    # Without these the dock/taskbar shows a generic Python icon and Linux
    # launchers cannot match the window to the desktop entry.
    app.setDesktopFileName("video-downloader")
    icon = QIcon(resource_path("assets/appicon.png"))
    if not icon.isNull():
        app.setWindowIcon(icon)
    _install_excepthook()

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
    set_motion(not settings.get("reduce_motion", False))
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
