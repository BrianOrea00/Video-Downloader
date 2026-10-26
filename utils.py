import hashlib
import os
import re
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

_URL_RE = re.compile(r"https?://[^\s'\"<>)\]]+", re.IGNORECASE)


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


def redact_url(url: str) -> str:
    """Host plus a short fingerprint instead of the full URL.

    Logs are meant to be shareable, so a downloaded video's identity must not
    be in them, while a fingerprint still lets two lines be correlated.
    """
    try:
        parts = urlsplit(url if "://" in url else "https://" + url)
    except ValueError:
        return "unparsed-url"
    host = parts.hostname or "unknown-host"
    digest = hashlib.sha256(url.encode("utf-8", "replace")).hexdigest()[:8]
    return f"{host}#{digest}"


def redact_text(text: str) -> str:
    """Redact every URL and the home directory in a log or error message."""
    if not text:
        return text
    redacted = _URL_RE.sub(lambda match: redact_url(match.group(0)), text)
    home = os.path.expanduser("~")
    if home and home != "~":
        redacted = redacted.replace(home, "~")
    return redacted


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
