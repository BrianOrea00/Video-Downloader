# Sessions

## Phase 8 — PySide6 port (done)
Sub-steps:
1. Core: `models.py`, `persistence.py`, `queue_manager.py`, `pyproject.toml`, `tests/`.
2. Skeleton: `ui/theme.py`, `ui/sidebar.py`, `ui/main_window.py`, pages package, new `main.py`.
3. Download Console: `queue_runner.py`, `ui/pages/queue_page.py` (preview, pills, rows, start/stop, dup check, history).
4. Media: `thumb_cache.py`, `ui/pages/media_page.py` + videos/music pages.
5. Settings form: `ui/pages/settings_page.py`.
6. Theme switch + 7. link preview: delivered within theme.py / queue_page.
8. Deleted 7 Tk modules; updated `requirements.txt`, `README.md`, `.gitignore`.

Verification: `yt-env/bin/python -m unittest discover -s tests -t .` (26 tests OK); py_compile OK; offscreen integration (stub downloader) + smoke (nav, scan=2 video/1 music, settings save) pass. Screenshots matched `docs/ui-prototype.html`.

Env: `yt-env` (Python 3.13), PySide6 6.12.0 installed. Run app offscreen: `QT_QPA_PLATFORM=offscreen yt-env/bin/python main.py`.
