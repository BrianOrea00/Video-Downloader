import tkinter as tk
from tkinter import ttk, messagebox
from config import THEMES  # Changed from THEME to THEMES
from utils import load_settings, save_settings, detect_vlc
from queue_tab import QueueTab
from videos_tab import VideosTab
from music_tab import MusicTab
from settings_tab import SettingsTab

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Downloader")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Load settings
        self.settings = load_settings()
        self.current_theme = self.settings.get("theme", "light")
        
        # Detect VLC
        self.vlc_path = detect_vlc()
        if not self.vlc_path:
            print("Warning: VLC not found. Media playback will be disabled.")
        
        # Current active tab
        self.current_tab = None
        
        # Build UI
        self.build_ui()
        
        # Apply theme
        self.apply_theme()
        
        # Start clipboard checking if enabled
        if self.settings.get("auto_clipboard", True):
            self.root.after(1000, self.check_clipboard)
        
        # Set download path from settings if exists
        if self.settings.get("download_path"):
            self.queue_tab.path_var.set(self.settings["download_path"])
    
    def build_ui(self):
        """Build the main UI with sidebar and content area"""
        # Main container
        self.main_container = tk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create sidebar frame
        self.sidebar = tk.Frame(self.main_container, width=200, relief=tk.RAISED, bd=1)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=0, pady=0)
        self.sidebar.pack_propagate(False)
        
        # Create content frame
        self.content_frame = tk.Frame(self.main_container)
        self.content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top bar with theme toggle
        self.top_bar = tk.Frame(self.content_frame)
        self.top_bar.pack(fill=tk.X, pady=(0, 10))
        
        self.title_label = tk.Label(self.top_bar, text="Video Downloader", font=('Arial', 16, 'bold'))
        self.title_label.pack(side=tk.LEFT)
        
        self.theme_btn = tk.Button(
            self.top_bar, 
            text="🌙 Dark Mode" if self.current_theme == "light" else "☀️ Light Mode",
            command=self.toggle_theme,
            width=12
        )
        self.theme_btn.pack(side=tk.RIGHT, padx=5)
        
        # Build sidebar buttons
        self.build_sidebar()
        
        # Initialize tabs
        self.queue_tab = QueueTab(self.content_frame, self)
        self.videos_tab = VideosTab(self.content_frame, self)
        self.music_tab = MusicTab(self.content_frame, self)
        self.settings_tab = SettingsTab(self.content_frame, self)
        
        # Hide all tabs initially
        self.queue_tab.hide()
        self.videos_tab.hide()
        self.music_tab.hide()
        self.settings_tab.hide()
        
        # Show default tab (Queue)
        self.show_tab("queue")
    
    def build_sidebar(self):
        """Create sidebar navigation buttons"""
        # App logo/title in sidebar
        logo_label = tk.Label(
            self.sidebar, 
            text="📥\nDownloader", 
            font=('Arial', 14, 'bold'),
            pady=20
        )
        logo_label.pack(fill=tk.X)
        
        # Navigation buttons
        buttons = [
            ("⏯️ Queue", "queue"),
            ("📹 Videos", "videos"),
            ("🎵 Music", "music"),
            ("⚙️ Settings", "settings")
        ]
        
        self.nav_buttons = {}
        for text, tab_name in buttons:
            btn = tk.Button(
                self.sidebar,
                text=text,
                font=('Arial', 11),
                pady=10,
                command=lambda t=tab_name: self.show_tab(t),
                relief=tk.FLAT
            )
            btn.pack(fill=tk.X, padx=10, pady=5)
            self.nav_buttons[tab_name] = btn
    
    def show_tab(self, tab_name):
        """Show selected tab and hide others"""
        # Update button styles - removed bg='' which was causing error
        for name, btn in self.nav_buttons.items():
            btn.config(relief=tk.FLAT)
            # Don't set bg to empty string, use default or theme color
            if hasattr(self, 'current_theme'):
                theme = THEMES[self.current_theme]
                btn.config(bg=theme["sidebar_bg"], fg=theme["fg"])
        
        if tab_name in self.nav_buttons:
            self.nav_buttons[tab_name].config(relief=tk.SUNKEN)
        
        # Hide all tabs
        self.queue_tab.hide()
        self.videos_tab.hide()
        self.music_tab.hide()
        self.settings_tab.hide()
        
        # Show selected tab
        if tab_name == "queue":
            self.queue_tab.show()
            self.title_label.config(text="📥 Download Queue")
            # Refresh queue display
            self.queue_tab.refresh_queue_display()
        elif tab_name == "videos":
            self.videos_tab.show()
            self.title_label.config(text="📹 Video Library")
            # Refresh video list
            self.videos_tab.refresh_list()
        elif tab_name == "music":
            self.music_tab.show()
            self.title_label.config(text="🎵 Music Library")
            # Refresh music list
            self.music_tab.refresh_list()
        elif tab_name == "settings":
            self.settings_tab.show()
            self.title_label.config(text="⚙️ Settings")
        
        self.current_tab = tab_name
    
    def toggle_theme(self):
        """Toggle between light and dark themes"""
        if self.current_theme == "light":
            self.current_theme = "dark"
            self.theme_btn.config(text="☀️ Light Mode")
        else:
            self.current_theme = "light"
            self.theme_btn.config(text="🌙 Dark Mode")
        
        self.settings["theme"] = self.current_theme
        save_settings(self.settings)
        self.apply_theme()
    
    def apply_theme(self):
        """Apply current theme colors to all widgets"""
        theme = THEMES[self.current_theme]
        
        # Apply to root window
        self.root.configure(bg=theme["bg"])
        
        # Apply to main container
        self.main_container.configure(bg=theme["bg"])
        
        # Apply to sidebar
        self.sidebar.configure(bg=theme["sidebar_bg"])
        
        # Apply to content frame
        self.content_frame.configure(bg=theme["bg"])
        
        # Apply to top bar
        self.top_bar.configure(bg=theme["bg"])
        self.title_label.configure(bg=theme["bg"], fg=theme["fg"])
        self.theme_btn.configure(bg=theme["button_bg"], fg=theme["button_fg"])
        
        # Apply to sidebar buttons
        for btn in self.nav_buttons.values():
            btn.configure(bg=theme["sidebar_bg"], fg=theme["fg"])
        
        # Apply to tabs
        if hasattr(self, 'queue_tab'):
            self.queue_tab.apply_theme(theme)
            self.videos_tab.apply_theme(theme)
            self.music_tab.apply_theme(theme)
            self.settings_tab.apply_theme(theme)
    
    def check_clipboard(self):
        """Auto-detect URLs from clipboard"""
        if not self.settings.get("auto_clipboard", True):
            self.root.after(3000, self.check_clipboard)
            return
        
        try:
            text = self.root.clipboard_get()
            if "http" in text or "youtu" in text:
                # Only auto-fill if queue tab is showing and url entry exists
                if self.current_tab == "queue":
                    self.queue_tab.url_var.set(text)
        except:
            pass
        
        interval = self.settings.get("clipboard_interval", 3000)
        self.root.after(interval, self.check_clipboard)
    
    def on_download_complete(self):
        """Called when a download completes - refresh library tabs"""
        if self.current_tab == "videos":
            self.videos_tab.refresh_list()
        elif self.current_tab == "music":
            self.music_tab.refresh_list()