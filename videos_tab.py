import customtkinter as ctk
from tkinter import messagebox
import os
import subprocess
from datetime import datetime
from icon_manager import icon_manager
from theme_manager import theme_manager


class VideosTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.current_files = []
        self.vlc_path = None
        self.empty_state = None  # Initialize as None
        
        self.build_ui()
    
    def build_ui(self):
        # Top Bar Card
        self.top_card = ctk.CTkFrame(
            self.frame,
            fg_color=theme_manager.get_color("card"),
            border_width=1,
            border_color=theme_manager.get_color("border"),
            corner_radius=10
        )
        self.top_card.pack(fill="x", pady=(0, 16))
        
        top_inner = ctk.CTkFrame(self.top_card, fg_color="transparent")
        top_inner.pack(fill="x", padx=14, pady=12)
        
        # Path display
        path_frame = ctk.CTkFrame(top_inner, fg_color="transparent")
        path_frame.pack(side="left", fill="x", expand=True)
        
        folder_icon = ctk.CTkLabel(
            path_frame,
            text="",
            image=icon_manager.get("folder"),
            width=20,
            height=20
        )
        folder_icon.pack(side="left", padx=(0, 8))
        
        self.path_label = ctk.CTkLabel(
            path_frame,
            text="No download folder selected",
            font=ctk.CTkFont(family="monospace", size=11),
            text_color=theme_manager.get_color("muted")
        )
        self.path_label.pack(side="left")
        
        # Search
        search_frame = ctk.CTkFrame(top_inner, fg_color="transparent")
        search_frame.pack(side="right")
        
        self.search_var = ctk.StringVar()
        self.search_var.trace('w', lambda *args: self.filter_files())
        
        search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="Search...",
            width=200,
            height=32,
            fg_color=theme_manager.get_color("surface"),
            border_color=theme_manager.get_color("border"),
            placeholder_text_color=theme_manager.get_color("muted")
        )
        search_entry.pack(side="left", padx=(0, 8))
        
        refresh_btn = ctk.CTkButton(
            search_frame,
            text="",
            image=icon_manager.get("refresh"),
            width=32,
            height=32,
            fg_color=theme_manager.get_color("surface"),
            border_width=1,
            border_color=theme_manager.get_color("border"),
            text_color=theme_manager.get_color("muted"),
            hover_color=theme_manager.get_color("card"),
            corner_radius=6,
            command=self.refresh_files
        )
        refresh_btn.pack(side="left")
        
        # File List Container
        self.list_container = ctk.CTkScrollableFrame(
            self.frame,
            fg_color="transparent",
            scrollbar_button_color=theme_manager.get_color("accent"),
            scrollbar_button_hover_color=theme_manager.get_color("surface")
        )
        self.list_container.pack(fill="both", expand=True)
        
        # Create empty state (but don't pack it yet)
        self.create_empty_state()
        
        # Status bar
        self.status_bar = ctk.CTkLabel(
            self.frame,
            text="Ready",
            font=ctk.CTkFont(size=11),
            text_color=theme_manager.get_color("secondary")
        )
        self.status_bar.pack(fill="x", pady=(12, 0))
    
    def create_empty_state(self):
        """Create the empty state widget"""
        self.empty_state = ctk.CTkFrame(self.list_container, fg_color="transparent")
        
        empty_icon = ctk.CTkLabel(
            self.empty_state,
            text="[ ]",
            font=ctk.CTkFont(size=32),
            text_color=theme_manager.get_color("muted")
        )
        empty_icon.pack(pady=(40, 16))
        
        empty_title = ctk.CTkLabel(
            self.empty_state,
            text="No videos found",
            font=ctk.CTkFont(size=14),
            text_color=theme_manager.get_color("greige")
        )
        empty_title.pack()
        
        empty_sub = ctk.CTkLabel(
            self.empty_state,
            text="Select a download folder in Queue tab",
            font=ctk.CTkFont(size=12),
            text_color=theme_manager.get_color("muted")
        )
        empty_sub.pack()
    
    def get_download_path(self):
        if hasattr(self.app, 'queue_tab'):
            path = self.app.queue_tab.path_var.get()
            if path and os.path.exists(path):
                return path
        return None
    
    def format_size(self, size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def refresh_files(self):
        download_path = self.get_download_path()
        
        if not download_path:
            try:
                self.path_label.configure(text="No download folder selected")
                self.status_bar.configure(text="Please select a download folder in Queue tab")
            except:
                pass
            self.show_empty_state()
            return
        
        try:
            self.path_label.configure(text=download_path, text_color=theme_manager.get_color("text_primary"))
            self.status_bar.configure(text="Scanning for videos...")
        except:
            pass
        
        video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv')
        
        self.current_files = []
        try:
            for filename in os.listdir(download_path):
                if filename.lower().endswith(video_extensions):
                    filepath = os.path.join(download_path, filename)
                    if os.path.isfile(filepath):
                        stat = os.stat(filepath)
                        size = self.format_size(stat.st_size)
                        modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                        
                        self.current_files.append({
                            'name': filename,
                            'path': filepath,
                            'size': size,
                            'modified': modified,
                            'size_bytes': stat.st_size
                        })
            
            self.current_files.sort(key=lambda x: x['size_bytes'], reverse=True)
            
            # Schedule UI update
            self.frame.after(100, self.filter_files)
            
            try:
                self.status_bar.configure(text=f"Found {len(self.current_files)} video files")
            except:
                pass
            
        except Exception as e:
            try:
                self.status_bar.configure(text=f"Error scanning: {str(e)[:50]}")
            except:
                pass
            self.show_empty_state()
    
    def show_empty_state(self):
        """Safely show empty state"""
        try:
            # Clear container first
            for widget in self.list_container.winfo_children():
                try:
                    widget.destroy()
                except:
                    pass
            
            # Recreate empty state
            self.create_empty_state()
            self.empty_state.pack(fill="both", expand=True)
        except Exception as e:
            print(f"Error showing empty state: {e}")
    
    def hide_empty_state(self):
        """Safely hide empty state"""
        try:
            if self.empty_state and self.empty_state.winfo_exists():
                self.empty_state.pack_forget()
        except:
            pass
    
    def filter_files(self):
        search_term = self.search_var.get().lower()
        
        # Safely clear the container
        try:
            for widget in self.list_container.winfo_children():
                try:
                    if widget != self.empty_state:
                        widget.destroy()
                except:
                    pass
        except:
            pass
        
        filtered = [f for f in self.current_files if search_term in f['name'].lower()]
        
        if not filtered:
            self.show_empty_state()
            return
        
        self.hide_empty_state()
        
        for file_info in filtered:
            try:
                self.create_file_row(file_info)
            except Exception as e:
                print(f"Error creating row: {e}")
    
    def create_file_row(self, file_info):
        row = ctk.CTkFrame(
            self.list_container,
            fg_color=theme_manager.get_color("card"),
            border_width=1,
            border_color=theme_manager.get_color("border"),
            corner_radius=8
        )
        row.pack(fill="x", pady=4)
        
        # Icon
        icon_frame = ctk.CTkFrame(row, width=40, fg_color="transparent")
        icon_frame.pack(side="left", padx=12, pady=12)
        icon_frame.pack_propagate(False)
        
        icon_label = ctk.CTkLabel(
            icon_frame,
            text="",
            image=icon_manager.get("video_sm"),
        )
        icon_label.pack()
        
        # Info section
        info_frame = ctk.CTkFrame(row, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True, padx=(0, 12), pady=12)
        
        filename = file_info['name']
        if len(filename) > 50:
            filename = filename[:47] + "..."
        
        name_label = ctk.CTkLabel(
            info_frame,
            text=filename,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=theme_manager.get_color("text_primary"),
            anchor="w"
        )
        name_label.pack(anchor="w")
        
        # Chips
        chips_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        chips_frame.pack(anchor="w", pady=(4, 0))
        
        # Size chip
        size_chip = ctk.CTkFrame(
            chips_frame,
            fg_color=theme_manager.get_color("surface"),
            border_width=1,
            border_color=theme_manager.get_color("border"),
            corner_radius=4
        )
        size_chip.pack(side="left", padx=(0, 6))
        
        size_label = ctk.CTkLabel(
            size_chip,
            text=file_info['size'],
            font=ctk.CTkFont(size=11),
            text_color=theme_manager.get_color("greige")
        )
        size_label.pack(padx=6, pady=2)
        
        # Date chip
        date_chip = ctk.CTkFrame(
            chips_frame,
            fg_color=theme_manager.get_color("surface"),
            border_width=1,
            border_color=theme_manager.get_color("border"),
            corner_radius=4
        )
        date_chip.pack(side="left")
        
        date_label = ctk.CTkLabel(
            date_chip,
            text=file_info['modified'],
            font=ctk.CTkFont(size=11),
            text_color=theme_manager.get_color("greige")
        )
        date_label.pack(padx=6, pady=2)
        
        # Actions
        actions_frame = ctk.CTkFrame(row, fg_color="transparent")
        actions_frame.pack(side="right", padx=12, pady=12)
        
        play_btn = ctk.CTkButton(
            actions_frame,
            text="",
            image=icon_manager.get("play_sm"),
            width=32,
            height=28,
            fg_color=theme_manager.get_color("accent"),
            text_color="#FFFFFF",
            corner_radius=6,
            command=lambda p=file_info['path'], n=file_info['name']: self.play_file(p, n)
        )
        play_btn.pack(side="left", padx=2)
        
        delete_btn = ctk.CTkButton(
            actions_frame,
            text="",
            image=icon_manager.get("trash_sm"),
            width=32,
            height=28,
            fg_color="transparent",
            border_width=1,
            border_color=theme_manager.get_color("error"),
            text_color=theme_manager.get_color("error"),
            hover_color=theme_manager.get_color("surface"),
            corner_radius=6,
            command=lambda p=file_info['path'], n=file_info['name']: self.delete_file(p, n)
        )
        delete_btn.pack(side="left", padx=2)
    
    def play_file(self, filepath, filename):
        if not os.path.exists(filepath):
            messagebox.showerror("Error", "File not found")
            self.refresh_files()
            return
        
        vlc_path = self.app.vlc_path
        
        try:
            if vlc_path and os.path.exists(vlc_path):
                subprocess.Popen([vlc_path, filepath])
            else:
                import sys
                if sys.platform == "win32":
                    os.startfile(filepath)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", filepath])
                else:
                    subprocess.Popen(["xdg-open", filepath])
            self.status_bar.configure(text=f"Playing: {filename}")
        except Exception as e:
            messagebox.showerror("Play Error", f"Failed to play video:\n{str(e)}")
    
    def delete_file(self, filepath, filename):
        if messagebox.askyesno("Confirm Delete", f"Delete '{filename}'?\n\nThis action cannot be undone!"):
            try:
                os.remove(filepath)
                self.frame.after(500, self.refresh_files)
            except Exception as e:
                messagebox.showerror("Delete Error", f"Failed to delete file:\n{str(e)}")
    
    def show(self):
        self.frame.pack(fill="both", expand=True)
        self.refresh_files()
    
    def hide(self):
        self.frame.pack_forget()
    
    def refresh_list(self):
        self.refresh_files()