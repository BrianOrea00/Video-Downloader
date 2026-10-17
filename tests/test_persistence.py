# tests/test_persistence.py
"""Unit tests for thread-safe, atomic JSON persistence."""
import json
import tempfile
import threading
import unittest
from pathlib import Path

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

    def test_defaults_written_when_file_absent(self):
        settings = persistence.load_settings()
        self.assertTrue(Path(self.settings_file).exists())
        self.assertEqual(settings["download_mode"], "parallel")


if __name__ == "__main__":
    unittest.main()
