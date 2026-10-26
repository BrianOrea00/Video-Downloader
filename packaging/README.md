# Packaging

Everything here is for building a distributable copy. The application itself
never reads these files at runtime; only `assets/` is bundled.

## PyInstaller (one-dir)

```bash
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm packaging/VideoDownloader.spec
```

The result is `dist/video-downloader/` (Windows: `video-downloader.exe` inside).
One-dir is deliberate: a one-file build re-extracts the whole bundle on every
start, trips antivirus heuristics and breaks `.part` resume when the temp folder
is cleared.

Things that must hold before shipping a build:

- `ffmpeg` is either on the user's `PATH` or bundled and passed with
  `ffmpeg_location`; without it audio-only and MP4 merging are disabled in the
  UI.
- The `assets/` folder (icons, `appicon.*`, `fonts/Monocraft.ttf` + `OFL.txt`)
  is inside the bundle. `utils.resource_path()` resolves it under `_MEIPASS`.
- `LICENSE` and `THIRD_PARTY_NOTICES.md` ship beside the binary.

Builds are not reproducible across operating systems; PyInstaller cannot
cross-compile. Build each target on its own runner.

## Linux

| File | Install to |
|------|------------|
| `video-downloader.desktop` | `/usr/share/applications/` |
| `video-downloader.metainfo.xml` | `/usr/share/metainfo/` |
| `../assets/appicon.png` | `/usr/share/icons/hicolor/512x512/apps/video-downloader.png` |

`Icon=video-downloader` in the desktop file resolves through that icon name, and
`app.setDesktopFileName("video-downloader")` makes the window match the entry.

For an AppImage, place the same three files inside the AppDir
(`usr/share/applications`, `usr/share/metainfo`, `usr/share/icons/hicolor/...`)
plus an `AppRun` that execs `usr/bin/video-downloader`, and a symlink
`video-downloader.desktop` at the AppDir root. Publish a SHA256 alongside.

## Windows

Build the one-dir bundle on a Windows runner, then package it with an Inno Setup
script installed per-user under `%LOCALAPPDATA%`. Unsigned executables trigger
SmartScreen; only an OV/EV code-signing certificate removes that warning.

## macOS

`pyinstaller packaging/VideoDownloader.spec` produces a `.app`; wrap it in a
`.dmg`, then sign with a Developer ID and notarize (hardened runtime). No
build exists yet, so none of the `os.startfile`/`open` branches have been
exercised on Windows or macOS.
