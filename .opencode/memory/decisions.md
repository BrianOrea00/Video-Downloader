# Decisions

- **Phase 8 before Phase 7**: Phase 7's pytest target (`queue_tab.py`) is deleted by the port, so durable items fold into Phase 8. Durable Phase 7 items now done: thread-safe JSON (`persistence.py`), `pyproject.toml` ruff config, tests.
- **Test runner = stdlib `unittest`** (not pytest): pytest is not installed in `yt-env`; unittest runs with plain python. Tests are pytest-compatible. `pyproject.toml` sets `pythonpath=["."]` for later pytest use.
- **Thumbnail key = filename** (`sha1(name)`), not URL — avoids a history→filename mapping and a history schema change. Populated via `downloader` `info_callback`.
- **`persistence` module passed as the QueueStore**: module-level `load_queue`/`save_queue` match the Protocol without an adapter class.
- **Tk modules deleted** in sub-step 8: `ui.py`, `queue_tab.py`, `videos_tab.py`, `music_tab.py`, `settings_tab.py`, `theme_manager.py`, `icon_manager.py`. `customtkinter` + `pillow` dropped from requirements.
- **`settings.json` is user data (gitignored)** — do not rewrite it during tests; point `persistence.QUEUE_FILE/HISTORY_FILE/SETTINGS_FILE` at a temp dir instead.

- **UI scale = one token, default 1.5**: every size derives from `ui.theme.px()`; the QSS uses `@{n}` markers. `config.DEFAULT_SETTINGS["ui_scale"] = 1.5` (1.0 = original design size). Do not reintroduce raw pixel ints in widgets — a mixed layout breaks at scale.
- **Settings checkbox labels are short ("Enabled") with the full sentence in `setAccessibleName()`**: a long checkbox label is a hard minimum width and made the Settings page overflow horizontally at 2x.
- **Media empty state**: the grid cell holds only `empty_title`; `empty_hint` goes in the status line (full width, no wrapping/clipping). Grid/icon sizes scale via `METRICS`.

# Known issues / limitations
- At `ui_scale = 1.5` the app's minimum window is 1350x900; at `2.0` it is ~1728x972 (clamped to 90% of the screen). Below the effective minimum, pages overflow horizontally. Adjust `ui_scale` in `settings.json`.
- No Settings UI control for `ui_scale` yet; it is settings.json-only.
- `settings_page._desc()` helper text uses the `#FormHelp` selector (muted); longer control labels must be short or the form overflows.
- Clipboard auto-detection: the setting exists and persists, but polling is **not yet wired** in the Qt UI (Tk did `xclip`/`xsel`/`powershell`). README no longer advertises auto-fill.
- Queue per-item *prioritize* (move up/down) was a Tk feature; not ported.
- `settings.json` theme value: restore to the user's value if any test toggles theme (toggles persist).
