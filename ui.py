import customtkinter as ctk
from tkinter import messagebox
from utils import load_settings, save_settings, detect_vlc
from queue_tab import QueueTab
from videos_tab import VideosTab
from music_tab import MusicTab
from settings_tab import SettingsTab
from icon_manager import icon_manager
from theme_manager import theme_manager
import subprocess
import os

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Downloader")
        self.root.geometry("1200x700")
        self.root.minsize(900, 600)
        
        # Load settings
        self.settings = load_settings()
        self.current_theme = self.settings.get("theme", "dark")
        
        # Set CustomTkinter appearance mode
        ctk.set_appearance_mode(self.current_theme)
        
        # Apply custom theme
        theme_manager.apply_custom_theme()
        
        # Detect VLC
        self.vlc_path = detect_vlc()
        if not self.vlc_path:
            print("Warning: VLC not found. Media playback will be disabled.")
        
        # Current active tab
        self.current_tab = None
        self.last_clipboard = ""
        
        # Build UI
        self.build_ui()
        
        # Start clipboard checking
        self.root.after(1000, self.check_clipboard)
        
        # Set download path from settings if exists
        if self.settings.get("download_path"):
            self.queue_tab.path_var.set(self.settings["download_path"])
    
    def get_clipboard_text(self):
        """Read clipboard robustly for WSL, native Linux, and Windows."""
        try:
            result = subprocess.run(
                ['powershell.exe', '-NoProfile', '-Command', 'Get-Clipboard'],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

        try:
            text = self.root.clipboard_get()
            if text and text.strip():
                return text.strip()
        except Exception:
            pass

        try:
            result = subprocess.run(
                ['xclip', '-selection', 'clipboard', '-o'],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

        try:
            result = subprocess.run(
                ['xsel', '--clipboard', '--output'],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

        return None
    
    def check_clipboard(self):
        """Auto-detect URLs from clipboard if enabled"""
        if self.settings.get("auto_clipboard", True):
            text = self.get_clipboard_text()
            if text and text != self.last_clipboard:
                if "youtube.com" in text or "youtu.be" in text:
                    self.last_clipboard = text
                    self.queue_tab.url_var.set(text)
                    self.queue_tab.preview()
        self.root.after(self.settings.get("clipboard_interval", 3000), self.check_clipboard)
    
    def build_ui(self):
        """Build the main UI with sidebar and content area"""
        # Main container frame
        self.main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True)
        
        # Create sidebar frame
        self.sidebar = ctk.CTkFrame(
            self.main_container, 
            width=240, 
            corner_radius=0,
            fg_color=theme_manager.get_color("surface")
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        # Right border for sidebar
        sidebar_border = ctk.CTkFrame(
            self.sidebar, 
            height=2, 
            fg_color=theme_manager.get_color("border"),
            corner_radius=0
        )
        sidebar_border.pack(side="right", fill="y", padx=(0, 0), pady=0)
        sidebar_border.configure(width=1)
        
        # Create content frame
        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_frame.pack(side="left", fill="both", expand=True, padx=20, pady=16)
        
        # Top bar
        self.top_bar = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.top_bar.pack(fill="x", pady=(0, 16))
        
        # Bottom border for top bar
        top_border = ctk.CTkFrame(self.top_bar, height=1, fg_color=theme_manager.get_color("border"), corner_radius=0)
        top_border.pack(side="bottom", fill="x", pady=(8, 0))
        
        self.title_label = ctk.CTkLabel(
            self.top_bar, 
            text="Download Queue", 
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=theme_manager.get_color("text_primary")
        )
        self.title_label.pack(side="left")
        
        # Right side top bar items
        top_right = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        top_right.pack(side="right")
        
        # Badge for item count
        self.count_badge = ctk.CTkFrame(
            top_right, 
            fg_color=theme_manager.get_color("surface"),
            border_width=1,
            border_color=theme_manager.get_color("mid"),
            corner_radius=4
        )
        self.count_badge.pack(side="left", padx=(0, 10))
        
        self.count_label = ctk.CTkLabel(
            self.count_badge, 
            text="0 items", 
            font=ctk.CTkFont(size=11),
            text_color=theme_manager.get_color("accent")
        )
        self.count_label.pack(padx=8, pady=2)
        
        _theme_icon = icon_manager.get("sun") if self.current_theme == "light" else icon_manager.get("moon")
        _theme_text = "Dark Mode" if self.current_theme == "light" else "Light Mode"
        self.theme_btn = ctk.CTkButton(
            top_right, 
            text=_theme_text,
            image=_theme_icon,
            compound="left",
            fg_color=theme_manager.get_color("surface"),
            border_width=1,
            border_color=theme_manager.get_color("border"),
            text_color=theme_manager.get_color("muted"),
            hover_color=theme_manager.get_color("card"),
            command=self.toggle_theme,
            width=130,
            height=32,
            corner_radius=6
        )
        self.theme_btn.pack(side="left")
        
        # Build sidebar
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
        """Create sidebar navigation buttons with icons - Compact responsive version"""
        # Logo block - reduce top padding
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=16, pady=(16, 8))
        
        icon_label = ctk.CTkLabel(
            logo_frame, 
            text="",
            image=icon_manager.get("download", size=(20, 20)),  # Smaller icon
            width=24,
            height=24
        )
        icon_label.pack(side="left", padx=(0, 8))
        
        logo_text_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
        logo_text_frame.pack(side="left")
        
        title_label = ctk.CTkLabel(
            logo_text_frame, 
            text="Downloader", 
            font=ctk.CTkFont(size=13, weight="bold"),  # Smaller font
            text_color=theme_manager.get_color("text_primary")
        )
        title_label.pack(anchor="w")
        
        subtitle_label = ctk.CTkLabel(
            logo_text_frame, 
            text="yt-dlp", 
            font=ctk.CTkFont(size=10),  # Smaller font
            text_color=theme_manager.get_color("muted")
        )
        subtitle_label.pack(anchor="w")
        
        # Divider - reduced padding
        divider = ctk.CTkFrame(self.sidebar, height=1, fg_color=theme_manager.get_color("border"), corner_radius=0)
        divider.pack(fill="x", padx=16, pady=(8, 8))
        
        # Library section - tighter
        library_label = ctk.CTkLabel(
            self.sidebar, 
            text="LIBRARY", 
            font=ctk.CTkFont(size=9),  # Smaller font
            text_color=theme_manager.get_color("secondary")
        )
        library_label.pack(anchor="w", padx=16, pady=(0, 4))
        
        # Navigation buttons - compact spacing
        nav_items = [
            (icon_manager.get("queue"), "Queue", "queue"),
            (icon_manager.get("videos"), "Videos", "videos"),
            (icon_manager.get("music"), "Music", "music"),
        ]
        
        self.nav_buttons = {}
        self.nav_frames = {}
        
        for icon, text, tab_name in nav_items:
            btn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=32)
            btn_frame.pack(fill="x", padx=12, pady=1)
            btn_frame.pack_propagate(False)
            
            # Active indicator
            indicator = ctk.CTkFrame(
                btn_frame, 
                width=3, 
                fg_color="transparent",
                corner_radius=0
            )
            indicator.pack(side="left", fill="y", padx=(0, 0))
            
            btn = ctk.CTkButton(
                btn_frame,
                text=text,
                image=icon,
                compound="left",
                font=ctk.CTkFont(size=12),  # Smaller font
                height=28,  # Reduced from 32 to 28
                corner_radius=6,
                fg_color="transparent",
                anchor="w",
                hover_color="#1B4A3A",
                command=lambda t=tab_name: self.show_tab(t)
            )
            btn.pack(side="left", fill="x", expand=True)
            
            self.nav_buttons[tab_name] = btn
            self.nav_frames[tab_name] = (btn_frame, indicator)
        
        # System section divider - tighter
        sys_divider = ctk.CTkFrame(self.sidebar, height=1, fg_color=theme_manager.get_color("border"), corner_radius=0)
        sys_divider.pack(fill="x", padx=16, pady=(12, 6))
        
        system_label = ctk.CTkLabel(
            self.sidebar, 
            text="SYSTEM", 
            font=ctk.CTkFont(size=9),  # Smaller font
            text_color=theme_manager.get_color("secondary")
        )
        system_label.pack(anchor="w", padx=16, pady=(0, 4))
        
        # Settings button - compact
        settings_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=32)
        settings_frame.pack(fill="x", padx=12, pady=1)
        settings_frame.pack_propagate(False)
        
        settings_indicator = ctk.CTkFrame(
            settings_frame, 
            width=3, 
            fg_color="transparent",
            corner_radius=0
        )
        settings_indicator.pack(side="left", fill="y")
        
        settings_btn = ctk.CTkButton(
            settings_frame,
            text="Settings",
            image=icon_manager.get("settings"),
            compound="left",
            font=ctk.CTkFont(size=12),  # Consistent font
            height=28,  # Reduced to match nav buttons
            corner_radius=6,
            fg_color="transparent",
            anchor="w",
            hover_color="#1B4A3A",
            command=lambda: self.show_tab("settings")
        )
        settings_btn.pack(side="left", fill="x", expand=True)
        
        self.nav_buttons["settings"] = settings_btn
        self.nav_frames["settings"] = (settings_frame, settings_indicator)
        
        # Storage bar at bottom - make more compact
        storage_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        storage_frame.pack(side="bottom", fill="x", padx=16, pady=(0, 12))
        
        storage_header = ctk.CTkFrame(storage_frame, fg_color="transparent")
        storage_header.pack(fill="x", pady=(0, 4))
        
        storage_label = ctk.CTkLabel(
            storage_header, 
            text="Storage", 
            font=ctk.CTkFont(size=10),
            text_color=theme_manager.get_color("greige")
        )
        storage_label.pack(side="left")
        
        self.storage_used_label = ctk.CTkLabel(
            storage_header, 
            text="0 GB", 
            font=ctk.CTkFont(size=10),
            text_color=theme_manager.get_color("greige")
        )
        self.storage_used_label.pack(side="right")
        
        storage_track = ctk.CTkFrame(
            storage_frame, 
            height=3,  # Smaller height
            fg_color=theme_manager.get_color("border"),
            corner_radius=2
        )
        storage_track.pack(fill="x")
        
        self.storage_progress = ctk.CTkFrame(
            storage_track, 
            height=3,  # Smaller height
            fg_color=theme_manager.get_color("accent"),
            corner_radius=2,
            width=0
        )
        self.storage_progress.pack(side="left")
    
    def update_storage(self, path, total_bytes=0):
        """Update storage bar display"""
        if path and os.path.exists(path):
            try:
                total = 0
                for f in os.listdir(path):
                    fpath = os.path.join(path, f)
                    if os.path.isfile(fpath):
                        total += os.path.getsize(fpath)
                
                gb = total / (1024**3)
                self.storage_used_label.configure(text=f"{gb:.1f} GB")
                
                # Mock max of 100GB for progress bar
                percent = min(gb / 100, 1.0)
                parent = self.storage_progress.master
                parent.update_idletasks()
                width = parent.winfo_width() * percent
                self.storage_progress.configure(width=max(2, width))
            except:
                pass
    
    def show_tab(self, tab_name):
        """Show selected tab and hide others"""
        # Update button styles
        accent_color = theme_manager.get_color("accent")
        bg_color = theme_manager.get_color("surface")
        
        for name, (frame, indicator) in self.nav_frames.items():
            if name == tab_name:
                btn = self.nav_buttons[name]
                btn.configure(fg_color=accent_color, text_color="#FFFFFF")
                indicator.configure(fg_color="#FFFFFF")
            else:
                btn = self.nav_buttons[name]
                btn.configure(fg_color="transparent", text_color=theme_manager.get_color("text_primary"))
                indicator.configure(fg_color="transparent")
        
        # Hide all tabs
        self.queue_tab.hide()
        self.videos_tab.hide()
        self.music_tab.hide()
        self.settings_tab.hide()
        
        # Show selected tab
        if tab_name == "queue":
            self.queue_tab.show()
            self.title_label.configure(text="Download Queue")
            self.queue_tab.refresh_queue_display()
            self.queue_tab.update_stats_display()
        elif tab_name == "videos":
            self.videos_tab.show()
            self.title_label.configure(text="Video Library")
            self.videos_tab.refresh_list()
        elif tab_name == "music":
            self.music_tab.show()
            self.title_label.configure(text="Music Library")
            self.music_tab.refresh_list()
        elif tab_name == "settings":
            self.settings_tab.show()
            self.title_label.configure(text="Settings")
        
        self.current_tab = tab_name
    
    def update_count_badge(self, count):
        """Update the count badge in top bar"""
        self.count_label.configure(text=f"{count} items")
    
    def toggle_theme(self):
        """Toggle theme by rebuilding the entire UI with new colors."""
        # 1. Flip the theme value and persist it
        if self.current_theme == "light":
            self.current_theme = "dark"
        else:
            self.current_theme = "light"

        self.settings["theme"] = self.current_theme
        save_settings(self.settings)

        # 2. Snapshot state we want to survive the rebuild
        saved_tab      = self.current_tab or "queue"
        saved_path     = self.queue_tab.path_var.get() if hasattr(self, "queue_tab") else ""
        saved_queue    = list(self.queue_tab.queue)    if hasattr(self, "queue_tab") else []
        saved_url      = self.queue_tab.url_var.get()  if hasattr(self, "queue_tab") else ""

        # 3. Switch CTk appearance mode and reapply palette
        ctk.set_appearance_mode(self.current_theme)
        theme_manager.apply_custom_theme()

        # 4. Tear down the old UI
        self.main_container.destroy()

        # 5. Rebuild everything from scratch
        self.current_tab = None
        self.build_ui()

        # 6. Restore state
        if saved_path:
            self.queue_tab.path_var.set(saved_path)
            self.queue_tab.path_label.configure(
                text=saved_path,
                text_color=theme_manager.get_color("text_primary")
            )
        if saved_queue:
            self.queue_tab.queue = saved_queue
            self.queue_tab.refresh_queue_display()
        if saved_url:
            self.queue_tab.url_var.set(saved_url)

        self.show_tab(saved_tab)
    
    def on_download_complete(self):
        """Called when a download completes - refresh library tabs"""
        if hasattr(self, 'current_tab'):
            if self.current_tab == "videos":
                self.videos_tab.refresh_list()
            elif self.current_tab == "music":
                self.music_tab.refresh_list()
        
        # Update storage
        if hasattr(self, 'queue_tab') and hasattr(self.queue_tab, 'path_var'):
            self.update_storage(self.queue_tab.path_var.get())