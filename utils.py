import json
import os
from config import HISTORY_FILE, QUEUE_FILE, SETTINGS_FILE, DEFAULT_SETTINGS

def save_history(data):
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w") as f:
            json.dump([], f)

    with open(HISTORY_FILE, "r+") as f:
        history = json.load(f)
        history.append(data)
        f.seek(0)
        json.dump(history, f, indent=4)

def clean_filename(name):
    return "".join(c for c in name if c not in r'\/:*?"<>|')

def load_queue():
    """Load queue from JSON file"""
    if not os.path.exists(QUEUE_FILE):
        return []
    try:
        with open(QUEUE_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_queue(queue):
    """Save queue to JSON file"""
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=4)

def load_settings():
    """Load settings from JSON file"""
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except:
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Save settings to JSON file"""
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)

def detect_vlc():
    """Auto-detect VLC executable path"""
    import sys
    import subprocess
    
    common_paths = []
    
    if sys.platform == "win32":
        common_paths = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        ]
    elif sys.platform == "darwin":  # macOS
        common_paths = [
            "/Applications/VLC.app/Contents/MacOS/VLC",
        ]
    else:  # Linux
        common_paths = [
            "/usr/bin/vlc",
            "/usr/local/bin/vlc",
        ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    # Try to find in PATH
    try:
        result = subprocess.run(['which', 'vlc'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    return None