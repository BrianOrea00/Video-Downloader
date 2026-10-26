# Third-party notices

Video Downloader is distributed under the **GNU General Public License v3.0 or
later** (see `LICENSE`). It builds on the following components. This file is a
summary; the licence text of each component governs where it differs.

## Bundled or linked at runtime

| Component | Version | Licence | Notes |
|-----------|---------|---------|-------|
| [Qt for Python (PySide6-Essentials)](https://pypi.org/project/PySide6-Essentials/) | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0 | This application is GPL-3.0-or-later, so the GPL-3 terms apply and the LGPL relinking obligation does not. Qt is used as shipped in the PySide6 wheel, unmodified. |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | 2026.8.19 | Unlicense | Engine used for metadata and downloads. |
| [mutagen](https://github.com/quodlibet/mutagen) | 1.47.0 | GPL-2.0-or-later | Reads music tags and durations. This dependency is what makes the project GPL rather than permissive. |
| [Tabler Icons](https://tabler.io/icons) | MIT © 2020-2026 Paweł Kuna | MIT | The PNG glyphs in `assets/` are unmodified Tabler outline icons, tinted at runtime. Full MIT text below. |
| [Monocraft](https://github.com/IdreesInc/Monocraft) | © 2022 Idrees Hassan | SIL Open Font License 1.1 | Bundled unmodified as `assets/fonts/Monocraft.ttf`; the full OFL text ships in `assets/fonts/OFL.txt`. |
| [Pillow](https://python-pillow.org/) | 12.2.0 | MIT-CMU | Build-time only: produces `assets/appicon.ico` from the PNG. Not imported at runtime. |

## Required but not bundled

| Component | Licence | Notes |
|-----------|---------|-------|
| [FFmpeg](https://ffmpeg.org/) | LGPL-2.1-or-later or GPL-2.0-or-later depending on the build | Audio extraction (`FFmpegExtractAudio`) and MP4 merging call the `ffmpeg` binary found on `PATH`. The project does not distribute FFmpeg; if you ship a build that bundles it, check that build's licence flags (`--enable-gpl`, `--enable-nonfree`). |
| [Python](https://www.python.org/) | PSF-2.0 | Interpreter. |
| yt-dlp default extras (`certifi`, `requests`, `urllib3`, `brotli`, `websockets`, `pycryptodomex`, `yt-dlp-ejs`) | MIT / Apache-2.0 / BSD / ISC (per package) | Installed through `yt-dlp[default]`; see each package's metadata for the exact text. |

## Tabler Icons — MIT licence

```
MIT License

Copyright (c) 2020-2026 Paweł Kuna

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Source code

Because the application is GPL-3.0-or-later, a binary distribution must be
accompanied by the corresponding source. The source lives at
<https://github.com/BrianOrea00/Video-Downloader>; release archives include it.
