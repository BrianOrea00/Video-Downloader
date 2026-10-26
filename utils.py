import os
import shutil
import subprocess
import sys


def resource_path(relative: str) -> str:
    """Absolute path to a bundled resource, from source or a frozen build."""
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative)


def ffmpeg_available() -> bool:
    """True when an ffmpeg binary is on PATH.

    Audio extraction and MP4 merging both fail without it, so the UI disables
    those choices instead of letting a download fail later.
    """
    return shutil.which("ffmpeg") is not None


def detect_vlc() -> str | None:
    """Auto-detect the VLC executable, or return ``None``."""
    if sys.platform == "win32":
        common_paths = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        ]
    elif sys.platform == "darwin":
        common_paths = ["/Applications/VLC.app/Contents/MacOS/VLC"]
    else:
        common_paths = ["/usr/bin/vlc", "/usr/local/bin/vlc"]

    for path in common_paths:
        if os.path.exists(path):
            return path

    try:
        result = subprocess.run(
            ["which", "vlc"], capture_output=True, text=True, check=False,
        )
    except OSError:
        return None
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None
