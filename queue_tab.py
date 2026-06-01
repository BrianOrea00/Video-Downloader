import customtkinter as ctk
from tkinter import messagebox
from downloader import Downloader
from config import RESOLUTIONS, HISTORY_FILE
from utils import save_history, load_queue, save_queue
from icon_manager import icon_manager
from theme_manager import theme_manager
from datetime import datetime
import threading
import subprocess
import tkinter as tk
import os
import json


class QueueTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.downloader = Downloader()
        self.queue = load_queue()
        self.downloading = False
        self.active_downloads = []
        self.current_download_item = None
        
        self.build_ui()
    
    def get_clipboard_text(self):
        """Read clipboard robustly"""
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
            text = self.frame.clipboard_get()
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
    
    def build_ui(self):
        # Main container
        self.main_frame = ctk.CTkScrollableFrame(self.frame, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True)
        
        # URL Input Card
        self.input_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=theme_manager.get_color("card"),
            border_width=1,
            border_color=theme_manager.get_color("border"),
            corner_radius=10
        )
        self.input_card.pack(fill="x", pady=(0, 16))
        
        # Card header
        input_header = ctk.CTkFrame(self.input_card, fg_color="transparent")
        input_header.pack(fill="x", padx=14, pady=(12, 8))
        
        section_label = ctk.CTkLabel(
            input_header,
            text="ADD URL",
            font=ctk.CTkFont(size=11),
            text_color=theme_manager.get_color("secondary")
        )
        section_label.pack(anchor="w")
        
        # URL row
        url_frame = ctk.CTkFrame(self.input_card, fg_color="transparent")
        url_frame.pack(fill="x", padx=14, pady=(0, 10))
        
        self.url_var = ctk.StringVar()
        self.url_entry = ctk.CTkEntry(
            url_frame,
            textvariable=self.url_var,
            placeholder_text="https://youtube.com/watch?v=...",
            font=ctk.CTkFont(family="monospace", size=12),
            fg_color=theme_manager.get_color("surface"),
            border_color=theme_manager.get_color("border"),
            text_color=theme_manager.get_color("text_primary"),
            placeholder_text_color=theme_manager.get_color("muted")
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        paste_btn = ctk.CTkButton(
            url_frame,
            text="Paste",
            fg_color=theme_manager.get_color("surface"),
            border_width=1,
            border_color=theme_manager.get_color("border"),
            text_color=theme_manager.get_color("muted"),
            hover_color=theme_manager.get_color("card"),
            width=80,
            height=36,
            corner_radius=6,
            command=self.paste_from_clipboard
        )
        paste_btn.pack(side="left", padx=(0, 8))
        
        add_btn = ctk.CTkButton(
            url_frame,
            text="Add to Queue",
            fg_color=theme_manager.get_color("accent"),
            text_color="#FFFFFF",
            width=120,
            height=36,
            corner_radius=6,
            command=self.add_to_queue
        )
        add_btn.pack(side="left")
        
        # Options row (pill buttons)
        options_frame = ctk.CTkFrame(self.input_card, fg_color="transparent")
        options_frame.pack(fill="x", padx=14, pady=(0, 10))
        
        # Resolution pills
        self.res_pills = {}
        res_pill_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        res_pill_frame.pack(side="left", padx=(0, 10))
        
        self.res_var = ctk.StringVar(value="720")
        
        for res in ["720", "1080"]:
            pill = ctk.CTkButton(
                res_pill_frame,
                text=f"{res}p",
                fg_color=theme_manager.get_color("surface"),
                border_width=1,
                border_color=theme_manager.get_color("border"),
                text_color=theme_manager.get_color("greige"),
                hover_color=theme_manager.get_color("card"),
                width=50,
                height=28,
                corner_radius=14,
                font=ctk.CTkFont(size=12),
                command=lambda r=res: self.set_resolution(r)
            )
            pill.pack(side="left", padx=2)
            self.res_pills[res] = pill
        
        # Audio pill
        self.audio_only = ctk.BooleanVar(value=False)
        self.audio_pill = ctk.CTkButton(
            options_frame,
            text="Audio Only",
            fg_color=theme_manager.get_color("surface"),
            border_width=1,
            border_color=theme_manager.get_color("border"),
            text_color=theme_manager.get_color("greige"),
            hover_color=theme_manager.get_color("card"),
            width=100,
            height=28,
            corner_radius=14,
            font=ctk.CTkFont(size=12),
            command=self.toggle_audio
        )
        self.audio_pill.pack(side="left")
        
        # Path row
        path_frame = ctk.CTkFrame(self.input_card, fg_color="transparent")
        path_frame.pack(fill="x", padx=14, pady=(0, 14))
        
        path_bg = ctk.CTkFrame(
            path_frame,
            fg_color=theme_manager.get_color("surface"),
            border_width=1,
            border_color=theme_manager.get_color("border"),
            corner_radius=6
        )
        path_bg.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        folder_icon = ctk.CTkLabel(
            path_bg,
            text="",
            image=icon_manager.get("folder"),
            width=20,
            height=20
        )
        folder_icon.pack(side="left", padx=(10, 5), pady=8)
        
        self.path_var = ctk.StringVar()
        self.path_label = ctk.CTkLabel(
            path_bg,
            text="Select download folder...",
            font=ctk.CTkFont(family="monospace", size=11),
            text_color=theme_manager.get_color("muted"),
            anchor="w"
        )
        self.path_label.pack(side="left", fill="x", expand=True, pady=8)
        
        browse_btn = ctk.CTkButton(
            path_frame,
            text="Browse",
            fg_color=theme_manager.get_color("surface"),
            border_width=1,
            border_color=theme_manager.get_color("border"),
            text_color=theme_manager.get_color("muted"),
            hover_color=theme_manager.get_color("card"),
            width=80,
            height=36,
            corner_radius=6,
            command=self.browse
        )
        browse_btn.pack(side="left")
        
        # Active Download Card
        self.active_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=theme_manager.get_color("card"),
            border_width=1,
            border_color=theme_manager.get_color("border"),
            corner_radius=10
        )
        
        self.active_title_label = ctk.CTkLabel(
            self.active_card,
            text="No active download",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=theme_manager.get_color("text_primary")
        )
        self.active_title_label.pack(anchor="w", padx=14, pady=(12, 8))
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            self.active_card,
            height=5,
            fg_color=theme_manager.get_color("border"),
            progress_color=theme_manager.get_color("warning")
        )
        self.progress_bar.pack(fill="x", padx=14, pady=(0, 8))
        self.progress_bar.set(0)
        
        # Progress stats row
        stats_row = ctk.CTkFrame(self.active_card, fg_color="transparent")
        stats_row.pack(fill="x", padx=14, pady=(0, 10))
        
        self.bytes_label = ctk.CTkLabel(
            stats_row,
            text="0 MB / 0 MB",
            font=ctk.CTkFont(size=11),
            text_color=theme_manager.get_color("greige")
        )
        self.bytes_label.pack(side="left")
        
        self.percent_label = ctk.CTkLabel(
            stats_row,
            text="0%",
            font=ctk.CTkFont(family="monospace", size=11),
            text_color=theme_manager.get_color("greige")
        )
        self.percent_label.pack(side="right")
        
        # Speed and ETA row
        speed_eta_row = ctk.CTkFrame(self.active_card, fg_color="transparent")
        speed_eta_row.pack(fill="x", padx=14, pady=(0, 12))
        
        self.speed_label = ctk.CTkLabel(
            speed_eta_row,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=theme_manager.get_color("muted")
        )
        self.speed_label.pack(side="left")
        
        self.eta_label = ctk.CTkLabel(
            speed_eta_row,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=theme_manager.get_color("muted")
        )
        self.eta_label.pack(side="right")
        
        self.active_card.pack_forget()
        
        # Stats chips row
        chips_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        chips_frame.pack(fill="x", pady=(0, 12))
        
        stats = [
            ("Total", "0"),
            ("Pending", "0"),
            ("Active", "0"),
            ("Done", "0"),
        ]
        
        self.stat_chips = {}
        for label, value in stats:
            chip = ctk.CTkFrame(
                chips_frame,
                fg_color=theme_manager.get_color("surface"),
                border_width=1,
                border_color=theme_manager.get_color("border"),
                corner_radius=4
            )
            chip.pack(side="left", padx=4)
            
            chip_label = ctk.CTkLabel(
                chip,
                text=f"{label}: {value}",
                font=ctk.CTkFont(size=11),
                text_color=theme_manager.get_color("greige")
            )
            chip_label.pack(padx=8, pady=3)
            self.stat_chips[label] = chip_label
        
        # Queue List - CTkScrollableFrame with row cards
        queue_label = ctk.CTkLabel(
            self.main_frame,
            text="QUEUE",
            font=ctk.CTkFont(size=11),
            text_color=theme_manager.get_color("secondary")
        )
        queue_label.pack(anchor="w", pady=(0, 8))
        
        self.queue_container = ctk.CTkScrollableFrame(
            self.main_frame,
            fg_color="transparent",
            scrollbar_button_color=theme_manager.get_color("accent"),
            scrollbar_button_hover_color=theme_manager.get_color("surface")
        )
        self.queue_container.pack(fill="both", expand=True, pady=(0, 12))
        
        # Action Buttons
        action_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        action_frame.pack(fill="x", pady=(0, 0))
        
        self.start_btn = ctk.CTkButton(
            action_frame,
            text="Start Queue",
            fg_color=theme_manager.get_color("accent"),
            text_color="#FFFFFF",
            height=36,
            corner_radius=6,
            command=self.start_queue
        )
        self.start_btn.pack(side="left", padx=4)
        
        self.stop_btn = ctk.CTkButton(
            action_frame,
            text="Stop",
            fg_color=theme_manager.get_color("surface"),
            border_width=1,
            border_color=theme_manager.get_color("error"),
            text_color=theme_manager.get_color("error"),
            height=36,
            corner_radius=6,
            state="disabled",
            command=self.stop_queue
        )
        self.stop_btn.pack(side="left", padx=4)
        
        clear_completed_btn = ctk.CTkButton(
            action_frame,
            text="Clear Completed",
            fg_color=theme_manager.get_color("surface"),
            border_width=1,
            border_color=theme_manager.get_color("border"),
            text_color=theme_manager.get_color("greige"),
            height=36,
            corner_radius=6,
            command=self.clear_completed
        )
        clear_completed_btn.pack(side="left", padx=4)
    
    def set_resolution(self, res):
        """Set resolution and update pill styling"""
        self.res_var.set(res)
        for pill_res, pill in self.res_pills.items():
            if pill_res == res:
                pill.configure(
                    border_color=theme_manager.get_color("accent"),
                    text_color=theme_manager.get_color("accent"),
                    fg_color="#0A2822"
                )
            else:
                pill.configure(
                    border_color=theme_manager.get_color("border"),
                    text_color=theme_manager.get_color("greige"),
                    fg_color=theme_manager.get_color("surface")
                )
    
    def toggle_audio(self):
        """Toggle audio only mode"""
        current = self.audio_only.get()
        self.audio_only.set(not current)
        if self.audio_only.get():
            self.audio_pill.configure(
                border_color=theme_manager.get_color("accent"),
                text_color=theme_manager.get_color("accent"),
                fg_color="#0A2822"
            )
        else:
            self.audio_pill.configure(
                border_color=theme_manager.get_color("border"),
                text_color=theme_manager.get_color("greige"),
                fg_color=theme_manager.get_color("surface")
            )
    
    def paste_from_clipboard(self):
        """Paste URL from clipboard"""
        url = self.get_clipboard_text()
        if url:
            self.url_var.set(url)
            self.preview()
        else:
            messagebox.showerror(
                "Clipboard Error",
                "Could not read clipboard.\n\nTry Ctrl+V to paste manually."
            )
    
    def browse(self):
        from tkinter import filedialog
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)
            self.path_label.configure(text=folder, text_color=theme_manager.get_color("text_primary"))
            if hasattr(self.app, 'update_storage'):
                self.app.update_storage(folder)
    
    def preview(self):
        if not self.url_var.get():
            messagebox.showwarning("Warning", "Please enter a URL first")
            return
            
        try:
            # Just validate - don't need to show info
            info = self.downloader.get_info(self.url_var.get())
        except Exception as e:
            pass
    
    def check_duplicate_url(self, url):
        """Check if URL already exists in queue or history"""
        # Check in current queue (pending or downloading)
        for item in self.queue:
            if item.get("url") == url and item.get("status") in ["pending", "downloading"]:
                return "queue", item
        
        # Check in history
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f:
                    history = json.load(f)
                    for item in history:
                        if item.get("url") == url:
                            return "history", item
            except:
                pass
        
        return None, None
    
    def add_to_queue(self):
        if not self.url_var.get():
            messagebox.showwarning("Warning", "Please enter a video URL")
            return
        
        if not self.path_var.get():
            messagebox.showwarning("Warning", "Please select a save path")
            return
        
        url = self.url_var.get()
        
        # Check for duplicates
        duplicate_type, duplicate_item = self.check_duplicate_url(url)
        
        if duplicate_type == "queue":
            # URL already in queue with pending/downloading status
            response = messagebox.askyesno(
                "Duplicate URL in Queue",
                f"This URL is already in the queue with status: {duplicate_item.get('status')}\n\n"
                f"Add it again anyway?"
            )
            if not response:
                self.url_var.set("")  # Clear URL
                return
                
        elif duplicate_type == "history":
            # URL was previously downloaded
            date_added = duplicate_item.get('date_added', 'unknown date')
            status = duplicate_item.get('status', 'completed')
            response = messagebox.askyesno(
                "Previously Downloaded",
                f"This URL was already downloaded on {date_added}\n"
                f"Status: {status}\n\n"
                f"Download again?"
            )
            if not response:
                self.url_var.set("")  # Clear URL
                return
        
        # Apply default settings
        default_res = self.app.settings.get("default_resolution", "720")
        default_audio = self.app.settings.get("default_audio_only", False)
        
        if self.res_var.get() == "720" and default_res != "720":
            self.res_var.set(default_res)
        
        if not self.audio_only.get() and default_audio:
            self.audio_only.set(True)
        
        # Get video title
        try:
            info = self.downloader.get_info(url)
            title = info.get('title', 'Unknown')
        except Exception as e:
            title = url[:50]
        
        # Create queue item
        queue_item = {
            "url": url,
            "path": self.path_var.get(),
            "resolution": self.res_var.get(),
            "audio_only": self.audio_only.get(),
            "title": title,
            "status": "pending",
            "date_added": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.queue.append(queue_item)
        save_queue(self.queue)
        self.refresh_queue_display()
        
        # Clear URL
        self.url_var.set("")
        
        # Reset to defaults
        self.res_var.set(self.app.settings.get("default_resolution", "720"))
        self.audio_only.set(self.app.settings.get("default_audio_only", False))
        
        self.update_stats_display()
    
    def refresh_queue_display(self):
        """Refresh queue display with card rows"""
        # Clear existing widgets
        for widget in self.queue_container.winfo_children():
            widget.destroy()
        
        for i, item in enumerate(self.queue):
            status = item.get("status", "pending")
            
            # Row card
            row = ctk.CTkFrame(
                self.queue_container,
                fg_color=theme_manager.get_color("card") if status != "pending" else "#0A1A16",
                border_width=1,
                border_color=theme_manager.get_color("border"),
                corner_radius=8
            )
            row.pack(fill="x", pady=4)
            
            # Thumbnail placeholder
            thumb = ctk.CTkFrame(
                row,
                width=40,
                height=28,
                fg_color=theme_manager.get_color("surface"),
                corner_radius=4
            )
            thumb.pack(side="left", padx=12, pady=10)
            thumb.pack_propagate(False)
            
            _thumb_icon = icon_manager.get("download_sm") if not item.get("audio_only") else icon_manager.get("music_sm")
            icon_label = ctk.CTkLabel(
                thumb,
                text="",
                image=_thumb_icon,
            )
            icon_label.pack(expand=True)
            
            # Middle section - title and chips
            middle = ctk.CTkFrame(row, fg_color="transparent")
            middle.pack(side="left", fill="x", expand=True, padx=(0, 12), pady=10)
            
            # Title
            title_color = theme_manager.get_color("greige") if status == "completed" else theme_manager.get_color("text_primary")
            title_label = ctk.CTkLabel(
                middle,
                text=item.get('title', 'Unknown')[:60],
                font=ctk.CTkFont(size=13, weight="bold" if status != "completed" else "normal"),
                text_color=title_color,
                anchor="w"
            )
            title_label.pack(anchor="w")
            
            # Chips row
            chips_row = ctk.CTkFrame(middle, fg_color="transparent")
            chips_row.pack(anchor="w", pady=(4, 0))
            
            # Resolution/Format chip
            res_text = f"{item.get('resolution', 'N/A')}p"
            if item.get('audio_only'):
                res_text = "MP3"
            
            res_chip = ctk.CTkFrame(
                chips_row,
                fg_color=theme_manager.get_color("surface"),
                border_width=1,
                border_color=theme_manager.get_color("mid"),
                corner_radius=4
            )
            res_chip.pack(side="left", padx=(0, 6))
            
            res_label = ctk.CTkLabel(
                res_chip,
                text=res_text,
                font=ctk.CTkFont(size=10),
                text_color=theme_manager.get_color("accent")
            )
            res_label.pack(padx=6, pady=2)
            
            # Status dot
            if status == "pending":
                dot_color = theme_manager.get_color("mid")
                dot_text = "Pending"
            elif status == "downloading":
                dot_color = theme_manager.get_color("warning")
                dot_text = "Downloading"
            elif status == "completed":
                dot_color = theme_manager.get_color("success")
                dot_text = "Completed"
            elif status == "failed":
                dot_color = theme_manager.get_color("error")
                dot_text = "Failed"
            else:
                dot_color = theme_manager.get_color("mid")
                dot_text = "Pending"
            
            status_chip = ctk.CTkFrame(
                chips_row,
                fg_color=theme_manager.get_color("surface"),
                border_width=1,
                border_color=dot_color,
                corner_radius=4
            )
            status_chip.pack(side="left")
            
            status_label = ctk.CTkLabel(
                status_chip,
                text=f"● {dot_text}",
                font=ctk.CTkFont(size=10),
                text_color=dot_color
            )
            status_label.pack(padx=6, pady=2)
            
            # Right side - action buttons
            actions = ctk.CTkFrame(row, fg_color="transparent")
            actions.pack(side="right", padx=12, pady=10)
            
            folder_btn = ctk.CTkButton(
                actions,
                text="",
                image=icon_manager.get("folder_sm"),
                width=28,
                height=28,
                fg_color="transparent",
                border_width=1,
                border_color=theme_manager.get_color("border"),
                text_color=theme_manager.get_color("muted"),
                hover_color=theme_manager.get_color("surface"),
                corner_radius=6,
                command=lambda p=item.get('path', ''): self.open_folder(p)
            )
            folder_btn.pack(side="left", padx=2)
            
            if status != "downloading":
                delete_btn = ctk.CTkButton(
                    actions,
                    text="",
                    image=icon_manager.get("trash_sm"),
                    width=28,
                    height=28,
                    fg_color="transparent",
                    border_width=1,
                    border_color=theme_manager.get_color("error"),
                    text_color=theme_manager.get_color("error"),
                    hover_color=theme_manager.get_color("surface"),
                    corner_radius=6,
                    command=lambda idx=i: self.remove_item(idx)
                )
                delete_btn.pack(side="left", padx=2)
        
        self.update_stats_display()
        
        # Update app badge
        if hasattr(self.app, 'update_count_badge'):
            pending_count = sum(1 for item in self.queue if item.get("status") == "pending")
            self.app.update_count_badge(pending_count)
    
    def remove_item(self, index):
        """Remove item at index"""
        if index < len(self.queue):
            del self.queue[index]
            save_queue(self.queue)
            self.refresh_queue_display()
    
    def open_folder(self, path):
        """Open folder in file explorer"""
        if path and os.path.exists(path):
            import sys
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
    
    def clear_completed(self):
        """Remove all completed items from queue"""
        self.queue = [item for item in self.queue if item.get("status") != "completed"]
        save_queue(self.queue)
        self.refresh_queue_display()
    
    def get_queue_stats(self):
        total = len(self.queue)
        pending = sum(1 for item in self.queue if item.get("status") == "pending")
        downloading = sum(1 for item in self.queue if item.get("status") == "downloading")
        completed = sum(1 for item in self.queue if item.get("status") == "completed")
        failed = sum(1 for item in self.queue if item.get("status") == "failed")
        
        return {
            "total": total,
            "pending": pending,
            "downloading": downloading,
            "completed": completed,
            "failed": failed
        }
    
    def update_stats_display(self):
        stats = self.get_queue_stats()
        self.stat_chips["Total"].configure(text=f"Total: {stats['total']}")
        self.stat_chips["Pending"].configure(text=f"Pending: {stats['pending']}")
        self.stat_chips["Active"].configure(text=f"Active: {stats['downloading']}")
        self.stat_chips["Done"].configure(text=f"Done: {stats['completed']}")
    
    def start_queue(self):
        if self.downloading:
            return
        
        pending = any(item.get("status") == "pending" for item in self.queue)
        if not pending:
            messagebox.showinfo("Queue Empty", "No pending downloads in queue")
            return
        
        self.downloading = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        
        self.active_card.pack(fill="x", pady=(0, 16))
        
        thread = threading.Thread(target=self.process_queue, daemon=True)
        thread.start()
    
    def stop_queue(self):
        self.downloading = False
        if self.current_download_item:
            self.downloader.cancel()
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.update_stats_display()
    
    def process_queue(self):
        for i, item in enumerate(self.queue):
            if not self.downloading:
                break
            
            if item.get("status") == "pending":
                item["status"] = "downloading"
                save_queue(self.queue)
                
                self.frame.after(0, lambda t=item['title']: self.active_title_label.configure(text=t[:60]))
                self.frame.after(0, self.refresh_queue_display)
                
                self.download_item(item)
                
                while item.get("status") == "downloading" and self.downloading:
                    import time
                    time.sleep(0.5)
                    self.frame.after(0, self.update_stats_display)
        
        self.downloading = False
        self.frame.after(0, lambda: self.start_btn.configure(state="normal"))
        self.frame.after(0, lambda: self.stop_btn.configure(state="disabled"))
        self.frame.after(0, lambda: self.active_card.pack_forget())
        self.frame.after(0, self.update_stats_display)
        self.frame.after(0, self.refresh_queue_display)
        
    def download_item(self, item):
        download_complete = threading.Event()
        self.current_download_item = item
        
        # Build cookie settings from app settings
        cookie_settings = {
            "cookie_method": self.app.settings.get("cookie_method", "none"),
            "cookie_browser": self.app.settings.get("cookie_browser", "chrome"),
            "cookie_file_path": self.app.settings.get("cookie_file_path", "")
        }
        
        def update_progress(data):
            def update():
                if '_percent' in data:
                    percent = data['_percent'] / 100
                    self.progress_bar.set(percent)
                    self.percent_label.configure(text=f"{data['_percent']:.1f}%")
                
                if '_speed_str' in data and data['_speed_str']:
                    self.speed_label.configure(text=f"{data['_speed_str']}")
                
                if '_eta_str' in data and data['_eta_str']:
                    self.eta_label.configure(text=f"ETA: {data['_eta_str']}")
                
                if '_downloaded_bytes_str' in data and '_total_bytes_str' in data:
                    self.bytes_label.configure(text=f"{data['_downloaded_bytes_str']} / {data['_total_bytes_str']}")
                elif '_percent_str' in data:
                    self.bytes_label.configure(text=f"{data['_percent_str']}")
            
            self.frame.after(0, update)
        
        def done_callback(msg):
            def finalize():
                if "completed" in msg.lower():
                    item["status"] = "completed"
                    save_history({
                        "url": item["url"],
                        "resolution": item["resolution"] if not item["audio_only"] else "Audio Only",
                        "status": msg
                    })
                    self.app.on_download_complete()
                else:
                    item["status"] = "failed"
                
                save_queue(self.queue)
                self.refresh_queue_display()
                
                self.progress_bar.set(0)
                self.percent_label.configure(text="0%")
                self.speed_label.configure(text="")
                self.eta_label.configure(text="")
                self.bytes_label.configure(text="0 MB / 0 MB")
                
                download_complete.set()
            
            self.frame.after(0, finalize)
        
        downloader = Downloader()
        downloader.download(
            item["url"],
            item["path"],
            item["resolution"],
            update_progress,
            done_callback,
            audio_only=item["audio_only"],
            cookie_settings=cookie_settings  # Pass cookie settings here
        )
        
        download_complete.wait()
        self.current_download_item = None
    
    def show(self):
        self.frame.pack(fill="both", expand=True)
        self.refresh_queue_display()
        self.update_stats_display()
        if hasattr(self, 'url_entry'):
            self.url_entry.focus_set()
    
    def hide(self):
        self.frame.pack_forget()