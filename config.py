RESOLUTIONS = ["144", "240", "360", "480", "720", "1080"]
DEFAULT_PATH = ""
HISTORY_FILE = "history.json"
QUEUE_FILE = "queue.json"
SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "theme": "light",
    "parallel_limit": 2,
    "download_mode": "parallel",
    "auto_clipboard": True,
    "clipboard_interval": 3000,
    "default_resolution": "720",
    "default_audio_only": False
}

THEMES = {  # Changed from THEME to THEMES
    "light": {
        "bg": "#f0f0f0",
        "sidebar_bg": "#e0e0e0",
        "fg": "#000000",
        "button_bg": "#4caf50",
        "button_fg": "#ffffff",
        "entry_bg": "#ffffff",
        "entry_fg": "#000000",
        "progress_bg": "#d3d3d3",
        "selected_bg": "#b0b0b0"
    },
    "dark": {
        "bg": "#2d2d2d",
        "sidebar_bg": "#1e1e1e",
        "fg": "#ffffff",
        "button_bg": "#388e3c",
        "button_fg": "#ffffff",
        "entry_bg": "#3e3e3e",
        "entry_fg": "#ffffff",
        "progress_bg": "#4a4a4a",
        "selected_bg": "#555555"
    }
}