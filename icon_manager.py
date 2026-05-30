import os
from PIL import Image
import customtkinter as ctk

# Get the base directory of your project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_PATH = os.path.join(BASE_DIR, "assets")

class IconManager:
    def __init__(self):
        self.icons = {}
        self.load_all_icons()
    
    def load_icon(self, icon_name, size=(20, 20)):
        """Load an icon from the assets folder"""
        icon_file = os.path.join(ASSETS_PATH, f"{icon_name}.png")
        if os.path.exists(icon_file):
            return ctk.CTkImage(
                light_image=Image.open(icon_file),
                dark_image=Image.open(icon_file),
                size=size
            )
        return None
    
    def load_all_icons(self):
        """Load all icons at once"""
        self.icons = {
            # Nav (24x24)
            "queue":              self.load_icon("list-details",        (24, 24)),
            "videos":             self.load_icon("video",               (24, 24)),
            "music":              self.load_icon("music",               (24, 24)),
            "settings":           self.load_icon("settings",            (24, 24)),
            # Actions (20x20)
            "play":               self.load_icon("player-play",         (20, 20)),
            "refresh":            self.load_icon("refresh",             (20, 20)),
            "trash":              self.load_icon("trash",               (20, 20)),
            "folder":             self.load_icon("folder",              (20, 20)),
            "search":             self.load_icon("search",              (20, 20)),
            "download":           self.load_icon("download",            (20, 20)),
            "history":            self.load_icon("history",             (20, 20)),
            # Theme toggle
            "moon":               self.load_icon("moon",                (16, 16)),
            "sun":                self.load_icon("sun",                 (16, 16)),
            # Status / misc
            "check":              self.load_icon("check",               (16, 16)),
            "exclamation":        self.load_icon("exclamation-circle",  (16, 16)),
            "eye":                self.load_icon("eye",                 (16, 16)),
            "clock":              self.load_icon("clock",               (16, 16)),
            "arrow_down":         self.load_icon("arrow-move-down",     (16, 16)),
            "arrow_up":           self.load_icon("arrow-move-up",       (16, 16)),
            # Small variants used in rows
            "play_sm":            self.load_icon("player-play",         (14, 14)),
            "trash_sm":           self.load_icon("trash",               (14, 14)),
            "folder_sm":          self.load_icon("folder",              (14, 14)),
            "video_sm":           self.load_icon("video",               (20, 20)),
            "music_sm":           self.load_icon("music",               (20, 20)),
            "download_sm":        self.load_icon("download",            (20, 20)),
        }

    def get(self, name, size=None):
        """Get an icon by name; pass size to get a freshly-scaled copy."""
        if size:
            # Map friendly names back to file names
            _file_map = {
                "queue": "list-details", "videos": "video", "music": "music",
                "settings": "settings", "play": "player-play", "play_sm": "player-play",
                "refresh": "refresh", "trash": "trash", "trash_sm": "trash",
                "folder": "folder", "folder_sm": "folder", "search": "search",
                "download": "download", "download_sm": "download",
                "history": "history", "moon": "moon", "sun": "sun",
                "check": "check", "exclamation": "exclamation-circle",
                "eye": "eye", "clock": "clock",
                "arrow_down": "arrow-move-down", "arrow_up": "arrow-move-up",
                "video_sm": "video", "music_sm": "music",
            }
            fname = _file_map.get(name, name)
            return self.load_icon(fname, size)
        return self.icons.get(name)

# Create a global instance for easy importing
icon_manager = IconManager()