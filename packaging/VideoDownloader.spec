# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller one-dir spec.

One-dir, not one-file: a single-file build re-extracts ~200 MB on every launch,
trips antivirus heuristics and breaks `.part` resume when the temp folder is
cleaned. Build with:

    python -m PyInstaller --noconfirm packaging/VideoDownloader.spec

The yt-dlp package ships its own PyInstaller hook, which collects its data
files and hidden imports; do not hand-maintain `hiddenimports` for it.
"""
import sys

from PyInstaller.utils.hooks import collect_data_files

datas = [("assets", "assets")]
datas += collect_data_files("yt_dlp")

# The app imports only QtCore/QtGui/QtWidgets. Excluding the rest keeps the
# bundle ~120-180 MB instead of ~670 MB, and prevents Accelerate's dependency
# scan from pulling in WebEngine on machines that have the full wheel.
excludes = [
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQml",
    "PySide6.Qt3DCore",
    "PySide6.QtCharts",
    "PySide6.QtDesigner",
    "PySide6.QtMultimedia",
    "PySide6.QtNetworkAuth",
    "PySide6.QtPdf",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtWebSockets",
    "tkinter",
    "unittest",
]

icon = "assets/appicon.ico" if sys.platform == "win32" else "assets/appicon.png"

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="video-downloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # windowed: stderr is invisible, logger.py handles it
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="video-downloader",
)
