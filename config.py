import os
import shutil
import sys
from pathlib import Path

RESOLUTIONS = ["144", "240", "360", "480", "720", "1080"]
DEFAULT_PATH = ""

APP_VERSION = "1.0.0"
APP_DIR_NAME = "Video-Downloader"
LEGACY_FILES = ("history.json", "queue.json", "settings.json")
DEFAULT_DOWNLOAD_DIR = str(Path.home() / "Downloads")


def _default_data_dir() -> str:
    """Per-user data directory, so the app never writes next to its binary."""
    override = os.environ.get("VIDEO_DOWNLOADER_DATA_DIR")
    if override:
        return str(Path(override).expanduser())
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return str(Path(base) / APP_DIR_NAME)
    if sys.platform == "darwin":
        return str(Path.home() / "Library" / "Application Support" / APP_DIR_NAME)
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return str(Path(base) / "video-downloader")


DATA_DIR = _default_data_dir()
LOG_DIR = os.path.join(DATA_DIR, "logs")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
QUEUE_FILE = os.path.join(DATA_DIR, "queue.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")


def migrate_legacy_files(directory: str = "") -> list[str]:
    """Copy any cwd-era JSON state into the data directory.

    Only files that are missing in ``directory`` are copied, so an existing
    data directory always wins and repeated starts are a no-op.
    """
    target_dir = Path(directory or DATA_DIR)
    migrated: list[str] = []
    for name in LEGACY_FILES:
        source = Path(name)
        target = target_dir / name
        if source.is_file() and not target.exists():
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            except OSError:
                continue
            migrated.append(name)
    return migrated

DEFAULT_SETTINGS = {
    "theme": "dark",  # Colour mode: "dark" or "light"
    "theme_family": "arisu",  # Palette: "arisu", "saas" or "arch"
    "parallel_limit": 2,
    "download_mode": "parallel",
    "auto_clipboard": True,
    "clipboard_interval": 3000,
    "default_resolution": "720",
    "default_audio_only": False,
    "download_path": DEFAULT_DOWNLOAD_DIR,
    "cookie_method": "none",  # Options: "none", "browser", "file"
    "cookie_browser": "chrome",  # Options: "chrome", "firefox", "edge", "brave", "opera", "safari"
    "cookie_file_path": "",  # Path to cookies.txt file
    "ui_scale": 1.5,  # UI scale: 1.0 = original design size, 1.5 = 50% larger
    "sidebar_collapsed": False  # Icon-only sidebar rail
}

# These are now just for reference - CustomTkinter custom theme handles colors
THEMES = {
    "light": {
        "bg": "#F2F5F3",
        "sidebar_bg": "#E8EDE9",
        "fg": "#1A2E28",
        "button_bg": "#2BB2A9",
        "button_fg": "#1A2E28",
        "entry_bg": "#E8EDE9",
        "entry_fg": "#1A2E28",
        "progress_bg": "#C9D4CB",
        "selected_bg": "#A8D8D5"
    },
    "dark": {
        "bg": "#000103",
        "sidebar_bg": "#0F3029",
        "fg": "#FFFFFF",
        "button_bg": "#2BB2A9",
        "button_fg": "#FFFFFF",
        "entry_bg": "#0F3029",
        "entry_fg": "#FFFFFF",
        "progress_bg": "#1B7774",
        "selected_bg": "#2BB2A9"
    }
}
