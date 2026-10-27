# UI Improvement Spec

Status: proposed, not implemented. Scope: the PySide6 desktop UI in `ui/`.
Companion reference: `docs/ui-prototype.html` — every fix below that can be shown
statically is demonstrated there and tagged with the same number
(`data-fix="N"`). Toggle **Fixes** in the prototype's top bar to outline the
tagged regions.

Nothing in this document changes behaviour outside the UI layer. Data flow,
downloads, persistence, and yt-dlp options stay as they are.

---

## 1. Evidence baseline

Measured on this machine, at the shipped defaults (`theme_family=arisu`,
`theme=dark`, `ui_scale=1.5`):

- Render check: `QT_QPA_PLATFORM=offscreen` grab of the running window at
  1200×760 (`/tmp/opencode/ui_queue.png`, `/tmp/opencode/ui_settings.png`).
- Contrast: WCAG relative-luminance calculation against each theme's own
  `card`/`bg` tokens (table in §3.1).
- Code read: all 2,292 lines under `ui/`.

Three defects are visible in that render without any interaction: the settings
form paints as stripes, the queue card overflows horizontally and hides "Add to
Queue", and the disabled Stop button still looks enabled.

`PHASES.md` §6 and `FEATURES.md` already track some product work. This document
covers only what the rendered UI shows, and it supersedes those UI entries where
they overlap.

---

## 2. P0 — defects users hit immediately

### 2.1 Fix 1 — One icon system

`ui/sidebar.py:19-26`, `ui/pages/queue_page.py:208-214`,
`ui/pages/media_page.py:159` mix `⬇ ▶ ♪ ⚙ ▼ 📁 🗑 ✕ ↻`. Mixed Unicode ranges
mean inconsistent weight, baseline, and optical size; emoji code points
(`📁`, `🗑`) render in colour on some platforms and as tofu on others. The
collapsed rail makes this obvious: the active `⬇` reads as a bar next to a
smaller `♪` and `⚙`.

`assets/` already ships `folder.png`, `trash.png`, `refresh.png`,
`player-play.png`, `settings.png`, `moon.png`, `sun.png` — nothing in `ui/` uses
them.

Fix: one icon source. Prefer `QIcon` from bundled SVG at a single design size
(16 at 1x, 24 at 1.5), `Qt.KeepAspectRatio`. If PNG only, ship `@2x` and let
`QIcon` pick by device pixel ratio. Never use emoji as an affordance.

### 2.2 Fix 2 — Two type roles, not one

`ui/theme.py:174` sets `UI_FONT = "Monocraft"` for every string, and
`ui/theme.py:444-448` silently falls back to generic `monospace` when the font
is missing — which is every machine that has not installed it manually.

Monocraft is a pixel/monospace face. It works for the brand mark, numbers,
sizes, speeds, and durations. It reads poorly for multi-line help text, titles,
and status sentences.

Fix: two roles.

| Role | Face | Used for |
|---|---|---|
| `ui` | system UI sans (or bundled Inter / Noto Sans) | titles, labels, help text, buttons |
| `mono` | bundled Monocraft, `tabular-nums` | logo sub, sizes, speeds, ETA, percentages, durations, paths |

Bundle Monocraft in the release build so the identity survives a clean machine.

### 2.3 Fix 3 — Contrast tokens

The shipped palettes were inherited from the Tk prototype and were never
measured. `muted` is used for chips, section labels, empty states, form help, and
the download path; at 15 px effective size, AA requires 4.5:1.

Measured ratio (text on `card`; `sidebar` is within 0.2 of these):

| Token | arisu/dark | arisu/light | Used for |
|---|---|---|---|
| `muted` | **3.17** | **3.76** | chips, help, empty state, section labels |
| `gray_light` | 5.17 | 6.14 | stats, form help |
| `success` | 14.16 | **2.15** | "Completed" status |
| `error` | 6.18 | **3.89** | "Failed" status |
| `warning` | 11.41 | **2.71** | "Paused" status |
| `accent` (as text) | 8.15 | **4.19** | badge, checked pill, active tab |

`saas` and `arch` pass at 4.5 or better on `card`; only `arisu` fails.

Fixed values (all ≥ 4.5 on `card`, `bg`, and `sidebar`):

| Token | arisu/dark | arisu/light |
|---|---|---|
| `muted` | `#9284a6` (5.62) | `#6b5b7e` (6.14) |
| `accent` (text) | `#ff79c6` unchanged (8.15) | `#9c3676` (6.56) |
| `success` | `#50fa7b` unchanged (14.16) | `#1a7f37` (5.08) |
| `error` | `#ff5555` unchanged (6.18) | `#b42323` (6.55) |
| `warning` | `#ffb86c` unchanged (11.41) | `#9a5410` (5.75) |
| `paused` | `#f1fa8c` unchanged | `#7a5c00` (6.25) |
| `info` | `#bd93f9` unchanged | `#6a3fb5` (6.02) |

Dark-mode accents stay vivid; only the light mode needs darkening, because the
dark palette already carries enough luminance.

Add a unit test that asserts every text/background pair used by the QSS is
≥ 4.5:1. `tests/test_theme.py` already imports the tokens, so this is a
table-driven addition, not a new module.

### 2.4 Fix 4 — Disabled controls must look disabled

`ui/theme.py:315` defines `QPushButton:disabled`, but the ID selectors at
`ui/theme.py:316-324` outrank it. `#PrimaryButton` forces
`border-color: transparent` and `#DangerButton` forces `color: $error;
border-color: $error`, so a disabled Start/Stop still reads as active. The
render confirms it: Stop is red-outlined while no run is in progress
(`ui/pages/queue_page.py:389`, `:725`).

Fix: add explicit `:disabled` rules per ID, not one generic rule.

```css
QPushButton#PrimaryButton:disabled {
    background: $bg; color: $muted; border-color: $border;
}
QPushButton#DangerButton:disabled {
    background: transparent; color: $muted; border-color: $border;
}
```

Same class of bug applies to `QPushButton#Pill:checked` versus
`QPushButton:disabled`: add `QPushButton#Pill:disabled`.

### 2.5 Fix 5 — Focus must be visible everywhere

`ui/theme.py:314` gives `QPushButton:focus` a 1 px accent border, but
`#PrimaryButton` sets `border-color: transparent` at the same specificity level
by ID, so the primary action has no focus ring at all. `ui/theme.py:384` sets
`outline: 0` on `QListWidget`, removing the focus rect from both media grids.

Fix:

```css
QPushButton:focus { border: 2px solid $accent; padding: 6px 13px; }
QPushButton#PrimaryButton:focus { border: 2px solid $text; }
QListWidget { outline: 0; }
QListWidget:focus { border: 1px solid $accent; }
```

Keep the padding compensation so the ring does not reflow the row. Do not remove
the ring for aesthetics.

### 2.6 Fix 6 — No horizontal clipping at the shipped scale

`ui/theme.py:247-248` defines `min_window_w: 900`, `min_window_h: 600`, and
`px()` multiplies both by the active scale. At the shipped 1.5, the minimum
window is 1350×900 — larger than the usable width of a 1366-wide laptop once
panel and compositor margins are counted. The queue input row
(`ui/pages/queue_page.py:316-332`) needs roughly 1400 px for URL + Paste + Add,
so "Add to Queue" is clipped and the row action buttons scroll out of reach.

Fix:

- Keep window minimums in device pixels (900×600), not design pixels.
- Let the input row wrap: `QHBoxLayout` cannot wrap, so use a `QVBoxLayout` of
  two rows on narrow widths, or put Paste inside the line edit as an action and
  keep Add as the only trailing button.
- Replace the fixed path label with an elided label (`QFontMetrics.elidedText`)
  and a tooltip carrying the full path.
- Cap queue content width (the prototype uses 980 px) and centre it, so a wide
  monitor does not stretch rows into unreadable lines.

### 2.7 Fix 7 — Keyboard parity

There is no `returnPressed` connection on the URL field (`ui/pages/queue_page.py:318-321`),
no application-level `QShortcut`, no `setTabOrder` call anywhere in `ui/`. A
keyboard user can type a URL and then has no way to submit it.

Fix:

| Key | Action |
|---|---|
| `Enter` in URL field | add to queue |
| `Ctrl+Enter` | start queue |
| `Ctrl+.` | stop queue |
| `Ctrl+F` | focus library search |
| `Delete` | remove selected queue row (with confirm) |
| `Esc` | clear input / dismiss preview |

Also add `QShortcut` for the theme toggle, and surface the hints in the action
row as small `kbd` text. Shortcuts must not fire while a modal dialog is open.

---

## 3. Accessibility

### 3.1 Fix 8 — Validation cannot be colour-only

`ui/pages/queue_page.py:410,414` communicates validity with a green or red input
border and nothing else (WCAG 1.4.1). Add an inline message under the field with
an icon, and set `accessibleDescription` so screen readers receive the same
information:

```
✓ Recognised link — youtube.com
✕ Not a supported link — paste a YouTube or yt-dlp-supported URL
```

Keep the border colour as redundancy, never as the only signal.

### 3.2 Focus order

Rows are rebuilt on every `refresh()` (`ui/pages/queue_page.py:703-715`,
`:752-760`), so a keyboard user's focus is destroyed whenever a download starts,
finishes, or changes state. Reconcile rows by `id(item)` and update in place;
only insert and remove when the set actually changes. This is also the
performance fix — a full rebuild on every progress tick rebuilds widgets that
have not changed.

### 3.3 Names and roles

Icon-only buttons already set `setAccessibleName` (`ui/pages/queue_page.py:221`,
`ui/sidebar.py:83`) — keep that. Add:

- `QProgressBar` accessible name and description (`"Downloading, 43 percent, 2.4 MB/s"`).
- Role/label on the queue row container so a screen reader can announce
  "title, resolution, status" as one unit.
- `QMessageBox` replacements (Fix 20) need `role=status`-equivalent behaviour:
  prefer `QLabel` in a live region or an accessible status bar.

---

## 4. Product surface

### 4.1 Fix 9 — Preview card earns its space

Current preview (`ui/pages/queue_page.py:489-522`) is a card inside a card, shows
a 96×54 thumb with no duration, and quotes `filesize_approx` — the whole-file
size, not the size at the selected resolution.

Fix:

- Inset surface (`$bg` + 1 px border, radius 8) instead of a nested `#Card`.
- Duration badge on the thumbnail, bottom-right, mono.
- "Will download: 1080p MP4 · ~249 MB" computed from `duration` and the
  selected pill; audio-only shows "MP3 · ~23 MB".
- Spinner + disabled Add while the info fetch is in flight.
- Elided single-line title with tooltip.

### 4.2 Fix 10 — Empty states, and no empty section headers

`ui/pages/queue_page.py:287-295` always adds "ACTIVE" and "QUEUE"; the empty
state exists only inside the queue list (`:717-720`), so a fresh install shows
"ACTIVE" above nothing.

Fix: hide a section and its heading when its list is empty; when the whole queue
is empty, show one empty block with an icon, a one-line explanation, and an
"Add a link" button that focuses the URL field. Empty states are not error
states and should not use `error` colour.

### 4.3 Fix 11 — Titles elide, never slice

`ui/pages/queue_page.py:175` truncates at 80 characters with no ellipsis, so a
long title looks like a rendering bug and can still push the action buttons out.
Use `QFontMetrics.elidedText(text, Qt.ElideRight, width)` and set the full text
as tooltip.

### 4.4 Fix 12 — Failed rows explain themselves

`ui/pages/queue_page.py:682-683` logs the reason and renders only a "Failed"
chip. Users see a red dot and no idea what to do. Put the reason inline (single
line, elided, tooltip with the full message) plus a Retry button, and keep the
full text in the log.

### 4.5 Fix 13 — Completed rows have an exit

Completed rows offer "Open folder" only (`ui/pages/queue_page.py:208`), which
opens the directory rather than the file. Add Play (default action on
double-click) and Reveal in file manager. Keep Open folder as the least
prominent of the three.

### 4.6 Fix 14 — Say remove when you mean remove

`ui/pages/queue_page.py:214` labels a trash icon "Delete", but it only removes
the entry from the queue; the file is untouched. `ui/pages/media_page.py:296`
genuinely deletes. Use "Remove" (no trash icon) in the queue and keep the trash
icon for the library.

### 4.7 Fix 15 — Badge only when it counts

`ui/main_window.py:110-122` always shows "0 items" in the top bar. Hide the
badge at zero.

### 4.8 Fix 16 — One persistence model in Settings

Theme changes apply and persist immediately
(`ui/pages/settings_page.py:273-279` → `ui/main_window.py:148-160`), while every
other control waits for the Save button (`ui/pages/settings_page.py:296-299`).
Two mental models in one form.

Fix: autosave every control on change, show a transient "Saved" status, and drop
the Save button. Destructive/irreversible settings only (if any appear later)
get an explicit confirm.

### 4.9 Fix 17 — No dead controls

Three controls currently do nothing:

| Control | Where | Reality |
|---|---|---|
| Auto clipboard + interval | `ui/pages/settings_page.py:157-170` | no poller exists |
| UI scale | `config.py:20`, `main.py:20` | no UI, only read at startup |
| Storage meter | `ui/sidebar.py:209` | `set_storage()` has zero callers |

Either wire them or remove them; a visible dead control costs more trust than a
missing feature.

- Storage: `shutil.disk_usage(download_path)` once on page change and after each
  completed download; label it "Storage" + "14.2 GB free", and note the folder in
  the tooltip. Do not poll on a timer.
- Clipboard: implement the poller described in `PHASES.md` §6.1 or hide both
  controls.
- Scale: expose a 100/125/150 % selector, applied on restart, or remove the
  setting.

### 4.10 Fix 18 — Libraries need sorting and visible actions

`ui/pages/media_page.py:114-116` sorts videos by size descending and music
alphabetically, and shows neither rule. Delete is reachable only from a
right-click menu (`:261-273`); the empty state is a disabled list item
(`:222-226`); the status line is written by two competing code paths
(`:204-206` vs `:226`).

Fix: a sort `QComboBox` (Newest, Oldest, Largest, Name) with a persisted
default; hover-revealed Play / Reveal / Delete on grid cards; a real empty-state
widget; one status line owned by one method ("6 videos · 2.4 GB").

### 4.11 Fix 19 — Motion that carries information

There is no motion anywhere, including the progress bar, which jumps in
discrete steps (`ui/pages/queue_page.py:229`). Add only what communicates state:

- Progress value animates over ~150 ms linear.
- New row fades in over ~120 ms.
- No page transitions, no hover bounce, no decorative motion.

Respect reduced motion. Qt has no portable API for the OS preference; read the
platform hint where available and fall back to a setting in Preferences, or
skip the animations when `ui_scale` is unknown. Keep durations under 200 ms.

### 4.12 Fix 20 — Stop using modals for success and routine information

`ui/pages/queue_page.py:437,558,562,601` open `QMessageBox` for an empty
clipboard, a missing URL, a missing folder, and an empty queue. Reserve modals
for destructive confirmation; everything else becomes an inline banner or status
line. Give the duplicate prompt named buttons ("Add anyway" / "Cancel") instead
of Yes/No (`ui/pages/queue_page.py:567-579`).

---

## 5. Fixes that only exist in code (no prototype marker)

### 5.1 Fix 21 — Persist window geometry and the last page

`ui/main_window.py:53` resizes to a constant every launch; the user's size,
maximised state, and last visited page are lost. Persist `saveGeometry()`,
`saveState()`, and `current_key` in `settings.json`, restore before `show()`,
and clamp to the available screen.

### 5.2 Fix 22 — Reconcile queue rows

As above (§3.2): replace the clear-and-rebuild in `refresh()` with a keyed
update. This preserves focus, avoids flicker, and removes the expensive rebuild
that currently happens on every status change.

### 5.3 Fix 23 — Bundle the fonts and the icon assets

A release build cannot rely on a user-installed Monocraft. Register the bundled
faces with `QFontDatabase.addApplicationFont` at startup and verify the family
actually resolved; log a warning and fall back to the system sans if it did not.

### 5.4 Fix 24 — Ship a version and a single instance

`setApplicationName` is set (`main.py:17`) but no version. Add
`setApplicationVersion` and show it in Settings → About, plus a single-instance
guard so a second launch raises the existing window instead of racing on
`queue.json`. Already tracked in `PHASES.md` §7; listed here so the UI reference
is complete.

---

## 6. Prototype marker map

Open `docs/ui-prototype.html`, click **Fixes**, and every demonstrated region
gains a dashed outline plus its number.

| Marker | Region in the prototype |
|---|---|
| 1 | Sidebar nav, row actions, refresh button — SVG icons |
| 2 | Logo sub, numerals, sizes, paths — mono; everything else sans |
| 3 | Whole app — corrected tokens; light mode status colours |
| 4 | Bottom action row — Stop shown disabled |
| 5 | Tab through the page — visible rings on buttons, pills, inputs, cards |
| 6 | Narrow the window to ~900 px — input row wraps, nothing clips |
| 7 | Focus the URL field, press `Enter`; hint row under the actions |
| 8 | Type a bad URL — inline message, not just a red border |
| 9 | Paste a link — preview with duration badge and live size estimate |
| 10 | Clear the queue — single empty state, no orphan "Active" heading |
| 11 | Long row titles — ellipsis + tooltip |
| 12 | The failed row — reason line + Retry |
| 13 | Completed row — Play / Reveal / Open folder |
| 14 | Queue row action — "Remove", no trash icon |
| 15 | Empty queue — badge disappears from the top bar |
| 16 | Change any setting — "Saved" appears, no Save button |
| 17 | Sidebar storage meter + clipboard description |
| 18 | Videos page — sort control, hover actions, duration badges, count |
| 19 | Start the queue — progress eases; enable reduced motion to stop it |
| 20 | Add, remove, play — status banner, no modal |

Markers 21-24 are code-only and have no prototype representation.

---

## 7. Implementation notes for Qt

Global background leak (`ui/theme.py:257`) — the stripes in the Settings
screenshot come from this rule painting every widget, including containers
inside `#Card`:

```css
/* remove */
QWidget { background: $bg; color: $text; font-size: $size; }

/* replace with */
QMainWindow, #Content, QStackedWidget, QScrollArea { background: $bg; }
QScrollArea > QWidget > QWidget { background: transparent; }
QLabel, QCheckBox { background: transparent; }
```

Elision needs the label widget to know its width; do it in `resizeEvent` or on
every text change, not once at construction.

Icons: build one helper `icon(name) -> QIcon` in `ui/icons.py` (new module only
if it replaces the glyph strings wholesale). Do not scatter absolute paths;
resolve relative to the package root so the frozen build works.

Progress animation: `QPropertyAnimation(self.progress, b"value")` with
`QEasingCurve.Linear`, 150 ms, and a guard that stops a new animation when a new
value arrives faster than the previous one finished.

Contrast test: table-driven over `THEMES`, asserting the token pairs the QSS
actually uses. Keep it in `tests/test_theme.py`; it is a pure function test, no
Qt event loop needed.

---

## 8. Verification

Run these after implementation, not before.

```bash
# behaviour and tokens
yt-env/bin/python -m unittest discover -s tests -t .

# visual check at the shipped scale, both modes
QT_QPA_PLATFORM=offscreen yt-env/bin/python tools/grab_ui.py   # or the ad-hoc grab
```

Acceptance:

1. Offscreen render at 1200×760 shows no horizontal scrollbar on the queue page
   and no clipped "Add to Queue".
2. Settings shows no striped row backgrounds; every row sits on one card surface.
3. With the queue stopped, Stop renders muted with a neutral border.
4. Tab from the URL field reaches Paste, Add, each pill, each row action, and the
   action row; every stop shows a visible ring.
5. `Enter` in the URL field adds the item; the queue updates without rebuilding.
6. A bad URL produces a visible message, not only a red border.
7. Every text/background pair in `THEMES` measures ≥ 4.5:1.
8. Light mode status text (Completed / Failed / Paused) is legible against
   `#ffffff`.
9. Storage meter shows real free space for the configured folder.
10. No control in Settings is inert.

---

## 9. Out of scope

- Redesigning the visual identity or replacing the three theme families.
- Changing download behaviour, format selection, or yt-dlp options.
- Adding new pages or features (playlist policy, DnD, retry policy — those live
  in `FEATURES.md`).
- Packaging, signing, and the engine update path (`PHASES.md` §7).
