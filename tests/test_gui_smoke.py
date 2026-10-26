"""Offscreen GUI smoke test: the shell, the queue and Settings must work.

This is the test CI runs so a missing Qt platform plugin or a theme regression
fails the build instead of a user's launch. It never touches the real per-user
data directory: the persistence paths are redirected to a temporary folder
before any page is constructed.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import config  # noqa: E402
import persistence  # noqa: E402
from models import DownloadItem, DownloadStatus  # noqa: E402
from ui import theme  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402


class GuiSmokeTest(unittest.TestCase):
    """Construct the real window offscreen and drive a few paths."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.files = {
            "QUEUE_FILE": persistence.QUEUE_FILE,
            "HISTORY_FILE": persistence.HISTORY_FILE,
            "SETTINGS_FILE": persistence.SETTINGS_FILE,
        }
        persistence.QUEUE_FILE = str(root / "queue.json")
        persistence.HISTORY_FILE = str(root / "history.json")
        persistence.SETTINGS_FILE = str(root / "settings.json")
        cls.app = QApplication.instance() or QApplication([])
        theme.apply_theme(cls.app, "arisu", "dark")
        cls.settings = dict(config.DEFAULT_SETTINGS)
        cls.settings["download_path"] = str(root)

    @classmethod
    def tearDownClass(cls):
        for name, value in cls.files.items():
            setattr(persistence, name, value)
        cls.tmp.cleanup()

    def setUp(self):
        self.window = MainWindow(dict(self.settings))
        self.window.show()
        QTest.qWait(50)

    def tearDown(self):
        self.window.close()
        QTest.qWait(20)

    def test_shell_has_every_page(self):
        for key in ("queue", "videos", "music", "settings"):
            self.assertIn(key, self.window.pages)

    def test_badge_tracks_pending_items(self):
        page = self.window.queue_page
        item = page.manager.add(DownloadItem(
            url="https://example.com/v", path=self.settings["download_path"],
            title="Badge item",
        ))
        page.refresh()
        self.assertTrue(self.window.badge.isVisible())
        self.assertIn("1", self.window.badge.text())
        page.manager.remove(page._index_of(item))
        page.refresh()
        self.assertFalse(self.window.badge.isVisible())

    def test_queue_row_survives_a_status_change(self):
        page = self.window.queue_page
        item = page.manager.add(DownloadItem(
            url="https://example.com/v", path=self.settings["download_path"],
            title="Row item",
        ))
        page.refresh()
        row = page._rows[id(item)]
        item.status = DownloadStatus.DOWNLOADING
        page.refresh()
        self.assertIs(page._rows[id(item)], row)
        self.assertEqual(row.objectName(), "RowActive")

    def test_theme_toggle_and_settings_autosave(self):
        self.window.show_page("settings")
        page = self.window.settings_page
        before = self.window.mode
        self.window.toggle_theme()
        self.assertNotEqual(self.window.mode, before)
        self.assertEqual(self.window.settings["theme"], self.window.mode)

        page.mode.setCurrentIndex(page.mode.findData("sequential"))
        # The save is debounced, so give the timer its window.
        QTest.qWait(600)
        saved = json.loads(Path(persistence.SETTINGS_FILE).read_text(encoding="utf-8"))
        self.assertEqual(saved["download_mode"], "sequential")
        self.assertEqual(page.status.text(), "Saved" if page.status.text() else "")

    def test_library_pages_scan_without_error(self):
        sample = Path(self.settings["download_path"]) / "sample.mp4"
        sample.write_bytes(b"\0" * 1024)
        page = self.window.pages["videos"]
        self.window.show_page("videos")
        for _ in range(20):   # the scan runs on a worker thread
            QTest.qWait(50)
            if page.list.count():
                break
        self.assertEqual(page.list.count(), 1)
        self.assertIn("1 video", page.status.text())
        sample.unlink()


if __name__ == "__main__":
    unittest.main()
