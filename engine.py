# engine.py
"""Runtime updates for the bundled ``yt-dlp``.

``yt-dlp``'s own updater refuses to run inside a frozen build, and the video
sites change faster than application releases, so the download engine has to be
refreshable on its own.

Design, in the order it happens:

1. A newer ``yt-dlp`` wheel is downloaded from PyPI together with the SHA256
   digest published in the *same* JSON response.
2. The bytes are hashed and unpacked only if the digest matches, into
   ``<data>/engine/<version>/``.
3. ``current.json`` is rewritten atomically, so an interrupted write falls back
   to the previous version instead of a half-written file.
4. ``main.py`` calls :func:`activate` *before* anything imports ``yt_dlp``,
   which prepends the recorded directory to ``sys.path``.

If the import of the recorded version fails, the module is purged from
``sys.modules`` and the bundled copy is used, so a bad engine can never make the
app unstartable.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

from config import DATA_DIR

logger = logging.getLogger(__name__)

ENGINE_DIR = Path(DATA_DIR) / "engine"
CURRENT_FILE = ENGINE_DIR / "current.json"
PYPI_JSON = "https://pypi.org/pypi/yt-dlp/json"
PACKAGE = "yt_dlp"
WHEEL_SUFFIX = "py3-none-any.whl"
FETCH_TIMEOUT = 30


class EngineError(RuntimeError):
    """Raised when an engine update cannot be completed safely."""


def version_key(version: str) -> tuple[int, ...]:
    """Numeric comparison key for a yt-dlp version like ``2026.8.19``."""
    return tuple(int(part) for part in re.findall(r"\d+", version))


def active_version() -> str | None:
    """The version recorded in ``current.json``, if it is still on disk."""
    try:
        data = json.loads(CURRENT_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    version = str(data.get("version") or "")
    if version and (ENGINE_DIR / version / PACKAGE).is_dir():
        return version
    return None


def activate() -> str | None:
    """Put the installed engine ahead of the bundled one; return its version.

    Must be called before the first ``import yt_dlp``. Returns ``None`` when no
    update is installed or when the updated copy cannot be imported, in which
    case the bundled engine is used.
    """
    version = active_version()
    if not version:
        return None
    if PACKAGE in sys.modules:
        # Already imported: swapping the module now would leave the old
        # objects in place, so honour the copy that is in use.
        logger.warning("activate() ran after yt_dlp was imported; keeping that copy")
        return None
    path = str(ENGINE_DIR / version)
    if path in sys.path:
        return version
    sys.path.insert(0, path)
    try:
        import yt_dlp  # noqa: F401  (import is the verification)
    except Exception:  # noqa: BLE001 - any failure means fall back
        logger.exception("Updated engine %s failed to import; using bundled copy", version)
        sys.path.remove(path)
        for name in [n for n in sys.modules if n == PACKAGE or n.startswith(PACKAGE + ".")]:
            sys.modules.pop(name, None)
        return None
    logger.info("Using updated engine %s from %s", version, path)
    return version


def _wheel_entry(payload: dict, version: str) -> dict:
    """The ``py3-none-any`` wheel record for ``version`` from PyPI metadata."""
    files = payload.get("urls")
    if not files:
        files = (payload.get("releases") or {}).get(version, [])
    for entry in files:
        name = str(entry.get("filename") or "")
        if entry.get("packagetype") == "bdist_wheel" and name.endswith(WHEEL_SUFFIX):
            return entry
    raise EngineError(f"PyPI has no {WHEEL_SUFFIX} for yt-dlp {version}")


def latest_metadata(timeout: int = FETCH_TIMEOUT, opener=None) -> tuple[str, str, str]:
    """Return ``(version, sha256, url)`` for the newest wheel, without downloading it."""
    fetch = opener or urllib.request.urlopen
    with fetch(PYPI_JSON, timeout=timeout) as response:
        payload = json.load(response)
    version = str((payload.get("info") or {}).get("version") or "")
    if not version:
        raise EngineError("PyPI metadata did not include a version")
    entry = _wheel_entry(payload, version)
    digest = str((entry.get("digests") or {}).get("sha256") or "")
    url = str(entry.get("url") or "")
    if not digest or not url:
        raise EngineError(f"PyPI did not publish a sha256 for yt-dlp {version}")
    return version, digest.lower(), url


def download(url: str, timeout: int = FETCH_TIMEOUT, opener=None) -> bytes:
    fetch = opener or urllib.request.urlopen
    with fetch(url, timeout=timeout) as response:
        return response.read()


def _check_archive(archive: zipfile.ZipFile) -> None:
    """Refuse an archive that would write outside the target directory."""
    for member in archive.namelist():
        name = member.replace("\\", "/")
        if name.startswith("/") or ".." in Path(name).parts:
            raise EngineError(f"Unsafe path in wheel: {member}")
    if not any(name.startswith(PACKAGE + "/") for name in archive.namelist()):
        raise EngineError("Wheel does not contain the yt_dlp package")


def install(version: str, wheel: bytes, expected_sha256: str) -> str:
    """Verify, unpack and record a wheel; return the version now installed.

    Nothing is switched over until the archive is fully unpacked and checked,
    so a failed download or a full disk leaves the previous engine in place.
    """
    actual = hashlib.sha256(wheel).hexdigest()
    if actual != expected_sha256.lower():
        raise EngineError("Downloaded wheel does not match the PyPI sha256")
    target = ENGINE_DIR / version
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=ENGINE_DIR))
    try:
        with zipfile.ZipFile(io.BytesIO(wheel)) as archive:
            _check_archive(archive)
            archive.extractall(staging)
        if target.exists():
            shutil.rmtree(target)
        os.replace(staging, target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    _write_current({"version": version, "installed": datetime.now().isoformat(timespec="seconds")})
    _prune(keep=version)
    return version


def _write_current(payload: dict) -> None:
    """Atomically rewrite ``current.json`` so a crash cannot truncate it."""
    tmp = CURRENT_FILE.with_name(CURRENT_FILE.name + ".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(tmp, CURRENT_FILE)


def _prune(keep: str) -> None:
    """Delete older installed engines; only one is ever used."""
    for child in ENGINE_DIR.iterdir():
        if child.is_dir() and child.name != keep and not child.name.startswith("."):
            shutil.rmtree(child, ignore_errors=True)


def update(timeout: int = FETCH_TIMEOUT, opener=None) -> str | None:
    """Download and install the newest wheel; return the new version.

    Returns ``None`` when the installed engine is already the newest one, so a
    repeated check is cheap and silent.
    """
    version, digest, url = latest_metadata(timeout=timeout, opener=opener)
    current = active_version()
    if current and version_key(current) >= version_key(version):
        return None
    wheel = download(url, timeout=timeout, opener=opener)
    return install(version, wheel, digest)


if __name__ == "__main__":  # pragma: no cover - support entry point
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if "--installed" in sys.argv:
        print(active_version() or "bundled")
    else:
        print(update() or "up to date")
