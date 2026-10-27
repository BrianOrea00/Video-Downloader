# Video Downloader — Improvement Plan

Audit of the full codebase (branch `InProgress`, Sep 2026). This document lists every
problem found, grouped by severity, and the phased plan to fix them.

App: desktop downloader wrapping `yt-dlp`. The UI is PySide6 (Qt) — the port from
CustomTkinter landed in Phase 8. The Tk modules (`main.py` `ui.py` `queue_tab.py`
`videos_tab.py` `music_tab.py` `settings_tab.py` `theme_manager.py` `icon_manager.py`)
are deleted. The current tree is `models.py`, `queue_manager.py`, `queue_runner.py`,
`persistence.py`, `thumb_cache.py`, `downloader.py`, `url_validator.py`, `utils.py`,
`config.py`, `logger.py`, and the `ui/` package.

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

**Resolved (Phase 6):** the dead tracking code is deleted. yt-dlp's `continuedl` already
resumes from the `<outtmpl>.part` file, so no app-side partial tracking is needed.

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

**Resolved (Phase 6):** `test_cookies` now raises on a `None`/falsy `get_info` result, so
the failure path reports "Cookie Test Failed" instead of crashing on `None.get`.

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

### Phase 6 — Resume + cookie test (1.5, 1.7) — **Completed**

- Resume: remove the dead partial-tracking code (`_find_partial_file`,
  `_save_partial_tracking`, `_clear_partial_tracking`, the `_partial_file` field, and
  their call sites). yt-dlp's `continuedl` already resumes from the `<outtmpl>.part`
  file, so resume works without app-side bookkeeping. This also removes the extra
  `queue.json` writer race noted in 2.8.
- Cookie test: a `None` result from `get_info` now raises, so the cookie test reports a
  clear failure instead of crashing on `None.get` or faking "Cookie test passed".

**Verify:** interrupted download resumes from where it stopped (yt-dlp default behavior);
cookie test fails clearly when cookies are wrong.

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

### Phase 8 — PySide6 incremental port (UI rewrite) — **Completed**

Decision: port the UI from CustomTkinter to PySide6 (Qt) as a **Download Console** —
see §4 for the approved UI reference. QSS styling, virtualized lists, real per-row
progress, signal-based threading. The "Spotify-grade look" goal is dropped: the app is
a video downloader, not a music player. Engine, persistence, and queue state machine
survive; only the Tk UI layer dies. The port landed incrementally so the app kept
working through the transition. All eight sub-steps are done; the Tk modules are
deleted.

Target layout:

```text
models.py              # DownloadItem dataclass + DownloadStatus enum
queue_manager.py       # queue state machine (pure Python, extracted from queue_tab)
queue_runner.py        # threaded download executor emitting Qt signals
persistence.py         # thread-safe JSON (queue/history/settings), single write lock
thumb_cache.py         # fetch/store/serve yt-dlp thumbnails (from info['thumbnail'])
downloader.py          # yt-dlp wrapper (survives), callbacks -> Qt signals at edge
ui/
  main_window.py       # shell + QStackedWidget
  sidebar.py
  theme.py             # QSS dark/light — arisu-pink palette (see §4)
  pages/queue_page.py  # Download Console: pinned active rows + input bar
  pages/media_page.py  # shared media-browser base
  pages/videos_page.py # thumbnail grid (QListView icon-mode + delegate)
  pages/music_page.py  # metadata list (QThread scan)
  pages/settings_page.py
main.py                # PySide6 entry
```

Sub-steps (each lands a working app):

1. Extract `models.py` + `queue_manager.py` + `persistence.py` from `queue_tab` logic;
   port the Phase-1-style tests to the pure-Python manager.
2. PySide skeleton: main window, sidebar nav, dark QSS, stacked pages.
3. Port Queue page (highest value): add-URL, link preview panel (see §4.4), resolution
   pills, per-row progress driven by the existing hook data, stop/resume, storage bar,
   async `get_info`.
4. Port Videos/Music pages: Videos = thumbnail grid (word-wrapped QListView + delegate,
   real thumbs via `thumb_cache`, fallback icon when missing); Music = metadata list
   (QThread scan), play/delete.
5. Port Settings page + cookies UI; cookie test `None` handling (see Phase 6).
6. Light/dark QSS theme switch (replaces Phase 3).
7. Implement the real link preview panel (§4.4) so the README claim holds; keep the
   fetch off the UI thread. (Resolves the Phase 5 preview item.)
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
- Paste (or a valid URL) reveals a **link preview panel** below the field: thumbnail with
  a duration badge, title, and meta chips (channel, duration, views, estimated size).
  Fetch runs off the main thread (§1.6); `None` from `get_info` shows a "could not fetch"
  state. Reuse the fetched info for the queue item so no second `get_info` runs (§2.8).
  Reference: `docs/ui-prototype.html` `#preview`.
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
| 2 | Settings honored | Completed |
| 3 | Theme correctness | Absorbed into Phase 8 |
| 4 | Progress UI | Absorbed into Phase 8 |
| 5 | Async + dedupe | Absorbed into Phase 8 |
| 6 | Resume + cookie test | Completed |
| 7 | Hardening | Completed (Python items) — `pyproject.toml` (ruff) + tests added, thread-safe `persistence.py`, `where` fallback, host-match hardening, explicit `except` handling. The Tk-only items (icon caching, theme flash) are moot — see Phase 8. |
| 8 | PySide6 port (replaces 3/4/5 UI) | Completed — sub-steps 1-8 done; Tk modules deleted, `requirements.txt` is PySide6-only, README rewritten |
| 9 | Remaining backlog | Completed — clipboard polling (§6.1), `ui_scale` control (§6.2), history cap/clear (§6.3), queue reorder (§6.4), dead-code cleanup (§6.5). |
| 10 | Public-release blockers | Completed — per-user data dirs + migration, bundled assets and Monocraft, requirements with extras, single instance, icon/version/About, live storage meter, excepthook. First run defaults to `~/Downloads`, so adding a link works immediately. See §7.3–7.4. |
| 11 | License + repo hygiene | Completed except issue/PR templates — GPL-3 + notices, CI lint/test matrix on 3.11-3.13, `SECURITY.md`, log redaction. See §7.2, §7.7, §7.9. |
| 12 | Engine update path | Completed, frozen-build proof pending — runtime wheel swap with SHA256 verification and fallback; verified against live PyPI in a source run. See §7.6. |
| 13 | Packaging + signing | In progress — PyInstaller spec, `.desktop`, AppStream metadata and packaging notes are in `packaging/`; the build itself, platform installers and signing are not done. See §7.5. |
| 14 | First public release | Planned — docs, screenshots, support policy. See §7.10. |

---

## 6. Remaining Backlog (post-Phase 8)

State at time of writing: tree clean, 36 unittest tests pass
(`yt-env/bin/python -m unittest discover -s tests -t .`). No active plan. Items are
ordered by value, not by file.

### 6.1 Clipboard auto-detection is still dead UI

`config.py:12-13` defines `auto_clipboard` and `clipboard_interval`;
`ui/pages/settings_page.py:157-169` renders and persists both controls. Nothing polls the
clipboard: `ui/pages/queue_page.py:418` reads `QApplication.clipboard()` only when the
user clicks paste. Two settings are inert, and the decision record still lists this as
"not yet wired".

**Fix:** own a `QTimer` in `QueuePage`, interval from `clipboard_interval`, gated by
`auto_clipboard`; validate through `url_validator`; skip when the URL field has focus or
the text is unchanged from the last seen value; stop polling while a preview fetch is in
flight.

**Verify:** copying a supported URL auto-fills and previews; unsupported text is ignored;
toggling the setting off stops polling immediately; interval change re-arms the timer.

### 6.2 `ui_scale` has no Settings control

`config.py:20` and `main.py:20` read the value once at startup; there is no widget. At
`1.5` the minimum window is 1350x900, at `2.0` ~1728x972, so this is not a cosmetic knob.

**Fix:** add a scale control to the Settings APPEARANCE card (discrete steps 1.0/1.25/
1.5/1.75/2.0), persist via the existing `settings_changed` path, and note that a restart
applies it — re-scaling the live window is larger than this item.

**Verify:** changing the control writes `settings.json`; restart renders at the new scale
with no clipped labels and pages still navigable.

### 6.3 History has no viewer, no clear, no cap

`persistence.py:66-76` appends forever and only `ui/pages/queue_page.py:624` writes.
`history.json` grows unbounded and is only consumed for duplicate detection.

**Fix:** add a clear-history action (confirm dialog, then `save_history([])` style atomic
write) and a cap (e.g. 1000 most recent entries, trimmed on write). A full history page is
optional and out of scope for this item.

**Verify:** clear empties history without touching the queue; a 1000-entry history stays
at 1000 after another append; duplicate detection still works on retained entries.

### 6.4 Queue prioritize (move up/down) not ported

Dropped during the port and recorded as a known limitation. The manager has no reorder
API, so this needs a `QueueManager` method plus row buttons.

**Fix:** `QueueManager.reorder(index, delta)` guarded to `pending`/`paused` items only,
persisting through the injected store; wire up/down actions on the queue row.

**Verify:** reorder persists across restart; running and completed rows cannot be moved;
unit test covers clamping at both ends.

### 6.5 Dead legacy code in `utils.py` and `config.py`

- `utils.py`: `save_history` (5), `clean_filename` (22), `load_queue` (25),
  `save_queue` (35), `load_settings` (40), `save_settings` (51) are all superseded by
  `persistence.py` and have no callers. `utils.py` also still carries the Phase 7
  leftovers: bare `except:` at 32, 48, 87 and a `which`-only PATH lookup at 84 that does
  not work on Windows.
- Only `detect_vlc` is live, imported inline at `ui/pages/media_page.py:281`.
- `config.py:25-46` still holds a `THEMES` dict commented "CustomTkinter custom theme
  handles colors". `ui/theme.py:18` owns palettes now; `config.THEMES` has no readers.

**Fix:** move `detect_vlc` into `utils.py`'s surviving role as the single live helper
(fix the Windows `where` fallback and replace the bare excepts with explicit ones), delete
the duplicated JSON helpers and `clean_filename` after confirming zero callers, and delete
`config.THEMES`.

**Verify:** `grep` shows no references to the removed names; app launches, VLC detection
still returns a path on Linux; tests still pass.

### 6.6 Order

6.1 → 6.2 → 6.5 → 6.4 → 6.3. 6.5 is a pure cleanup and can ride along with any other
change; 6.3 needs a small UI decision (where the clear action lives) before it starts.

---

## 7. Public Release Readiness

Goal: hand the app to users who do not have this repo, this venv, Monocraft installed,
or ffmpeg on PATH. Everything below was measured against the current tree, not assumed.

Current state: 36 core tests pass; no CI, no `LICENSE`, no `.spec`, no `.ico`/`.icns`,
no `.desktop` file. The app works because the cwd is writable and the host has the font
and ffmpeg.

### 7.1 Measured facts

| Item | Value |
|------|-------|
| `PySide6` install size | 673 MB; `PySide6/Qt/lib` = 457 MB incl. `libQt6WebEngineCore.so.6` |
| Qt modules imported by the app | `QtCore` ×6, `QtGui` ×2, `QtWidgets` ×9 — nothing else |
| `yt_dlp` / `mutagen` size | 25 MB / 1.7 MB |
| `requirements.txt` yt-dlp pin | `2026.3.17` (`requirements.txt:1`) |
| yt-dlp actually installed | `2026.8.19` (= current PyPI latest) |
| yt-dlp default extras present | none (`requests`, `websockets`, `certifi`, `brotli`, `Cryptodome`, `yt_dlp_ejs`, `secretstorage` all absent) |
| PyInstaller / platformdirs | not installed / not installed |

### 7.2 License — decides the project license

| Dependency | License | Consequence |
|------------|---------|-------------|
| `mutagen` 1.47 | `GPL-2.0-or-later` | **forces a GPL-compatible app license**; MIT/Apache is not possible while bundling it |
| `PySide6` 6.12 | `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0` | choosing GPL-3 for the app removes LGPL relinking duties |
| `yt-dlp` | Unlicense | none |
| Tabler icons (`README.md:76`) | MIT | ship copyright + permission text |
| Monocraft (planned bundle) | OFL-1.1 | ship `OFL.txt`; unmodified bundling only |
| PyInstaller | GPLv2+ w/ bootloader exception | fine |
| Nuitka | AGPL-3 | avoid; weaker yt-dlp support |

Decision: **`GPL-3.0-or-later`** — the only option simultaneously valid with mutagen, Qt
and yt-dlp. Accepting redistribution is the cost. Alternative: drop `mutagen`
(`ui/pages/media_page.py:57-59`) and keep a permissive license.

### 7.3 Blockers (crash or visible failure for a stranger)

**B1. Relative paths — crash before a window exists**

- `logger.py:7-8` creates `logs/` at import time; `main.py:6` imports it.
- `config.py:3-5` — `history.json`, `queue.json`, `settings.json` are bare filenames.
- Installed under `/Applications`, `C:\Program Files`, AppImage root: `PermissionError`
  before `QApplication`, and no log to explain it.
- Fix: resolve one data root (stdlib per-platform logic, or `platformdirs`), use absolute
  paths everywhere. Note `platformdirs` latest needs **Python ≥3.11** while `README.md:85`
  and `pyproject.toml:4` say 3.10 — raise the floor or hand-roll ~20 lines.

**B2. Bundled assets are cwd-relative**

- `ui/pages/media_page.py:246` — `QPixmap("assets/video.png")`; in a frozen app the cwd is
  arbitrary and the file lives in `_MEIPASS`. Fails silently (`isNull()` → empty pixmap).
- Fix: one `resource_path()` helper (`sys._MEIPASS` when frozen) or `importlib.resources`,
  and ship `assets` as spec `datas`.

**B3. Font not shipped**

- `ui/theme.py:174-175` — `Monocraft` with `monospace` fallback; no
  `QFontDatabase.addApplicationFont` anywhere. The `ui_scale` metrics were tuned around
  this font, so strangers get a different-looking app.
- Fix: bundle the regular weight, register in `main.py` before `apply_theme`, ship OFL.

**B4. Media binaries and cookie backends missing**

- `downloader.py:158` (`FFmpegExtractAudio`), `downloader.py:167`
  (`merge_output_format: mp4`) need system ffmpeg.
- `downloader.py:52-57` `cookiesfrombrowser` needs `secretstorage` for Chromium on Linux —
  confirmed missing at `yt_dlp/dependencies/__init__.py:32-41`, so that path is already
  broken here.
- `yt_dlp_ejs` absent (`yt_dlp/dependencies/__init__.py:85-87`); metadata extraction still
  worked in a live probe (53 formats), but JS-challenged formats may not.
- Fix: `yt-dlp[default]==<pin>` + `secretstorage; sys_platform == "linux"`, bundle ffmpeg
  and pass `ffmpeg_location`, detect at startup and disable audio-only with an explanation.

**B5. No single-instance guard**

`persistence.py:26` lock is process-local; a second launch double-clicks into a race on
`queue.json` (written on every transition) → lost rows, duplicate downloads. Add
`QLockFile` in the data dir and focus the running window.

**B6. No icon, desktop entry, or version**

`ui/main_window.py:42` sets only a title. No `setWindowIcon`, `.ico`/`.icns`, `.desktop`,
`setApplicationVersion`, or `setDesktopFileName` → generic Python icon in dock/taskbar,
no Linux launcher entry, unidentifiable process. Ship icons per platform, a `.desktop` +
AppStream XML, and one `__version__` read by pyproject and an About dialog (GPL text and
source link belong there).

### 7.4 Dependency correctness ("works on my machine")

- `requirements.txt:3` — `PySide6>=6.12.0` pulls the Addons metapackage, hence WebEngine's
  400+ MB. The app imports only Core/Gui/Widgets: use `PySide6-Essentials==6.12.0`.
- `requirements.txt:1` — exact pin `2026.3.17` while `2026.8.19` is installed. No lock,
  no hashes. Add a lock and one source of truth for the engine version.
- yt-dlp ships its own PyInstaller hook (`yt_dlp/__pyinstaller/hook-yt_dlp.py`) registered
  through a `pyinstaller40` entry point; it already collects `websockets`, `requests`,
  `urllib3`, `mutagen`, `brotli`, `certifi`, `secretstorage`, `curl_cffi` and the
  `yt_dlp_ejs` payloads. Install the extras; do not hand-maintain `hiddenimports`.
- Add `platformdirs` (or equivalent) and `secretstorage` to the dependency set.

### 7.5 Packaging

- Tool: **PyInstaller 6.22.x**. yt-dlp maintains a hook for it; Nuitka is AGPL-3 with a
  less predictable yt-dlp path.
- Shape: **one-dir**, not one-file (one-file re-extracts ~200 MB per launch, trips
  antivirus, and breaks `.part` resume when temp is cleared).
- Size: Essentials-only ≈ 120–180 MB; with a static ffmpeg ≈ 200–260 MB. Exclude
  `QtWebEngine*`, `QtQml`, `QtQuick`, `Qt3D*`, `QtDesigner`, `QtCharts`, `QtMultimedia`,
  `PySide6.scripts`, unused translations. Verify with a size report after the first build.
- Linux: AppImage (`.desktop`, icon, AppRun) + `tar.gz` + SHA256. Flatpak only if
  sandboxing is worth the cookie/file-access friction.
- Windows: per-user Inno Setup installer under `%LOCALAPPDATA%` + portable zip. Unsigned
  builds warn in SmartScreen; an OV/EV cert (hardware token) is the only fix.
- macOS: `.app` in a `.dmg`, Developer ID signed + notarized (hardened runtime). Requires
  the Apple Developer Program. Keys live in CI secrets, never in the repo.
- Frozen hazards to test: SSL without `certifi`, Qt platform plugin (`xcb`) on minimal
  Linux, and the `os.startfile`/`open`/`xdg-open` branches (`media_page.py:285-291`,
  `queue_page.py:606-612`) which have never run on Windows/macOS here.
- CI builds on all three OSes; PyInstaller cannot cross-compile.

### 7.6 Engine updates

- `downloader.py:1` imports `yt_dlp` at module scope and `main.py` imports it
  transitively, so any `sys.path` override must happen in `main.py` **first**.
- `yt_dlp.update` only works for frozen single binaries (`is_non_updateable`), so it cannot
  update a bundled package.
- Workable design: bundled baseline → read `user_data_dir/engine/current.json` → prepend a
  newer verified wheel dir to `sys.path` → update by downloading the `py3-none-any` wheel
  from `https://pypi.org/pypi/yt-dlp/json`, verifying its SHA256 from the same response,
  unpacking into `engine/<version>/`, atomically rewriting `current.json`, and falling back
  to the bundled copy if import fails.
- Must be proven at build time: whether PyInstaller's frozen importer yields to a runtime
  `sys.path` prepend. Test with two deliberately different versions before building UX.
- Rejected alternative: execing a yt-dlp binary — loses the info dict that feeds
  thumbnails and `info_callback` (`queue_page.py:650`).

### 7.7 Privacy and public-repo surface

- `downloader.py:71,82,171,175,183,189,201,213` log full URLs → watch history in
  `logs/app.log`. Fine locally; redact paths/queries and the home dir in any diagnostics
  export.
- `settings.json` stores `cookie_file_path` and the browser name: never log, never include
  in diagnostics.
- Keep no telemetry, or make it opt-in with a visible switch.
- Any auto-update must verify hashes/signatures; unsigned updates are RCE by design.
- Add `SECURITY.md` — the app touches browser cookies, so a disclosure address is expected.

### 7.8 Correctness a stranger notices in hour one

- Storage meter is dead: `ui/sidebar.py:209` `set_storage()` has no callers; the sidebar
  always shows `0 GB` (`sidebar.py:139`). Wire `shutil.disk_usage` or delete the widget.
- `ui/main_window.py:44-53` clamps the minimum to 90% of the screen but requests
  `px(1200)×px(700)` = 1800×1050 at scale 1.5. On 1366×768 that overflows horizontally.
  Test 1280×720; consider picking the initial scale from the screen.
- First run has `download_path: ""` (`config.py:16`) and `add_to_queue` refuses with a
  dialog (`queue_page.py:513-516`): a stranger's first click fails. Add onboarding:
  folder, scale, audio default.
- No `sys.excepthook` — a Qt slot exception vanishes into a windowed build's stderr. Add a
  handler that logs and offers "copy diagnostics".

### 7.9 Tests and CI

- Existing 36 tests cover `queue_manager`, `persistence`, `theme`, `thumb_cache` only; no
  coverage of `QueueRunner` cancellation or any Qt page.
- CI on 3.11–3.13: ruff + unittest, plus an offscreen (`QT_QPA_PLATFORM=offscreen`) GUI
  smoke test (nav, add with stubbed downloader, theme switch, settings save).
- Build job per OS must at least launch the produced binary offscreen so a missing Qt
  plugin fails CI instead of users.

### 7.10 Plan

| Phase | Scope | Effort |
|-------|-------|--------|
| 10 | B1 data dirs + migration, B2 resources, B3 font, B4 ffmpeg/extras, B5 single instance, B6 icon/version, storage meter, excepthook, onboarding | 4–6 d |
| 11 | GPL-3 + `THIRD_PARTY_NOTICES.md` (Tabler, OFL, Qt, yt-dlp, mutagen, ffmpeg), CI matrix, issue/PR templates | 1–2 d |
| 12 | Engine update path (design + frozen-importer proof) | 2–4 d |
| 13 | PyInstaller specs, icons, `.desktop`, AppImage/Inno/dmg, signing, release workflow | 5–8 d |
| 14 | First public release: docs, screenshots, support policy | 1–2 d |

Critical path: **10 before 13** — packaging a relative-path app ships a binary that
crashes on launch for everyone but the author.

### 7.11 Open decisions

1. License: accept GPL-3, or drop `mutagen` to stay permissive? (blocks 11)
2. Target platforms and order — Windows adds signing cost, macOS adds $99/yr + notarization.
3. Distribution channel: GitHub Releases only, or Flathub/AUR/Homebrew cask too?
4. Engine updates: runtime wheel swap (fast, more moving parts) vs app releases only?
5. Whether PyInstaller's frozen importer yields to a prepended `sys.path` — measure it.