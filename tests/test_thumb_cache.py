# tests/test_thumb_cache.py
"""Unit tests for the thumbnail cache keying and storage."""
import tempfile
import unittest
from pathlib import Path

import thumb_cache


class ThumbCacheTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_store_then_local_path(self):
        path = thumb_cache.store(self.root, "clip.mp4", b"jpeg-bytes")
        self.assertIsNotNone(path)
        self.assertEqual(thumb_cache.local_path(self.root, "clip.mp4"), path)
        self.assertTrue(Path(path).exists())

    def test_local_path_missing_returns_none(self):
        self.assertIsNone(thumb_cache.local_path(self.root, "absent.mp4"))

    def test_key_is_deterministic_and_per_name(self):
        a = thumb_cache.thumb_path(self.root, "a.mp4")
        b = thumb_cache.thumb_path(self.root, "b.mp4")
        self.assertNotEqual(a, b)
        self.assertEqual(a, thumb_cache.thumb_path(self.root, "a.mp4"))

    def test_final_filename_from_requested_downloads(self):
        info = {"requested_downloads": [{"filepath": "/d/My Video.mp4"}]}
        self.assertEqual(thumb_cache.final_filename(info), "My Video.mp4")

    def test_final_filename_absent(self):
        self.assertIsNone(thumb_cache.final_filename({}))


if __name__ == "__main__":
    unittest.main()
