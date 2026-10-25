# Decisions

- **Phase 8 before Phase 7**: Phase 7's pytest target (`queue_tab.py`) is deleted by the port, so durable items fold into Phase 8. Durable Phase 7 items now done: thread-safe JSON (`persistence.py`), `pyproject.toml` ruff config, tests.
- **Test runner = stdlib `unittest`** (not pytest): pytest is not installed in `yt-env`; unittest runs with plain python. Tests are pytest-compatible. `pyproject.toml` sets `pythonpath=["."]` for later pytest use.
- **Thumbnail key = filename** (`sha1(name)`), not URL — avoids a history→filename mapping and a history schema change. Populated via `downloader` `info_callback`.
- **`persistence` module passed as the QueueStore**: module-level `load_queue`/`save_queue` match the Protocol without an adapter class.
- **Tk modules deleted** in sub-step 8: `ui.py`, `queue_tab.py`, `videos_tab.py`, `music_tab.py`, `settings_tab.py`, `theme_manager.py`, `icon_manager.py`. `customtkinter` + `pillow` dropped from requirements.
- **`settings.json` is user data (gitignored)** — do not rewrite it during tests; point `persistence.QUEUE_FILE/HISTORY_FILE/SETTINGS_FILE` at a temp dir instead.

- **Theme families × modes**: `THEMES[family][mode]`, families `arisu` (original pink, default), `saas` (blue on white), `arch` (Arch Linux `#1793d1`). Split across two settings keys to keep the existing `theme` key meaning intact: `theme_family` (new) and `theme` (`dark`/`light`). `MainWindow.set_theme(family, mode)` applies + persists + syncs the Settings combos and the top-bar button; `toggle_theme()` only flips the mode via `flip_mode()`. Picker lives in the Settings **APPEARANCE** card; it re-themes live. Light-mode accents are darkened so primary-button text stays legible (arch light = `#0e73a8`, not `#1793d1`). Every palette must define the identical 20 token keys — `tests/test_theme.py` enforces it.
- **UI scale = one token, default 1.5**: every size derives from `ui.theme.px()`; the QSS uses `@{n}` markers. `config.DEFAULT_SETTINGS["ui_scale"] = 1.5` (1.0 = original design size). Do not reintroduce raw pixel ints in widgets — a mixed layout breaks at scale.
- **Settings checkbox labels are short ("Enabled") with the full sentence in `setAccessibleName()`**: a long checkbox label is a hard minimum width and made the Settings page overflow horizontally at 2x.
- **Media empty state**: the grid cell holds only `empty_title`; `empty_hint` goes in the status line (full width, no wrapping/clipping). Grid/icon sizes scale via `METRICS`.

- **Sidebar collapse state persists** in `settings.json` as `sidebar_collapsed` (default `False`). `MainWindow` applies it with `set_collapsed(..., notify=False)` so restoring does not re-save. Collapsed = glyph-only nav, tooltip carries the label (the text is gone, so the tooltip is not redundant).

# Known issues / limitations
- At `ui_scale = 1.5` the app's minimum window is 1350x900; at `2.0` it is ~1728x972 (clamped to 90% of the screen). Below the effective minimum, pages overflow horizontally. Adjust `ui_scale` in `settings.json`.
- No Settings UI control for `ui_scale` yet; it is settings.json-only.
- `settings_page._desc()` helper text uses the `#FormHelp` selector (muted); longer control labels must be short or the form overflows.
- Clipboard auto-detection: the setting exists and persists, but polling is **not yet wired** in the Qt UI (Tk did `xclip`/`xsel`/`powershell`). README no longer advertises auto-fill.
- Queue per-item *prioritize* (move up/down) was a Tk feature; not ported.
- `settings.json` theme value: restore to the user's value if any test toggles theme (toggles persist; `set_theme` writes the file).
- QSS token resolution: a *query* helper (`tokens`, `stylesheet`, `color`) must read the active `_state`. Resolving against module defaults instead makes every family render the default palette — that exact bug shipped once and was only caught by comparing rendered PNGs.

- **Window minimums are device pixels, not design pixels** (`ui/main_window.py`). Scaling them forced 1350x900 at `ui_scale=1.5` and clipped queue rows on a 1366 laptop. Initial size clamps to the available screen, so a large scale no longer pushes the window off-screen.
- **Queue content is capped at 980 design px** (`ui/pages/queue_page.py`) and centred; labels that carry user text use `ElidedLabel` (middle elision + tooltip) because a plain `QLabel` sets its full text width as the layout minimum.
- **Inline validation is text, not colour** — `QueuePage._set_validity` writes a message under the URL field and mirrors it into `accessibleDescription`.

- **One per-user data dir** (`config.DATA_DIR`): Linux `$XDG_DATA_HOME/video-downloader`, macOS `~/Library/Application Support/Video-Downloader`, Windows `%APPDATA%\Video-Downloader`. All state (`queue.json`, `history.json`, `settings.json`), `logs/` and `app.lock` resolve from it at import time — tests still override the module constants, but nothing is written to the repo anymore. `VIDEO_DOWNLOADER_DATA_DIR` overrides it. `config.migrate_legacy_files()` copies legacy cwd JSON once and never overwrites.
- **Single instance** = `QLockFile(DATA_DIR/app.lock)` in `main.py`; a second launch shows a message and returns 0. Do not pass `setStaleLockTime(0)` — Qt's default PID check is what clears locks left by a crashed process.

- **ffmpeg is a hard dependency for two paths**: audio-only (`FFmpegExtractAudio`) and MP4 merge. `utils.ffmpeg_available()` gates the Audio Only pill and the Settings checkbox, and `add_to_queue` refuses the combination with an explanation. A saved `default_audio_only` must never re-enable a disabled pill — it is ANDed with the probe.
- **`sys.excepthook` is installed in `main()`** after `QApplication` exists: logs `CRITICAL` with the traceback, then shows a `QMessageBox`. A windowed/frozen build has no visible stderr.
