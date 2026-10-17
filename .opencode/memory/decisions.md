# Decisions

- **Phase 8 before Phase 7**: Phase 7's pytest target (`queue_tab.py`) is deleted by the port, so durable items fold into Phase 8. Durable Phase 7 items now done: thread-safe JSON (`persistence.py`), `pyproject.toml` ruff config, tests.
- **Test runner = stdlib `unittest`** (not pytest): pytest is not installed in `yt-env`; unittest runs with plain python. Tests are pytest-compatible. `pyproject.toml` sets `pythonpath=["."]` for later pytest use.
- **Thumbnail key = filename** (`sha1(name)`), not URL — avoids a history→filename mapping and a history schema change. Populated via `downloader` `info_callback`.
- **`persistence` module passed as the QueueStore**: module-level `load_queue`/`save_queue` match the Protocol without an adapter class.
- **Tk modules deleted** in sub-step 8: `ui.py`, `queue_tab.py`, `videos_tab.py`, `music_tab.py`, `settings_tab.py`, `theme_manager.py`, `icon_manager.py`. `customtkinter` + `pillow` dropped from requirements.
- **`settings.json` is user data (gitignored)** — do not rewrite it during tests; point `persistence.QUEUE_FILE/HISTORY_FILE/SETTINGS_FILE` at a temp dir instead.

# Known issues / limitations
- Clipboard auto-detection: the setting exists and persists, but polling is **not yet wired** in the Qt UI (Tk did `xclip`/`xsel`/`powershell`). README no longer advertises auto-fill.
- Queue per-item *prioritize* (move up/down) was a Tk feature; not ported.
- `settings.json` theme value: restore to the user's value if any test toggles theme (toggles persist).
