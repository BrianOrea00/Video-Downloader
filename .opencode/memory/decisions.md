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
- **Queue content is fluid**, not capped; `ElidedLabel` (middle elision + tooltip) keeps long user text from setting a huge layout minimum. Labels that carry user text must elide rather than wrap.
- **Inline validation is text, not colour** — `QueuePage._set_validity` writes a message under the URL field and mirrors it into `accessibleDescription`.

- **One per-user data dir** (`config.DATA_DIR`): Linux `$XDG_DATA_HOME/video-downloader`, macOS `~/Library/Application Support/Video-Downloader`, Windows `%APPDATA%\Video-Downloader`. All state (`queue.json`, `history.json`, `settings.json`), `logs/` and `app.lock` resolve from it at import time — tests still override the module constants, but nothing is written to the repo anymore. `VIDEO_DOWNLOADER_DATA_DIR` overrides it. `config.migrate_legacy_files()` copies legacy cwd JSON once and never overwrites.
- **Single instance** = `QLockFile(DATA_DIR/app.lock)` in `main.py`; a second launch shows a message and returns 0. Do not pass `setStaleLockTime(0)` — Qt's default PID check is what clears locks left by a crashed process.

- **ffmpeg is a hard dependency for two paths**: audio-only (`FFmpegExtractAudio`) and MP4 merge. `utils.ffmpeg_available()` gates the Audio Only pill and the Settings checkbox, and `add_to_queue` refuses the combination with an explanation. A saved `default_audio_only` must never re-enable a disabled pill — it is ANDed with the probe.
- **`sys.excepthook` is installed in `main()`** after `QApplication` exists: logs `CRITICAL` with the traceback, then shows a `QMessageBox`. A windowed/frozen build has no visible stderr.

- **Queue feedback is a banner, not a dialog**: `QueuePage._notify(text, level)` writes to `self.banner` under the input card, auto-hides after 8 s, and is dismissible. `QMessageBox` stays only for decisions (duplicate URL / previously downloaded). Do not add routine `information()`/`warning()` calls back.
- **`DownloadItem.message` / `.filename`** are persisted optional keys: `message` is the failure reason rendered on the row, `filename` is the yt-dlp final name used by Play. `_set_status(PENDING)` clears `message`; retry reuses the pause/resume path.
- **Queue rows say "Remove"** with a tooltip that the file is kept; the trash icon belongs to the media library only.

- **One icon source** = `ui/icons.py` (`pixmap`/`icon`). The PNGs in `assets/` are solid black, so they are re-tinted with a theme token and cached per `(name, pixels, hex)`; callers pass a token name, never a raw colour. No text glyphs as affordances. Theme switches must re-tint: `MainWindow.set_theme` calls `sidebar.refresh_icons()`; checked nav rows use `bg_dark`, unchecked `text`.
- **Preview size estimate** (`queue_page.RESOLUTION_KBPS`) is a deliberate rough table (kbps per resolution + 128 kbps audio); audio-only uses `AUDIO_KBPS = 192`. It is labelled as an estimate (`~`), never presented as exact.
- **Empty sections hide their heading**; `QueuePage._empty_state()` is the only empty block (icon + one line + "Add a link").

- **Source of truth for icon art is Tabler Icons outline** (`https://tabler.io/icons`, SVG from `tabler/tabler-icons`). `assets/*.png` are those SVGs rendered 240x240, solid black on transparent; `ui/icons.py` does the tinting. Add a new icon by rendering its outline SVG the same way, never by shipping a coloured bitmap.

- **Settings has no Save button**: every control autosaves through `SettingsPage._touch()` (400 ms debounce, "Saving…" → "Saved"), then emits `settings_changed` so the queue page re-reads defaults. Theme is the exception: it persists via `MainWindow.set_theme` because the QSS must re-apply live; the status line still confirms.
- **Dead controls are gone, not stubbed**: the clipboard poller and its interval were removed from Settings until a poller exists; the keys stay in settings.json. `ui_scale` is now a 100/125/150 % selector applied on the next start (`main.py` reads it before the window).
- **Storage meter is live**: `MainWindow._update_storage()` calls `shutil.disk_usage(download_path)` on page change and after a finished download (via `_refresh_current`); it is never polled. The sidebar bar shows the used fraction, the label the free space, and both carry the folder as a tooltip.

- **Library pages have one owner for order and status** (`ui/pages/media_page.py`): `_sorted_entries()` applies the header sort combo (Newest/Oldest/Largest/Name, persisted as `library_sort`), `_render()` alone writes the status line ("3 videos · 5.7 MB", no match, empty folder) and switches a `QStackedWidget` between the list and the real empty panel. Play/Reveal/Delete are header buttons gated by the selection; the context menu is the shortcut, not the only path.

- **Queue refresh is keyed, never clear-and-rebuild**: `QueuePage._rows` maps `id(DownloadItem)` → `QueueRow`; `QueueRow.update_item()` repaints labels/tile/reason/actions in place and `refresh()` only destroys rows whose item disappeared, then re-adds survivors in the new order. Row progress survives a refresh; focus and scroll position are not thrown away on every status change.

- **Motion is state only, and optional**: progress values animate 150 ms linear; new queue rows fade in 120 ms (`ui/theme.py:set_motion`). No page transitions or hover effects. `reduce_motion` is a Settings toggle and is read at startup (`main.py`) and on save (`MainWindow._on_settings_changed`); when off, values set instantly and no opacity effect is installed.

- **Queue rows are selectable and Delete is destructive-by-confirmation** (`ui/pages/queue_page.py`): clicking a `QueueRow` emits `pressed`, `QueuePage._set_selected()` keeps one selection and `QueueRow._apply_state()` merges selection and active state into the single `objectName` (`Row` / `RowActive` / `RowSelected`). `Delete` removes the selected item through `_confirm_remove()` (the one modal that is still warranted), refuses while the item is downloading, and `Esc` clears the selection before it clears the URL field. The page also sets an explicit `QWidget.setTabOrder` chain so keyboard focus follows the visual order.

- **`utils.py` holds only live helpers** (`resource_path`, `ffmpeg_available`, `detect_vlc`); the legacy JSON read/write wrappers and `clean_filename` were deleted because `persistence.py` owns that (atomic writes, corrupt-file recovery) and nothing called them. That also removed the last bare `except` clauses, so `ruff check .` is clean.

- **App identity assets**: `assets/appicon.png` (512, Tabler download glyph on the arisu gradient) and `assets/appicon.ico` (16-256, for the Windows build) are set through `app.setWindowIcon` together with `setDesktopFileName("video-downloader")`, so the dock icon matches a future `.desktop` entry instead of a generic Python icon.

- **Dependency set is extras-complete** (`requirements.txt`): `yt-dlp[default,secretstorage]==2026.8.19` (the extras supply certifi, requests, brotli, websockets, pycryptodomex, yt-dlp-ejs and the Linux cookie backend) and `PySide6-Essentials`, because only Core/Gui/Widgets are imported and the Addons wheel adds ~400 MB of unused WebEngine. The dev venv still has full PySide6 installed; the requirements file is the source of truth for a clean install.

- **Licence is GPL-3.0-or-later by necessity** (user decision): `mutagen` is GPL-2.0-or-later, so no permissive licence is possible while bundling it. `LICENSE` holds the verbatim GPLv3 text, `THIRD_PARTY_NOTICES.md` lists every component (Qt/PySide6, yt-dlp, mutagen, Tabler MIT text inline, Monocraft OFL, Pillow build-only, FFmpeg-not-bundled) and the source link; Settings → About shows the licence and the repository. A binary release must also offer the corresponding source.

- **CI is lint + tests on 3.11-3.13** (`.github/workflows/ci.yml`): ruff 0.17.2 from `requirements-dev.txt`, then `unittest` with `QT_QPA_PLATFORM=offscreen` on a runner that installs `libegl1`, `libglib2.0-0`, `libxkbcommon-x11-0`, `libdbus-1-3`. `tests/test_gui_smoke.py` builds the real `MainWindow` with persistence paths redirected to a temp dir, switches theme, waits for the Settings autosave, checks the badge and a library scan, so a missing Qt plugin or a broken page fails CI instead of a user's launch.
