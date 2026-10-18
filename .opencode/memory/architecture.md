# Architecture

## Overview
Video-Downloader: desktop `yt-dlp` downloader. UI is **PySide6 (Qt)** as of the Phase 8 port. Single-purpose personal app.

## Entry point
- `main.py` — `QApplication`, `persistence.load_settings()`, `ui.theme.apply_theme()`, `ui.main_window.MainWindow`, `app.exec()`.

## Core (GUI-free, unit-tested)
- `models.py` — `DownloadItem` dataclass, `DownloadStatus` str-enum. **Values are the exact legacy `queue.json` strings** (`pending`/`downloading`/`paused`/`completed`/`failed`). Do not change.
- `queue_manager.py` — `QueueManager` state machine. Store is injected (Protocol `QueueStore` = `load_queue`/`save_queue`). `persistence` module is passed as the store. Thread-safe via `RLock`. `load()` rehabilitates `downloading`→`pending`.
- `persistence.py` — thread-safe atomic JSON. One module `RLock`, temp-file + `os.fsync` + `os.replace`. Corrupt/missing → default. `load_settings()` merges `DEFAULT_SETTINGS`. Replaces the old unguarded `utils.py` writers.
- `thumb_cache.py` — thumbnails at `<download_path>/.thumbs/<sha1(filename)>.jpg`, keyed by **filename** (not URL). `fetch()` is network + must run off the GUI thread.

## Engine (survives port)
- `downloader.py` — `Downloader`. `download()` uses `ydl.extract_info(url, download=True)` and accepts optional `info_callback(info)`; `done_callback(str)` still drives Tk-era callers.
- `url_validator.py`, `config.py` (`DEFAULT_SETTINGS`, `RESOLUTIONS`), `utils.py` (`detect_vlc`), `logger.py` (`logging`, file at `logs/app.log`).

## Qt UI
- `ui/theme.py` — semantic colour tokens (`TOKENS`) for dark/light + QSS template. **Single source of visual truth.** `color(key)`/`current_theme()` read the applied theme. arisu-pink accent `#ff79c6`. Font Monocraft, fallback monospace.
  - **UI scale**: `set_ui_scale()` / `px()` / `METRICS` / `font_size()` / `font_pt()`. Default `DEFAULT_UI_SCALE = 1.5`, override via the `ui_scale` settings key (applied in `main.py`). QSS numbers are written as `@{n}` design-time pixels and expanded by `px()` in `stylesheet()`; hairline borders stay 1px. `px(0)` returns 0.
- `ui/sidebar.py` — nav rail, `navigate(str)` signal, storage meter. `collapsed_changed(bool)` + `set_collapsed(bool, notify=)` toggle an icon-only rail (burger button `BurgerButton`); width comes from `METRICS["sidebar_width"|"sidebar_collapsed_width"]`. Collapsed hides the logo text, section labels and the storage readout, keeps the glyph, and moves the label into the tooltip.
- `ui/main_window.py` — shell: sidebar + top bar + `QStackedWidget`. Owns `QueueManager(store=persistence, history_loader=persistence.load_history)`. Theme toggle persists to settings and refreshes the current page.
- `ui/pages/queue_page.py` — Download Console. `InfoWorker(QThread)` for preview, `ThumbWorker(QThread)` for thumbnails, `QueueRunner` for downloads.
- `ui/pages/media_page.py` — `MediaBrowser` base + `ScanWorker(QThread)`; Videos = icon grid, Music = list (mutagen tags read off-thread).
- `ui/pages/settings_page.py` — form; `settings_changed` signal; cookies + `CookieTestWorker`.

## Threading contract
- `queue_runner.QueueRunner` (QObject) signals: `progress(item, dict)`, `item_finished(item, str)`, `item_info(item, dict)`, `run_finished()`. Emitted from worker threads → Qt auto-queues to GUI thread.
- Stop token: `QueueRunner.stop()` sets the event and cancels every active `Downloader`; no new download starts afterward.

## Conventions
- All repeated glyphs/colors go through tokens; never hardcode hex in widgets (use `ui_theme.color`).
- **Never hardcode pixel sizes in widget code** — use `px()` (layout) or `px(METRICS[...])` (named sizes: sidebar, topbar, tiles, thumbs, grid, label column). A bare int is a bug at any scale ≠ 1.0.
- A long `QCheckBox` label or an unwrapped `QLabel` sets a hard *minimum* width; it steals the layout and forces horizontal overflow once the font scales. Keep control text short and put the sentence in `setAccessibleName()`.
- Qt re-evaluates a QSS property selector (`[collapsed="true"]`) only after `ui.theme.repolish(widget)`; a bare `setProperty` changes nothing visually.
- Word-wrapped text in `QFormLayout` needs the wrapper's size policy to advertise `setHeightForWidth(True)`, otherwise the row height comes from the field widget and lines overlap.
- New pages: subclass `MediaBrowser` for list/grid, else `QWidget` with `showEvent` → refresh.
- Deleting dynamic child widgets: `setParent(None)` then `deleteLater()` (immediate reflow; prevents ghost rows).
