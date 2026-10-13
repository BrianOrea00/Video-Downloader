# Video Downloader — Improvement Plan

Audit of the full codebase (branch `InProgress`, Sep 2026). This document lists every
problem found, grouped by severity, and the phased plan to fix them.

App: desktop downloader wrapping `yt-dlp`. Initially CustomTkinter; see Phase 8 — the
UI is being ported incrementally to PySide6 (Qt). Legacy modules: `main.py`, `ui.py`,
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

> **Absorbed into Phase 8.** CustomTkinter `theme_manager` and its palette hang is
> replaced by a Qt QSS stylesheet (dark/light). Not done as Tk work.

- Complete `COLORS["light"]`: add `muted`, `greige`, `secondary`, `hover`, `mid`,
  `success`, `warning` equivalents.
- Make `ThemeManager.get_color` strict (log/raise on unknown key).
- Replace hardcoded `#1B4A3A` and `#0A2822` with palette lookups.
- Remove startup theme flash in `main.py`.

**Verify:** both themes render all labels/buttons legibly; no `#000000` colors in light
mode.

### Phase 4 — Real progress UI (2.1)

> **Absorbed into Phase 8.** The downloader hook already computes `_percent`,
> `_speed_str`, `_eta_str`, `_downloaded_bytes_str`; the Qt queue page wires these into
> per-row progress bars. Not done as Tk work.

- Add per-row progress bars driven by the already-computed hook data.
- Replace fake "50%"/pulsing active card with honest aggregate (average or summed
  bytes/ETA).
- Persist running item progress only in memory (do not spam `queue.json` per tick).

**Verify:** during parallel downloads each row shows live %, speed, ETA, bytes.

### Phase 5 — Async metadata + remove blocking (1.6, 2.3, 2.4, 2.5)

> **Absorbed into Phase 8.** `get_info` for add/preview, async clipboard, music
> metadata scan, and the media-browser base all become Qt threading/delegate work.
> The README preview claim removal is done during the port.

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

> Note: icon caching is Tk-specific — skip it; Qt assets are handled in Phase 8.

### Phase 8 — PySide6 incremental port (UI rewrite)

Decision: port the UI from CustomTkinter to PySide6 (Qt) as a **Download Console** —
see §4 for the approved UI reference. QSS styling, virtualized lists, real per-row
progress, signal-based threading. The "Spotify-grade look" goal is dropped: the app is
a video downloader, not a music player. Engine, persistence, and queue state machine
survive; only the Tk UI layer dies. Port lands incrementally so the app keeps working
through the transition.

Target layout:

```text
models.py              # DownloadItem dataclass + DownloadStatus enum
queue_manager.py       # queue state machine (pure Python, extracted from queue_tab)
persistence.py         # thread-safe JSON (queue/history/settings), single write lock
thumb_cache.py         # fetch/store/serve yt-dlp thumbnails (from info['thumbnail'])
services/downloader.py # yt-dlp wrapper (survives), callbacks -> Qt signals at edge
ui/
  main_window.py       # shell + QStackedWidget
  sidebar.py
  theme.py             # QSS dark/light — arisu-pink palette (see §4)
  pages/queue_page.py  # Download Console: pinned active rows + input bar
  pages/videos_page.py # thumbnail grid (QListView icon-mode + delegate)
  pages/music_page.py  # metadata list (QThread scan)
  pages/settings_page.py
  widgets/queue_row.py # QWidget rows + real per-row progress bars
main.py                # PySide6 entry
```

Sub-steps (each lands a working app):

1. Extract `models.py` + `queue_manager.py` + `persistence.py` from `queue_tab` logic;
   port the Phase-1-style tests to the pure-Python manager.
2. PySide skeleton: main window, sidebar nav, dark QSS, stacked pages.
3. Port Queue page (highest value): add-URL, resolution pills, per-row progress driven
   by the existing hook data, stop/resume, storage bar, async `get_info`.
4. Port Videos/Music pages: Videos = thumbnail grid (word-wrapped QListView + delegate,
   real thumbs via `thumb_cache`, fallback icon when missing); Music = metadata list
   (QThread scan), play/delete.
5. Port Settings page + cookies UI; cookie test `None` handling (see Phase 6).
6. Light/dark QSS theme switch (replaces Phase 3).
7. Remove README preview claim or implement real preview (see Phase 5).
8. Delete Tk modules: `ui.py`, `queue_tab.py`, `videos_tab.py`, `music_tab.py`,
   `settings_tab.py`, `theme_manager.py`, `icon_manager.py`. Update README and
   `requirements.txt` (`-customtkinter`, `+PySide6`).

`queue.json` / `settings.json` / `history.json` schemas stay unchanged so user state
survives the rewrite.

**Verify:** queue stop/resume behaves per Phase 1; per-row progress live; large music
folders scan without blocking; both themes legible; tests pass on `queue_manager`.

---

## 4. UI Design Reference — Download Console (arisu-pink)

Approved UI direction (Sep 2026). Replaces the "Spotify-grade look" goal of Phase 8.
Decisions: keep Music tab, real thumbnail grid for Videos, dark + light themes, no
gradients, palette from user's nvim colorscheme `arisu-pink`.

### 4.1 Design principle

The app is a **download tool**, not a media player. Reference apps: IDM, JDownloader 2,
Downie (macOS). Primary mental model is a task pipeline:

```text
Paste URL → confirm format/res → fire → watch rows live → open file
```

The hero element is **progress**, not album art. No now-playing bar, no gradient hero
headers, no music-player decoration.

### 4.2 Palette — dark (arisu-pink, user's nvim theme)

Source: `~/.config/nvim/colors/arisu-pink.lua`.

| App token                     | Hex        |
|-------------------------------|------------|
| bg (window)                   | `#0a0710`  |
| bg_dark (deepest)             | `#05030a`  |
| sidebar                       | `#08050e`  |
| top bar / statusline          | `#0c0814`  |
| card (rows, panels)           | `#0f0b17`  |
| popup menu                    | `#130e1c`  |
| hover / line highlight        | `#1f192b`  |
| border / divider              | `#2a1f3a`  |
| text_primary                  | `#f8f2ff`  |
| text_secondary                | `#c9c3d4`  |
| muted / gutter                | `#6b5b7e`  |
| gray_light                    | `#8a7f9a`  |
| accent (nav, primary btn)     | `#ff79c6`  |
| pink_soft / pink_dim          | `#ff92d0` / `#e35aa5` |
| info numbers (size, duration) | `#bd93f9`  |
| success                       | `#50fa7b`  |
| error                         | `#ff5555`  |
| warning                       | `#ffb86c`  |
| paused                        | `#f1fa8c`  |

Flat fills only. No gradients.

### 4.3 Palette — light (derived, same hue family)

| App token      | Hex        |
|----------------|------------|
| bg             | `#fdfaff`  |
| sidebar        | `#f2ecfa`  |
| card           | `#ffffff`  |
| border         | `#d9cfe6`  |
| hover          | `#ece4f5`  |
| text_primary   | `#2a1e33`  |
| text_secondary | `#6b5b7e`  |
| muted          | `#8a7f9a`  |
| accent         | `#c1549c`  |
| success        | `#3ec96a`  |
| error          | `#e34c4c`  |
| warning        | `#e8833c`  |
| paused         | `#c9a227`  |

Accent = `pink_deep` (`#c1549c`), readable on white. Both themes required; the light
toggle stays.

### 4.4 Per-tab layout

**Queue — Download Console (primary)**

- Always-visible "New download" bar: URL field, paste, add; resolution pills derived
  from `config.RESOLUTIONS` (fixes §2.2); Audio-Only pill.
- Active downloads pinned top, one row each: status dot, title, res chip, **real
  per-row progress bar** (hook data already computed, see §2.1), speed, ETA, size,
  folder / cancel / retry actions.
- Completed rows collapse below. Status colors: pending `muted`, active `accent`,
  done `success`, fail `error`, paused `paused`.
- Aggregate honest (average/summed bytes + ETA), never fake "50%" pulsing (fixes §2.1).

**Videos — thumbnail grid**

- Card grid with real thumbnails. Flow: `Downloader` reads `info['thumbnail']`, writes
  it to `<download_path>/.thumbs/<sha1(url)>.jpg` on completion, records filename in
  `history.json`. Videos page renders grid (icon-mode QListView + delegate or
  QListWidget) with `QPixmap`, search by title/name, play/delete.
- Fallback icon when thumb missing. `.thumbs/` added to `.gitignore`.

**Music — restyled list (kept)**

- Keep the mutagen-backed metadata list (title, artist, duration, size). Scan in a
  QThread (fixes §2.5), search/play/delete. No thumbnails, no now-playing bar.

**Settings** — unchanged form page, arisu-pink restyle.

### 4.5 Thumbnail cache

- Store: `info['thumbnail']` → `<path>/.thumbs/<sha1(url)>.jpg` at download end.
- Load: videos page scans `.thumbs/`, keyed by history entry. Missing → placeholder.
- Never blocks the UI: fetch/store run off the main thread.

### 4.6 Scope notes

- Videos + Music share a media-browser base (fixes §2.4); Music = base list, Videos =
  grid override.
- Size/speed/ETA numbers in a monospace font for readability.
- README: replace "Spotify-grade" phrasing with Download Console; document thumbnails.
- Implementation order: theme → queue page → videos + thumbs → music → settings → then
  delete the Tk modules (Phase 8 sub-step 8).

### 4.7 Typography — Monocraft

The UI uses **Monocraft** (a monospaced pixel font derived from the Minecraft typeface)
for all text, including the numeric readouts.

- Installed for the current user at `~/.local/share/fonts/monocraft/` (Monocraft v4.2.1,
  regular plus every weight). The fontconfig family name is exactly `Monocraft`; run
  `fc-cache -f` after installing so Tk can find it.
- `ThemeManager.apply_custom_theme()` sets the CustomTkinter default font family to
  `Monocraft`. Every `CTkFont` created without an explicit family inherits it, so one
  change covers the whole UI. The readouts that previously passed `family="monospace"`
  (queue, videos, music) now pass `family="Monocraft"` as well.
- Tk resolves fonts through fontconfig and silently falls back to a default face when the
  family is missing — there is no runtime error if Monocraft is absent. The install is
  user-scoped, so other machines or users must install it separately.
- Reinstall: download `Monocraft-ttf.zip` from
  https://github.com/IdreesInc/Monocraft, copy the `.ttf` files into
  `~/.local/share/fonts/monocraft/`, then run `fc-cache -f`.

---

## 5. Status

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Queue state machine + cancel | Completed |
| 2 | Settings honored | Not started |
| 3 | Theme correctness | Absorbed into Phase 8 |
| 4 | Progress UI | Absorbed into Phase 8 |
| 5 | Async + dedupe | Absorbed into Phase 8 |
| 6 | Resume + cookie test | Not started |
| 7 | Hardening | Not started |
| 8 | PySide6 port (replaces 3/4/5 UI) | Not started |