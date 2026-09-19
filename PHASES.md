# Video Downloader — Improvement Plan

Audit of the full codebase (branch `InProgress`, Sep 2026). This document lists every
problem found, grouped by severity, and the phased plan to fix them.

App: CustomTkinter desktop downloader wrapping `yt-dlp`. Modules: `main.py`, `ui.py`,
`queue_tab.py`, `videos_tab.py`, `music_tab.py`, `settings_tab.py`, `downloader.py`,
`theme_manager.py`, `icon_manager.py`, `url_validator.py`, `utils.py`, `config.py`,
`logger.py`.

---

## 1. Critical Bugs

### 1.1 Stop Queue does not actually stop downloads

`queue_tab.py:836` `process_queue` submits every pending item to a `ThreadPoolExecutor`
up front. `stop_queue` (`queue_tab.py:823`) only cancels the `Downloader` objects that
have started already. Futures that have not started yet later spawn a fresh `Downloader`,
and `Downloader.download` resets `cancelled = False` (`downloader.py:126`), so those
downloads proceed anyway. The `self.downloading` flag only breaks the wait loop in
`download_item_thread`; it does not stop the spawned daemon thread.

**Fix:** reject new futures after stop; cancel every downloader; carry a "stop requested"
token into `download` so a fresh `Downloader` does not start.

### 1.2 Cancel/stop leaves zombie queue items

When stopped, items stay marked `"downloading"` forever. `start_queue` only collects
`pending`/`paused` items (`queue_tab.py:804`), so the item can never run again and there
is no way to reset it. The per-downloader cancel path (`downloader.py:240-242`) routes
through `done_callback("Download cancelled by user")`, and `_handle_done`
(`queue_tab.py:937`) marks the item `"failed"` instead of restoring it to a restartable
state.

**Fix:** on stop, mark running items `"paused"` (or `"pending"`); on user cancel, restore
instead of failing.

### 1.3 Sequential download mode is ignored

`SettingsTab` saves `download_mode` (`settings_tab.py:682`), but `process_queue`
(`queue_tab.py:836`) reads only `parallel_limit`. The app is always parallel regardless
of the setting. The setting is pure dead UI.

**Fix:** when mode is `sequential`, run with pool size 1.

### 1.4 Light theme is broken — `muted`/`greige`/`secondary` missing

`theme_manager.py:19` `COLORS["light"]` lacks the keys `muted`, `greige`, and
`secondary`, which are referenced 60+ times across the UI. `ThemeManager.get_color`
falls back to `#000000` (`theme_manager.py:40`) for missing keys, so light mode renders
black text on light backgrounds. Several fills are also hardcoded and never follow the
theme: `#1B4A3A` sidebar hover (`ui.py:288,331`), `#0A2822` active pills
(`queue_tab.py:423,439`).

**Fix:** complete the light palette, make `get_color` strict (raise on unknown key so
misses surface), and replace hardcoded colors with palette lookups.

### 1.5 Resume / partial-file feature is dead code

`downloader.py:129-131` fetches a partial file, logs "Resuming download from: ...", then
never uses the value. `_find_partial_file` also has a logic bug: the directory scan sets
`self._partial_file` but returns `None`. `_save_partial_tracking` stores whatever the
progress hook last reported as `filename` (the final output template), not the actual
`.part` file, so the persisted tracking is wrong. Resume relies only on yt-dlp's
`continuedl` flag.

**Fix:** decide the intended resume semantics, wire the real partial path to yt-dlp's
`continue_dl`, or remove the dead tracking code.

### 1.6 UI thread blocked on network I/O

`add_to_queue` (`queue_tab.py:532`) calls `downloader.get_info(url)` synchronously on the
UI thread for every add, even though a duplicate check already ran. `ui.py:99`
clipboard auto-detection calls `queue_tab.preview()`, which also runs `get_info` on the
UI thread. Any slow extractor freezes the whole window for seconds.

**Fix:** move `get_info` for add/preview into a worker thread; show pending/spinner state.

### 1.7 Cookie test reports success on failure

`get_info` sets `ignoreerrors: True` (`downloader.py:40`), so a failed extraction returns
`None` instead of raising. `settings_tab.py:621` treats any returned value as success and
calls `info.get('title', ...)` on `None`, crashing or faking "Cookie test passed".

**Fix:** treat `None` result as failure with a clear message.

---

## 2. Notable Gaps

### 2.1 No real progress UI

The download hook (`downloader.py:146-199`) computes `_percent`, `_speed_str`,
`_eta_str`, `_downloaded_bytes_str` for every tick, but `_handle_progress`
(`queue_tab.py:919`) discards it all. The active card shows a faked "50%" and a pulsing
bar (`queue_tab.py:966-968`). There are no per-row progress bars.

**Fix (later):** wire hook data into per-row progress bars and a truthful aggregate.

### 2.2 Resolution pills hardcoded to 720/1080

`queue_tab.py:175` builds pills from `["720", "1080"]` while `config.RESOLUTIONS` lists
144-1080 and the settings default can be e.g. `"480"`. A default that has no pill is
silently ignored. `add_to_queue` (`queue_tab.py:527`) also special-cases `"720"` to test
whether the user changed the value — fragile.

**Fix:** derive pills from `RESOLUTIONS`, and remove the "720" sentinel check.

### 2.3 `preview()` is dead

`queue_tab.py:468` fetches video info for preview but shows nothing. The README promises
"Video preview (title & duration) before downloading", which does not exist.

**Fix:** either render a real preview panel or drop the claim from the README.

### 2.4 Duplicated identical logic

- `get_clipboard_text` duplicated: `ui.py:50` and `queue_tab.py:52`.
- `format_size`, `play_file`, `delete_file`, `refresh_files`, row-pool pattern
  duplicated across `videos_tab.py` and `music_tab.py`.

**Fix:** extract shared helpers (`utils.py` or a `media_browser` base).

### 2.5 Music metadata scanned synchronously

`music_tab.py:283` reads mutagen tags for every file in the main thread during
`refresh_files`. Large folders freeze the UI for the whole scan.

**Fix:** scan in a background thread, update UI via `after`.

### 2.6 Stuck items after restart

Items persisted as `"downloading"` in `queue.json` are never rehabilitated on startup,
so they remain stuck after an app restart.

**Fix:** on load, downgrade `downloading` to `pending`/`paused` (or resume if actual
partial files exist).

### 2.7 No tests / no lint config

No test files exist and no linter (ruff/flake8) is configured. Download/queue logic
correctness is unverifiable.

**Fix:** add pytest for queue state transitions, URL validation, settings merge,
download hook parsing; add ruff config.

### 2.8 Minor issues

- Theme start flash: `main.py:8` hardcodes dark, `ui.py:26` switches to saved theme
  shortly after.
- `get_color` silently returns `#000000` on unknown keys — masks bugs (see 1.4).
- `detect_vlc` (`utils.py:84`) uses `which`, which does not exist on Windows (use
  `where`).
- `icon_manager.get(name, size)` re-reads the PNG file per call; row updates call it for
  every row on every refresh (`queue_tab.py:727`, `videos_tab.py:371`,
  `music_tab.py:481`).
- No history viewer or "clear history" UI; `history.json` grows unbounded.
- `update_storage` (`ui.py:379`) mocks a 100 GB max and swallows all exceptions.
- `save_history`/`save_queue`/`load_queue` are not thread-safe on the file side; queue
  writers race with `Downloader._save_partial_tracking`.
- `url_validator.is_supported_url` uses substring match on the host, so e.g.
  `notvimeo.com` passes.
- `settings_tab` default widget state says `sequential` while `config.DEFAULT_SETTINGS`
  says `parallel` (inconsistent defaults).
- `get_info` is called twice per add (duplicate check + title fetch) — wasteful network
  round trips.

---

## 3. Phased Plan

### Phase 1 — Queue state machine + cancel correctness (1.1, 1.2, 2.6)

- Introduce a "stop requested" token checked before starting any downloader.
- `stop_queue`: cancel all active downloaders, mark running items `paused`, reject new
  futures.
- Cancel path restores item to `paused` instead of `failed`.
- On queue load, rehabilitate `downloading` items to `pending`.
- `resume_item` and `start_queue` guard against double-start.

**Verify:** start N downloads, stop mid-flight — nothing continues, items resumable;
restart app with in-flight items — all runnable again.

### Phase 2 — Honor saved settings (1.3, 2.2)

- Respect `download_mode`: sequential runs pool size 1.
- Build resolution pills from `RESOLUTIONS`.
- Apply default resolution/audio correctly at add time without sentinel `"720"` check.
- Align settings widget defaults with `DEFAULT_SETTINGS`.

**Verify:** sequential mode runs downloads one at a time; default resolution with no
hardcoded value works for 144/240/360/480/720/1080.

### Phase 3 — Theme correctness (1.4, 2.8)

- Complete `COLORS["light"]`: add `muted`, `greige`, `secondary`, `hover`, `mid`,
  `success`, `warning` equivalents.
- Make `ThemeManager.get_color` strict (log/raise on unknown key).
- Replace hardcoded `#1B4A3A` and `#0A2822` with palette lookups.
- Remove startup theme flash in `main.py`.

**Verify:** both themes render all labels/buttons legibly; no `#000000` colors in light
mode.

### Phase 4 — Real progress UI (2.1)

- Add per-row progress bars driven by the already-computed hook data.
- Replace fake "50%"/pulsing active card with honest aggregate (average or summed
  bytes/ETA).
- Persist running item progress only in memory (do not spam `queue.json` per tick).

**Verify:** during parallel downloads each row shows live %, speed, ETA, bytes.

### Phase 5 — Async metadata + remove blocking (1.6, 2.3, 2.4, 2.5)

- Move `get_info` for add/preview into worker threads with loading state.
- Either implement a real title/duration preview panel or remove the README claim.
- Deduplicate clipboard logic into `utils.py`.
- Extract shared media-browser base for videos/music tabs.
- Scan music tags in a background thread.

**Verify:** pasting/add/clipboard never freezes the UI even on slow sites; large music
folders scan without blocking.

### Phase 6 — Resume + cookie test (1.5, 1.7)

- Define resume semantics; wire the actual partial path to yt-dlp `continue_dl` or
  delete the dead tracking code.
- Treat `None` `get_info` result as failure in the cookie test.

**Verify:** interrupted download resumes from where it stopped; cookie test fails clearly
when cookies are wrong.

### Phase 7 — Hardening (2.7, 2.8)

- Add `pyproject.toml` (ruff) and pytest suite covering queue transitions, URL
  validation, settings merge, hook parsing.
- Windows `where` fallback in `detect_vlc`.
- Cache scaled icons in `icon_manager`.
- Add history viewer / clear-history UI, or cap `history.json`.
- Make JSON persistence thread-safe (single write lock).
- Harden `is_supported_url` host matching.
- Replace bare `except:` blocks with explicit exception handling.

---

## 4. Status

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Queue state machine + cancel | Completed |
| 2 | Settings honored | Not started |
| 3 | Theme correctness | Not started |
| 4 | Progress UI | Not started |
| 5 | Async + dedupe | Not started |
| 6 | Resume + cookie test | Not started |
| 7 | Hardening | Not started |