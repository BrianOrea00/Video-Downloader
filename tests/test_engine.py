# tests/test_engine.py
"""Unit tests for the runtime yt-dlp update path (no network access)."""
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import engine


class FakeResponse(io.BytesIO):
    """Minimal stand-in for the object urlopen returns."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def make_wheel(version: str = "2026.9.1", extra: dict | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("yt_dlp/__init__.py", f'__version__ = "{version}"\n')
        archive.writestr(f"yt_dlp-{version}.dist-info/METADATA",
                         "Metadata-Version: 2.1\nName: yt-dlp\n")
        for name, body in (extra or {}).items():
            archive.writestr(name, body)
    return buffer.getvalue()


class EngineTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self._orig = (engine.ENGINE_DIR, engine.CURRENT_FILE)
        engine.ENGINE_DIR = root / "engine"
        engine.CURRENT_FILE = engine.ENGINE_DIR / "current.json"

    def tearDown(self):
        engine.ENGINE_DIR, engine.CURRENT_FILE = self._orig
        self._tmp.cleanup()


class VersionKeyTests(unittest.TestCase):
    def test_numeric_parts_order_versions_not_strings(self):
        self.assertGreater(engine.version_key("2026.10.1"), engine.version_key("2026.9.30"))
        self.assertEqual(engine.version_key("2026.8.19"), (2026, 8, 19))


class MetadataTests(EngineTestBase):
    def test_latest_metadata_reads_the_wheel_digest(self):
        payload = {
            "info": {"version": "2026.9.1"},
            "urls": [
                {"packagetype": "sdist", "filename": "yt_dlp-2026.9.1.tar.gz"},
                {"packagetype": "bdist_wheel",
                 "filename": "yt_dlp-2026.9.1-py3-none-any.whl",
                 "url": "https://files.example/yt_dlp-2026.9.1-py3-none-any.whl",
                 "digests": {"sha256": "ABC123"}},
            ],
        }
        called = {}

        def opener(url, timeout=0):
            called["url"] = url
            return FakeResponse(json.dumps(payload).encode())

        version, digest, url = engine.latest_metadata(opener=opener)
        self.assertEqual(version, "2026.9.1")
        self.assertEqual(digest, "abc123")          # normalised to lowercase
        self.assertTrue(url.endswith(".whl"))
        self.assertEqual(called["url"], engine.PYPI_JSON)

    def test_latest_metadata_refuses_metadata_without_digest(self):
        payload = {"info": {"version": "2026.9.1"},
                   "urls": [{"packagetype": "bdist_wheel",
                             "filename": "yt_dlp-2026.9.1-py3-none-any.whl",
                             "url": "https://files.example/x.whl"}]}
        with self.assertRaises(engine.EngineError):
            engine.latest_metadata(opener=lambda url, timeout=0: FakeResponse(json.dumps(payload).encode()))


class InstallTests(EngineTestBase):
    def test_install_unpacks_verifies_and_records(self):
        wheel = make_wheel("2026.9.1")
        digest = hashlib.sha256(wheel).hexdigest()
        self.assertEqual(engine.install("2026.9.1", wheel, digest), "2026.9.1")
        self.assertTrue((engine.ENGINE_DIR / "2026.9.1" / "yt_dlp" / "__init__.py").is_file())
        self.assertEqual(engine.active_version(), "2026.9.1")
        self.assertIn("2026.9.1", engine.CURRENT_FILE.read_text(encoding="utf-8"))

    def test_digest_mismatch_leaves_the_previous_engine_in_place(self):
        good = make_wheel("2026.9.1")
        engine.install("2026.9.1", good, hashlib.sha256(good).hexdigest())
        bad = make_wheel("2026.10.1")
        with self.assertRaises(engine.EngineError):
            engine.install("2026.10.1", bad, "0" * 64)
        self.assertEqual(engine.active_version(), "2026.9.1")
        self.assertFalse((engine.ENGINE_DIR / "2026.10.1").exists())

    def test_install_prunes_older_versions(self):
        first = make_wheel("2026.9.1")
        engine.install("2026.9.1", first, hashlib.sha256(first).hexdigest())
        second = make_wheel("2026.10.1")
        engine.install("2026.10.1", second, hashlib.sha256(second).hexdigest())
        self.assertEqual(engine.active_version(), "2026.10.1")
        self.assertFalse((engine.ENGINE_DIR / "2026.9.1").exists())

    def test_archive_without_the_package_is_refused(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("not_yt_dlp/__init__.py", "")
        wheel = buffer.getvalue()
        with self.assertRaises(engine.EngineError):
            engine.install("2026.9.1", wheel, hashlib.sha256(wheel).hexdigest())
        self.assertIsNone(engine.active_version())

    def test_archive_with_a_traversal_path_is_refused(self):
        wheel = make_wheel("2026.9.1", {"../escaped.py": "print('x')\n"})
        with self.assertRaises(engine.EngineError):
            engine.install("2026.9.1", wheel, hashlib.sha256(wheel).hexdigest())
        self.assertFalse((engine.ENGINE_DIR.parent / "escaped.py").exists())

    def test_update_is_a_no_op_when_installed_engine_is_newest(self):
        wheel = make_wheel("2026.9.1")
        engine.install("2026.9.1", wheel, hashlib.sha256(wheel).hexdigest())
        payload = {"info": {"version": "2026.9.1"},
                   "urls": [{"packagetype": "bdist_wheel",
                             "filename": "yt_dlp-2026.9.1-py3-none-any.whl",
                             "url": "https://files.example/x.whl",
                             "digests": {"sha256": hashlib.sha256(wheel).hexdigest()}}]}

        def opener(url, timeout=0):
            if url == engine.PYPI_JSON:
                return FakeResponse(json.dumps(payload).encode())
            raise AssertionError("the wheel should not be downloaded again")

        self.assertIsNone(engine.update(opener=opener))


class ActivateTests(EngineTestBase):
    def _forget_imported_package(self):
        import sys
        for name in [n for n in sys.modules if n == "yt_dlp" or n.startswith("yt_dlp.")]:
            del sys.modules[name]

    def test_broken_engine_falls_back_to_the_bundled_copy(self):
        self._forget_imported_package()
        (engine.ENGINE_DIR / "2026.9.1" / "yt_dlp").mkdir(parents=True)
        (engine.ENGINE_DIR / "2026.9.1" / "yt_dlp" / "__init__.py").write_text(
            "raise RuntimeError('broken engine')\n", encoding="utf-8")
        (engine.ENGINE_DIR / "current.json").write_text(
            json.dumps({"version": "2026.9.1"}), encoding="utf-8")
        self.assertIsNone(engine.activate())
        self.assertNotIn(str(engine.ENGINE_DIR / "2026.9.1"), __import__("sys").path)

    def test_already_imported_package_is_not_replaced(self):
        import sys
        (engine.ENGINE_DIR / "2026.9.1" / "yt_dlp").mkdir(parents=True)
        (engine.ENGINE_DIR / "current.json").write_text(
            json.dumps({"version": "2026.9.1"}), encoding="utf-8")
        previous = sys.modules.get("yt_dlp")
        sys.modules["yt_dlp"] = object()   # pretend something imported it already
        try:
            self.assertIsNone(engine.activate())
        finally:
            if previous is None:
                del sys.modules["yt_dlp"]
            else:
                sys.modules["yt_dlp"] = previous

    def test_missing_current_file_means_bundled_copy(self):
        self.assertIsNone(engine.active_version())
        self.assertIsNone(engine.activate())


if __name__ == "__main__":
    unittest.main()
