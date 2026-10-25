# persistence.py
"""Thread-safe JSON persistence for queue, history and settings.

All writes funnel through one re-entrant lock and an atomic temp-file replace,
so a crash or a concurrent writer cannot leave a half-written file behind. This
replaces the unguarded ``json.dump`` calls in the legacy ``utils.py``.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from datetime import datetime
from typing import Any

from config import DEFAULT_SETTINGS, HISTORY_FILE, QUEUE_FILE, SETTINGS_FILE

logger = logging.getLogger(__name__)

_write_lock = threading.RLock()


def _read(path: str, default: Any) -> Any:
    """Read JSON, returning ``default`` for a missing, empty or corrupt file."""
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return default
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to read %s: %s", path, exc)
        return default


def _write(path: str, data: Any) -> None:
    """Atomically serialise ``data`` to ``path`` under the module write lock."""
    with _write_lock:
        directory = os.path.dirname(os.path.abspath(path)) or "."
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=4)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise


def load_queue() -> list[dict]:
    data = _read(QUEUE_FILE, [])
    return data if isinstance(data, list) else []


def save_queue(queue: list[dict]) -> None:
    _write(QUEUE_FILE, queue)


def load_history() -> list[dict]:
    data = _read(HISTORY_FILE, [])
    return data if isinstance(data, list) else []


def save_history(entry: dict) -> None:
    """Append one completed-download record, stamping a date if absent."""
    record = dict(entry)
    record.setdefault("date_added", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    with _write_lock:
        history = load_history()
        history.append(record)
        _write(HISTORY_FILE, history)


def load_settings() -> dict:
    """Load settings merged over defaults, so new keys are always present."""
    data = _read(SETTINGS_FILE, None)
    if not isinstance(data, dict):
        merged = dict(DEFAULT_SETTINGS)
        save_settings(merged)
        return merged
    merged = dict(DEFAULT_SETTINGS)
    merged.update(data)
    if not merged.get("download_path"):
        merged["download_path"] = DEFAULT_SETTINGS["download_path"]
    return merged


def save_settings(settings: dict) -> None:
    _write(SETTINGS_FILE, settings)
