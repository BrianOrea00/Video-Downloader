RESOLUTIONS = ["144", "240", "360", "480", "720", "1080"]
DEFAULT_PATH = ""
HISTORY_FILE = "history.json"
QUEUE_FILE = "queue.json"
SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "theme": "dark",  # Changed to dark as default (your dark palette is primary)
    "parallel_limit": 2,
    "download_mode": "parallel",
    "auto_clipboard": True,
    "clipboard_interval": 3000,
    "default_resolution": "720",
    "default_audio_only": False,
    "download_path": ""
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