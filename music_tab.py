import tkinter as tk
from tkinter import ttk, messagebox
import os
import subprocess
from datetime import datetime
import mutagen
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4

class MusicTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.frame = tk.Frame(parent)
        self.current_files = []
        
        self.build_ui()
    
    def build_ui(self):
        # Main container
        main_frame = tk.Frame(self.frame, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top bar with refresh and info
        top_frame = tk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.info_label = tk.Label(top_frame, text="Music Library", font=('Arial', 10, 'bold'))
        self.info_label.pack(side=tk.LEFT)
        
        self.refresh_btn = tk.Button(
            top_frame, 
            text="🔄 Refresh", 
            command=self.refresh_files,
            width=10
        )
        self.refresh_btn.pack(side=tk.RIGHT, padx=5)
        
        self.path_label = tk.Label(
            top_frame, 
            text="No download folder selected", 
            font=('Arial', 9), 
            fg='gray'
        )
        self.path_label.pack(side=tk.RIGHT, padx=10)
        
        # Search bar
        search_frame = tk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(search_frame, text="🔍 Search:", font=('Arial', 10)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.filter_files())
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # Create Treeview for file list
        list_frame = tk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Scrollbars
        v_scrollbar = tk.Scrollbar(list_frame)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        h_scrollbar = tk.Scrollbar(list_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeview with more columns for music metadata
        columns = ("Title", "Artist", "Duration", "Size", "Modified", "Actions")
        self.tree = ttk.Treeview(
            list_frame, 
            columns=columns, 
            show='headings',
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            height=15
        )
        
        self.tree.heading("Title", text="Song Title")
        self.tree.heading("Artist", text="Artist")
        self.tree.heading("Duration", text="Duration")
        self.tree.heading("Size", text="Size")
        self.tree.heading("Modified", text="Date Modified")
        self.tree.heading("Actions", text="Actions")
        
        self.tree.column("Title", width=300)
        self.tree.column("Artist", width=150)
        self.tree.column("Duration", width=80)
        self.tree.column("Size", width=100)
        self.tree.column("Modified", width=150)
        self.tree.column("Actions", width=100)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        v_scrollbar.config(command=self.tree.yview)
        h_scrollbar.config(command=self.tree.xview)
        
        # Bind double-click to play
        self.tree.bind('<Double-Button-1>', self.on_double_click)
        
        # Right-click menu
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="▶ Play", command=self.play_selected)
        self.context_menu.add_command(label="📂 Open Folder", command=self.open_folder)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑 Delete File", command=self.delete_selected)
        
        self.tree.bind('<Button-3>', self.show_context_menu)
        
        # Status bar
        self.status_bar = tk.Label(
            main_frame, 
            text="Ready", 
            font=('Arial', 9), 
            fg='gray',
            anchor=tk.W
        )
        self.status_bar.pack(fill=tk.X, pady=(10, 0))
    
    def get_download_path(self):
        """Get the current download path from queue tab"""
        if hasattr(self.app, 'queue_tab'):
            path = self.app.queue_tab.path_var.get()
            if path and os.path.exists(path):
                return path
        return None
    
    def get_audio_metadata(self, filepath, filename):
        """Extract metadata from audio file"""
        title = os.path.splitext(filename)[0]
        artist = "Unknown Artist"
        duration_str = "Unknown"
        
        try:
            # Try to use mutagen for metadata
            if filename.lower().endswith('.mp3'):
                audio = MP3(filepath)
                if audio.get('TIT2'):
                    title = str(audio['TIT2'])
                if audio.get('TPE1'):
                    artist = str(audio['TPE1'])
                duration = audio.info.length
            elif filename.lower().endswith('.m4a'):
                audio = MP4(filepath)
                if audio.get('©nam'):
                    title = str(audio['©nam'][0])
                if audio.get('©art'):
                    artist = str(audio['©art'][0])
                duration = audio.info.length
            elif filename.lower().endswith('.flac'):
                audio = FLAC(filepath)
                if audio.get('title'):
                    title = audio.get('title')[0]
                if audio.get('artist'):
                    artist = audio.get('artist')[0]
                duration = audio.info.length
            else:
                # For other formats, just use filename
                duration = 0
            
            # Format duration
            if duration > 0:
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                duration_str = f"{minutes}:{seconds:02d}"
                
        except Exception as e:
            # If mutagen fails, just use filename
            pass
        
        return title, artist, duration_str
    
    def format_size(self, size_bytes):
        """Format file size to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def filter_files(self):
        """Filter files based on search query"""
        search_term = self.search_var.get().lower()
        
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add filtered files
        for file_info in self.current_files:
            if (search_term in file_info['title'].lower() or 
                search_term in file_info['artist'].lower() or
                search_term in file_info['name'].lower()):
                self.tree.insert('', 'end', values=(
                    file_info['title'],
                    file_info['artist'],
                    file_info['duration'],
                    file_info['size'],
                    file_info['modified'],
                    "▶️ Play"
                ), tags=(file_info['path'],))
    
    def on_double_click(self, event):
        """Handle double-click on item"""
        self.play_selected()
    
    def show_context_menu(self, event):
        """Show right-click context menu"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def play_selected(self):
        """Play selected audio file"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a music file first")
            return
        
        # Get file path from selected item
        item = selection[0]
        values = self.tree.item(item, 'values')
        title = values[0]
        
        # Find the file by title
        filepath = None
        for file_info in self.current_files:
            if file_info['title'] == title:
                filepath = file_info['path']
                break
        
        if not filepath or not os.path.exists(filepath):
            messagebox.showerror("Error", "File not found")
            self.refresh_files()
            return
        
        # Get VLC path from app
        vlc_path = self.app.vlc_path
        
        try:
            if vlc_path and os.path.exists(vlc_path):
                subprocess.Popen([vlc_path, filepath])
            else:
                # Try system default
                import sys
                if sys.platform == "win32":
                    os.startfile(filepath)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", filepath])
                else:
                    subprocess.Popen(["xdg-open", filepath])
            self.status_bar.config(text=f"Playing: {title}")
        except Exception as e:
            messagebox.showerror("Play Error", f"Failed to play music:\n{str(e)}")
    
    def open_folder(self):
        """Open folder containing the selected file"""
        download_path = self.get_download_path()
        if download_path and os.path.exists(download_path):
            import sys
            if sys.platform == "win32":
                os.startfile(download_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", download_path])
            else:
                subprocess.Popen(["xdg-open", download_path])
    
    def delete_selected(self):
        """Delete selected audio file"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file first")
            return
        
        item = selection[0]
        values = self.tree.item(item, 'values')
        title = values[0]
        
        # Find the file path
        filepath = None
        for file_info in self.current_files:
            if file_info['title'] == title:
                filepath = file_info['path']
                break
        
        if not filepath:
            messagebox.showerror("Error", "File not found")
            return
        
        # Confirm deletion
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete:\n{title}\n\nThis action cannot be undone!"):
            try:
                os.remove(filepath)
                self.status_bar.config(text=f"Deleted: {title}")
                self.refresh_files()
                messagebox.showinfo("Success", f"Deleted: {title}")
            except Exception as e:
                messagebox.showerror("Delete Error", f"Failed to delete file:\n{str(e)}")
    
    def refresh_files(self):
        """Actually scan and refresh the music list"""
        download_path = self.get_download_path()
        
        if not download_path:
            self.path_label.config(text="No download folder selected", fg='orange')
            self.status_bar.config(text="Please select a download folder in Queue tab")
            # Clear tree
            for item in self.tree.get_children():
                self.tree.delete(item)
            return
        
        self.path_label.config(text=f"📁 {download_path}", fg='green')
        self.status_bar.config(text="Scanning for music files...")
        self.frame.update()
        
        # Audio extensions
        audio_extensions = ('.mp3', '.m4a', '.ogg', '.flac', '.wav')
        
        # Scan directory
        self.current_files = []
        try:
            for filename in os.listdir(download_path):
                if filename.lower().endswith(audio_extensions):
                    filepath = os.path.join(download_path, filename)
                    if os.path.isfile(filepath):
                        # Get file info
                        stat = os.stat(filepath)
                        size = self.format_size(stat.st_size)
                        modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                        
                        # Get metadata
                        title, artist, duration = self.get_audio_metadata(filepath, filename)
                        
                        self.current_files.append({
                            'name': filename,
                            'path': filepath,
                            'title': title,
                            'artist': artist,
                            'duration': duration,
                            'size': size,
                            'modified': modified,
                            'size_bytes': stat.st_size
                        })
            
            # Sort by title
            self.current_files.sort(key=lambda x: x['title'].lower())
            
            self.filter_files()
            self.status_bar.config(text=f"Found {len(self.current_files)} music files")
            
        except Exception as e:
            self.status_bar.config(text=f"Error scanning: {str(e)}")
            messagebox.showerror("Scan Error", f"Failed to scan folder:\n{str(e)}")
    
    def refresh_list(self):
        """Public method to refresh the list - called from ui.py"""
        self.refresh_files()
    
    def show(self):
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.refresh_files()
    
    def hide(self):
        self.frame.pack_forget()
    
    def apply_theme(self, theme):
        self.frame.configure(bg=theme["bg"])
        for widget in self.frame.winfo_children():
            self.apply_theme_to_widget(widget, theme)
    
    def apply_theme_to_widget(self, widget, theme):
        try:
            if isinstance(widget, (tk.Frame, tk.Label)):
                widget.configure(bg=theme["bg"])
                if isinstance(widget, tk.Label):
                    current_fg = widget.cget("fg")
                    if current_fg not in ["orange", "red", "gray", "green"]:
                        widget.configure(fg=theme["fg"])
            elif isinstance(widget, tk.Button):
                current_bg = widget.cget("bg")
                if current_bg not in ["#2196F3", "#4CAF50", "#f44336"]:
                    widget.configure(bg=theme["button_bg"], fg=theme["button_fg"])
            elif isinstance(widget, tk.Entry):
                widget.configure(bg=theme["entry_bg"], fg=theme["entry_fg"])
        except:
            pass
        
        for child in widget.winfo_children():
            self.apply_theme_to_widget(child, theme)