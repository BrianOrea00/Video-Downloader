# Feature Backlog

Candidate features for Video Downloader, ordered by value against the current codebase.
Companion to `PHASES.md`: that file covers correctness and release readiness, this one
covers product surface.

Every entry was checked against the tree, so nothing here duplicates what already exists
(theme families, collapsible sidebar, link preview, per-row progress, thumbnail grid,
music metadata list, settings form, cookies UI, duplicate detection, retry-with-backoff at
the engine level).

---

## Current surface (for reference)

- Queue: add URL, preview panel, resolution pills (`config.RESOLUTIONS`), audio-only,
  start/stop, clear completed, per-row progress + cancel/delete
  (`ui/pages/queue_page.py:134-200`, `:369-376`).
- Library: shared `MediaBrowser` base (`ui/pages/media_page.py:120`), thumbnail grid for
  video, mutagen metadata list for music, search, play, delete, refresh.
- Engine: `Downloader` with 3 retries + backoff, `continuedl`, optional cookies
  (`downloader.py:63-213`).
- Persistence: queue/history/settings JSON, atomic writes, `downloading`→`pending`
  rehabilitation (`persistence.py`, `queue_manager.py:51`).

---

## Tier 1 — cheap, high perceived value

### 1.1 Per-item retry

**Problem.** Rows expose Cancel and Delete only (`ui/pages/queue_page.py:196-200`). A
failed item must be deleted and re-pasted; there is no way to retry in place, and no bulk
"retry failed".

**Implementation.**
- `QueueManager.retry(index)` → set status `pending` (reuse the clamp logic in
  `queue_manager.py:172` `resume()`).
- Row action next to cancel, visible only for `failed`.
- Queue-level "Retry failed" button beside "Clear completed"
  (`ui/pages/queue_page.py:376`).

**Verify.** Fail a download (bad cookie/file state), retry from the row — item re-runs and
persists; retry twice does not double-run (guard with `has_running`).

### 1.2 Keyboard shortcuts and drag-and-drop

**Problem.** No `QShortcut` and no `setAcceptDrops` anywhere in the tree. Everything is
mouse-driven.

**Implementation.**
- `QShortcut` on the main window: `Ctrl+V` paste, `Enter` add, `Ctrl+Enter` add+start,
  `Del` remove selected row, `Ctrl+O` choose folder, `Ctrl+1..4` navigate.
- `dragEnterEvent`/`dropEvent` on `QueuePage`: accept URLs and text files containing one
  URL per line; reuse the multi-URL path from 2.7.

**Verify.** All shortcuts act on the focused page only; dropping an unsupported URL shows
the existing validation message rather than a traceback.

### 1.3 Playlist policy (correctness hazard, not just a feature)

**Problem.** `url_validator.py:15` accepts `youtube.com/playlist?list=…`, but nothing sets
`noplaylist` in `downloader.py:143-152`. yt-dlp's default behavior for a playlist URL is to
download **every entry**, while the UI shows a single row with one resolution. Users
silently get dozens of files, or a failure that looks like a bug.

**Implementation.** Choose one:
- **Reject:** drop the playlist pattern from `url_validator.py:15` and explain why in the
  field's error state; or
- **Import:** detect playlists during preview (`InfoWorker`, `queue_page.py:100`), fetch
  with `extract_flat='in_playlist'`, show a confirmation ("Import 42 videos?"), then add N
  `DownloadItem`s with per-entry URLs.
- Always set `'noplaylist': True` for ordinary watch URLs that carry a `list=` parameter.

**Verify.** Pasting a watch URL with `&list=` downloads one video; a bare playlist URL is
either refused or imports N rows, never one row hiding N downloads.

### 1.4 Completion notifications

**Problem.** Long downloads finish silently; `run_finished` (`queue_runner.py:33`) is only
used to re-enable buttons.

**Implementation.** `QSystemTrayIcon.showMessage()` on `run_finished` with a summary
("3 completed, 1 failed"); optional tray icon with a progress tooltip. Gate behind a
"Notify when finished" setting so headless/quiet users can disable it.

**Verify.** Notification fires once per run, never per item; disabled setting produces no
tray icon.

### 1.5 Reveal in file manager

**Problem.** Rows open the file (`ui/pages/queue_page.py:603-612`) but there is no way to
reach the containing folder.

**Implementation.** Reuse the platform branches: `explorer /select,<path>` on Windows,
`open -R` on macOS, `xdg-open <dir>` on Linux; add a "Folder" icon button to `QueueRow`
and a context-menu entry in `MediaBrowser._context_menu` (`media_page.py:262`).

---

## Tier 2 — expected from a downloader

### 2.1 Filename safety and templates

**Problem.** `downloader.py:144` is `f'{path}/%(title)s.%(ext)s'`. Long titles, `/`,
Windows-reserved names, emoji, and duplicate titles all produce broken or colliding files.
`utils.py:22` has an unused `clean_filename`, which suggests this was intended.

**Implementation.** `outtmpl` setting with a documented default such as
`%(title).120B [%(id)s].%(ext)s`; toggles for `restrictfilenames` and (on Windows)
`windowsfilenames`; optional subfolder template `%(uploader)s/`. Keep the setting
string-only so it can be edited without a UI rebuild.

**Verify.** Titles with `/`, `:`, 300+ characters, and duplicates produce distinct, valid
filenames on each platform.

### 2.2 Per-item format override

**Problem.** Resolution and audio-only are fixed at add time (`models.py:39-58`); changing
your mind means remove + re-add.

**Implementation.** Row-level menu (resolution pills, audio toggle) writing to the item,
enabled only for `pending`/`paused`. New fields are schema-safe because
`from_dict` (`models.py:67`) tolerates missing keys; update `to_dict` and the tests.

**Verify.** Changing a pending item's resolution persists across restart and affects the
actual yt-dlp format string.

### 2.3 Metadata, thumbnail, and subtitle embedding

**Problem.** Postprocessors are used only for audio extraction
(`downloader.py:157-162`).

**Implementation.** Settings switches wiring yt-dlp options: `FFmpegMetadata`,
`writethumbnail` + `FFmpegThumbnailsConvertor` + `EmbedThumbnail`,
`writesubtitles`/`subtitleslangs` + `FFmpegEmbedSubtitle`. Everything flows through the
existing `ydl_opts` construction; no new engine code.

**Verify.** Output `.mp4` carries title/artist tags, cover art, and embedded subs; audio
`.mp3` keeps ID3 metadata.

### 2.4 True download archive

**Problem.** Duplicate detection is URL-only against the live queue and history
(`queue_manager.py:112`). Delete a history entry and the app re-downloads happily.

**Implementation.** yt-dlp `download_archive` file in the app data dir (see `PHASES.md`
§7.3 B1 for the data-root change); record `extractor id`, not raw URL, so redirects and
`youtu.be`/`watch?v=` variants collapse.

**Verify.** Downloading, deleting from history, then re-adding the same URL reports
"already in archive" and skips the transfer.

### 2.5 Rate limit and fragment concurrency

**Problem.** No global speed cap; parallel downloads can saturate a connection.

**Implementation.** `ratelimit` (e.g. "2M") and `concurrent_fragment_downloads` settings,
validated in the Settings page. Document that the cap is per download, not global.

### 2.6 Proxy support

**Problem.** No `proxy` option; users behind regional or corporate blocks cannot use the
app at all.

**Implementation.** `proxy` setting validated by `urllib.parse`, passed to `ydl_opts`;
"Test proxy" button reusing the existing `CookieTestWorker` pattern.

### 2.7 Multi-URL input

**Problem.** `add_to_queue` handles exactly one URL (`queue_page.py:509-546`).

**Implementation.** Split input on newlines, run the existing duplicate checks per line,
add all valid entries in one `manager` transaction, report skipped lines in the status
area. Pairs with 1.2 drag-and-drop.

---

## Tier 3 — app polish

- **3.1 History page.** History is already stored and only used for duplicate detection
  (`persistence.py:66-76`). A searchable table with "download again", "open", "delete"
  makes the data useful and closes `PHASES.md` §6.3.
- **3.2 Queue filters.** Status chips (`all/pending/active/done/failed`); rows currently
  render in one undifferentiated list.
- **3.3 Bulk selection.** Checkboxes plus "start selected / remove selected" for large
  queues.
- **3.4 Scheduled start.** `QDateTimeEdit` + timer that calls the existing `start()`; useful
  with sequential mode for overnight batches.
- **3.5 Media library actions.** Rename, move, copy path, open containing folder —
  `MediaBrowser` currently offers play/delete only (`media_page.py:262-273`).
- **3.6 SponsorBlock and clip ranges.** `sponsorblock_remove` toggle and `download_ranges`
  for section downloads. Each is a settings entry plus a postprocessor; defer until Tier 2
  lands.

---

## Tier 4 — deliberately out of scope

Channel/feed subscriptions with polling, built-in transcoding presets, per-item cookie
sources, cloud sync. Each duplicates a dedicated tool and adds support burden before the
app is distributed; revisit only with real user demand.

---

## Cross-cutting constraints

- New yt-dlp options must travel settings → `QueueRunner.start` (`queue_runner.py:47-56`)
  → `Downloader.download` (`downloader.py:63`). No module-level globals, or the core tests
  stop covering behavior.
- `DownloadStatus` values are the persisted contract (`models.py:16-30`). Add fields to
  `DownloadItem`; never rename status strings.
- Network calls belong in the existing worker pattern (`InfoWorker`, `ThumbWorker`,
  `queue_page.py:100-133`), never on the GUI thread.
- Any row action that changes state must go through `QueueManager` so `save()` and
  `queue.json` stay consistent (`queue_manager.py:70`).
- Features that change download semantics (playlist import, archive, filename templates)
  need a note in the release changelog; `queue.json` rows only carry
  `path`/`resolution`/`audio_only`.

---

## Recommended order

1. **1.3 Playlist policy** — fixes a data-risk bug before adding surface area.
2. **1.1 Per-item retry** — smallest change with visible payoff.
3. **1.2 Shortcuts and drag-and-drop** — highest usability gain per line.
4. **2.1 Filename safety** — prevents user-visible corruption on other platforms.
5. **2.7 Multi-URL** → **1.4 Notifications** → **2.4 Archive** → **2.3 Embedding**.

Tier 3 follows once Tiers 1–2 are shipped and the release pipeline exists
(`PHASES.md` §7.10).
