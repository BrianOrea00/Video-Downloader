# tests/test_persistence.py
"""Unit tests for thread-safe, atomic JSON persistence."""
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path

import config
import persistence


class PersistenceTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.queue_file = str(root / "queue.json")
        self.history_file = str(root / "history.json")
        self.settings_file = str(root / "settings.json")
        self._orig = (
            persistence.QUEUE_FILE,
            persistence.HISTORY_FILE,
            persistence.SETTINGS_FILE,
        )
        persistence.QUEUE_FILE = self.queue_file
        persistence.HISTORY_FILE = self.history_file
        persistence.SETTINGS_FILE = self.settings_file

    def tearDown(self):
        (
            persistence.QUEUE_FILE,
            persistence.HISTORY_FILE,
            persistence.SETTINGS_FILE,
        ) = self._orig
        self._tmp.cleanup()


class QueuePersistenceTests(PersistenceTestBase):
    def test_roundtrip(self):
        persistence.save_queue([{"url": "a"}])
        self.assertEqual(persistence.load_queue(), [{"url": "a"}])

    def test_missing_file_returns_empty_list(self):
        self.assertEqual(persistence.load_queue(), [])

    def test_corrupt_file_returns_empty_list(self):
        Path(self.queue_file).write_text("{not json", encoding="utf-8")
        self.assertEqual(persistence.load_queue(), [])

    def test_non_list_json_returns_empty_list(self):
        Path(self.queue_file).write_text('{"a": 1}', encoding="utf-8")
        self.assertEqual(persistence.load_queue(), [])

    def test_concurrent_writes_leave_valid_json(self):
        def writer(n):
            persistence.save_queue([{"url": f"u{n}"}] * 50)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        # The file must still be parseable (atomic replace, single lock).
        data = json.loads(Path(self.queue_file).read_text(encoding="utf-8"))
        self.assertIsInstance(data, list)


class HistoryPersistenceTests(PersistenceTestBase):
    def test_append_stamps_date(self):
        persistence.save_history({"url": "a"})
        persistence.save_history({"url": "b", "date_added": "fixed"})
        history = persistence.load_history()
        self.assertEqual(len(history), 2)
        self.assertIn("date_added", history[0])
        self.assertEqual(history[1]["date_added"], "fixed")


class SettingsPersistenceTests(PersistenceTestBase):
    def test_defaults_are_merged_for_missing_keys(self):
        Path(self.settings_file).write_text('{"theme": "light"}', encoding="utf-8")
        settings = persistence.load_settings()
        self.assertEqual(settings["theme"], "light")   # user value wins
        self.assertEqual(settings["parallel_limit"], 2)  # default filled in

    def test_blank_download_path_falls_back_to_the_default(self):
        Path(self.settings_file).write_text('{"download_path": ""}', encoding="utf-8")
        settings = persistence.load_settings()
        self.assertEqual(settings["download_path"],
                         config.DEFAULT_SETTINGS["download_path"])
        self.assertTrue(settings["download_path"])

    def test_defaults_written_when_file_absent(self):
        settings = persistence.load_settings()
        self.assertTrue(Path(self.settings_file).exists())
        self.assertEqual(settings["download_mode"], "parallel")


class DataDirTests(unittest.TestCase):
    def test_state_paths_are_absolute_under_one_root(self):
        root = Path(config.DATA_DIR)
        self.assertTrue(root.is_absolute())
        for path in (config.QUEUE_FILE, config.HISTORY_FILE,
                     config.SETTINGS_FILE, config.LOG_DIR):
            self.assertEqual(Path(path).parent, root)

    def test_migration_copies_once_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as source, \
                tempfile.TemporaryDirectory() as target:
            Path(source, "queue.json").write_text("[]", encoding="utf-8")
            Path(source, "settings.json").write_text(
                '{"theme": "light"}', encoding="utf-8")
            Path(target, "settings.json").write_text(
                '{"theme": "dark"}', encoding="utf-8")
            cwd = os.getcwd()
            os.chdir(source)
            try:
                self.assertEqual(config.migrate_legacy_files(target), ["queue.json"])
                self.assertEqual(config.migrate_legacy_files(target), [])
            finally:
                os.chdir(cwd)
            self.assertEqual(Path(target, "queue.json").read_text(encoding="utf-8"), "[]")
            self.assertEqual(Path(target, "settings.json").read_text(encoding="utf-8"),
                             '{"theme": "dark"}')


if __name__ == "__main__":
    unittest.main()
