import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from downloader import Downloader
from config import RESOLUTIONS
from utils import save_history, load_queue, save_queue
from datetime import datetime
import threading
import subprocess


class QueueTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.frame = tk.Frame(parent)
        self.downloader = Downloader()
        self.queue = load_queue()
        self.downloading = False
        self.active_downloads = []
        
        self.build_ui()
    
    def create_context_menu(self, widget):
        """Create right-click context menu for entry widgets"""
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="✂️ Cut", command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="📋 Copy", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="📌 Paste", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="🔍 Select All", command=lambda: widget.select_range(0, tk.END))
        
        def show_menu(event):
            menu.post(event.x_root, event.y_root)
        
        widget.bind("<Button-3>", show_menu)
    
    def get_clipboard_text(self):
        """
        Read clipboard robustly for WSL, native Linux, and Windows.
        Priority:
          1. powershell.exe Get-Clipboard  (WSL1 & WSL2 — reads Windows clipboard directly)
          2. tkinter clipboard_get()       (works under WSLg / native Linux with a display)
          3. xclip / xsel                  (native Linux X11 fallback)
        """
        # 1. WSL: ask Windows PowerShell directly (most reliable in WSL)
        try:
            result = subprocess.run(
                ['powershell.exe', '-NoProfile', '-Command', 'Get-Clipboard'],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

        # 2. tkinter clipboard (works under WSLg with a real display)
        try:
            text = self.frame.clipboard_get()
            if text and text.strip():
                return text.strip()
        except Exception:
            pass

        # 3. xclip
        try:
            result = subprocess.run(
                ['xclip', '-selection', 'clipboard', '-o'],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

        # 4. xsel
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

    def paste_from_clipboard(self):
        """Paste URL from clipboard using the Paste button"""
        url = self.get_clipboard_text()
        if url:
            self.url_var.set(url)
            self.url_entry.icursor(tk.END)
            self.preview()
        else:
            messagebox.showerror(
                "Clipboard Error",
                "Could not read clipboard.\n\n"
                "Try clicking inside the URL box and pressing Ctrl+V,\n"
                "or type/paste the URL manually."
            )
    
    def build_ui(self):
        main_frame = tk.Frame(self.frame, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # URL Input Section with Paste button
        tk.Label(main_frame, text="Video URL:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        
        url_frame = tk.Frame(main_frame)
        url_frame.pack(fill=tk.X, pady=(5, 10))
        
        self.url_var = tk.StringVar()
        self.url_entry = tk.Entry(url_frame, textvariable=self.url_var, width=70, font=('Arial', 10))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.create_context_menu(self.url_entry)

        # Fix Ctrl+V for WSL and Linux:
        # - In WSL, tkinter's default paste can't reach the Windows clipboard.
        # - On native Linux, default paste uses PRIMARY (mouse highlight) not CLIPBOARD.
        # We override it to use get_clipboard_text() which handles both cases.
        def force_paste(event=None):
            text = self.get_clipboard_text()
            if text:
                try:
                    sel_start = self.url_entry.index(tk.SEL_FIRST)
                    sel_end = self.url_entry.index(tk.SEL_LAST)
                    self.url_entry.delete(sel_start, sel_end)
                except tk.TclError:
                    pass
                self.url_entry.insert(tk.INSERT, text)
            return "break"  # Suppress tkinter's default paste

        self.url_entry.bind("<Control-v>", force_paste)
        self.url_entry.bind("<Control-V>", force_paste)
        
        paste_btn = tk.Button(url_frame, text="📋 Paste", command=self.paste_from_clipboard, width=8, bg='#2196F3', fg='white')
        paste_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Save Path
        tk.Label(main_frame, text="Save Path:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        path_frame = tk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=(5, 10))
        
        self.path_var = tk.StringVar()
        self.path_entry = tk.Entry(path_frame, textvariable=self.path_var, width=55, font=('Arial', 10))
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.create_context_menu(self.path_entry)
        
        tk.Button(path_frame, text="Browse", command=self.browse, width=10).pack(side=tk.LEFT, padx=(5, 0))
        
        # Download Options
        options_frame = tk.LabelFrame(main_frame, text="Download Options", padx=10, pady=10)
        options_frame.pack(fill=tk.X, pady=10)
        
        self.audio_only = tk.BooleanVar()
        tk.Checkbutton(options_frame, text="Audio Only (MP3)", variable=self.audio_only, font=('Arial', 10)).pack(anchor=tk.W)
        
        resolution_frame = tk.Frame(options_frame)
        resolution_frame.pack(anchor=tk.W, pady=(5, 0))
        tk.Label(resolution_frame, text="Resolution:", font=('Arial', 10)).pack(side=tk.LEFT)
        self.res_var = tk.StringVar(value="720")
        resolution_combo = ttk.Combobox(resolution_frame, values=RESOLUTIONS, textvariable=self.res_var, width=10, state='readonly')
        resolution_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        # Preview Button
        preview_frame = tk.Frame(main_frame)
        preview_frame.pack(fill=tk.X, pady=10)
        tk.Button(preview_frame, text="Preview Info", command=self.preview, width=15).pack(side=tk.LEFT)
        self.info_label = tk.Label(preview_frame, text="", font=('Arial', 9, 'italic'), fg='gray')
        self.info_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Queue List Section
        queue_label = tk.Label(main_frame, text="Download Queue:", font=('Arial', 10, 'bold'))
        queue_label.pack(anchor=tk.W, pady=(10, 5))
        
        # Queue listbox with scrollbar
        list_frame = tk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.queue_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=8)
        self.queue_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.queue_listbox.yview)
        
        # Queue Control Buttons
        queue_btn_frame = tk.Frame(main_frame)
        queue_btn_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(queue_btn_frame, text="Add to Queue", command=self.add_to_queue, width=12, bg='#2196F3', fg='white').pack(side=tk.LEFT, padx=2)
        tk.Button(queue_btn_frame, text="Remove Selected", command=self.remove_selected, width=12, bg='#f44336', fg='white').pack(side=tk.LEFT, padx=2)
        tk.Button(queue_btn_frame, text="Move Up", command=self.move_up, width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(queue_btn_frame, text="Move Down", command=self.move_down, width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(queue_btn_frame, text="Clear Queue", command=self.clear_queue, width=10).pack(side=tk.LEFT, padx=2)
        
        # Stats Frame
        stats_frame = tk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=5)
        
        self.stats_label = tk.Label(
            stats_frame, 
            text="📊 Total: 0 | ⏳ Pending: 0 | ▶️ Downloading: 0 | ✅ Completed: 0 | ❌ Failed: 0", 
            font=('Arial', 9), 
            fg='gray'
        )
        self.stats_label.pack(side=tk.LEFT)
        
        # Queue Action Buttons
        action_frame = tk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=5)
        
        self.start_btn = tk.Button(action_frame, text="▶ Start Queue", command=self.start_queue, width=12, bg='#4CAF50', fg='white')
        self.start_btn.pack(side=tk.LEFT, padx=2)
        
        self.stop_btn = tk.Button(action_frame, text="⏸ Stop Queue", command=self.stop_queue, width=12, bg='#f44336', fg='white', state='disabled')
        self.stop_btn.pack(side=tk.LEFT, padx=2)
        
        # Progress Section
        progress_frame = tk.LabelFrame(main_frame, text="Current Download", padx=10, pady=10)
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.current_title = tk.Label(progress_frame, text="No active download", font=('Arial', 9, 'italic'))
        self.current_title.pack(anchor=tk.W, pady=(0, 5))
        
        self.percent_label = tk.Label(progress_frame, text="0%", font=('Arial', 10, 'bold'), fg='blue')
        self.percent_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.progress = ttk.Progressbar(progress_frame, length=400, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = tk.Label(progress_frame, text="Ready", font=('Arial', 9))
        self.status_label.pack(anchor=tk.W)
        
        self.speed_label = tk.Label(progress_frame, text="", font=('Arial', 9), fg='blue')
        self.speed_label.pack(anchor=tk.W)
        
        self.eta_label = tk.Label(progress_frame, text="", font=('Arial', 9), fg='green')
        self.eta_label.pack(anchor=tk.W)
    
    def browse(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)
    
    def preview(self):
        if not self.url_var.get():
            messagebox.showwarning("Warning", "Please enter a URL first")
            return
            
        try:
            self.info_label.config(text="Fetching video info...", fg='orange')
            self.frame.update()
            
            info = self.downloader.get_info(self.url_var.get())
            duration = info.get('duration', 0)
            duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else "Unknown"
            self.info_label.config(text=f"📹 {info['title']} ({duration_str})", fg='gray')
        except Exception as e:
            self.info_label.config(text="Failed to fetch info", fg='red')
            messagebox.showerror("Error", f"Failed to fetch video info:\n{str(e)}")
    
    def add_to_queue(self):
        if not self.url_var.get():
            messagebox.showwarning("Warning", "Please enter a video URL")
            return
        
        if not self.path_var.get():
            messagebox.showwarning("Warning", "Please select a save path")
            return
        
        # Apply default settings from app settings
        default_res = self.app.settings.get("default_resolution", "720")
        default_audio = self.app.settings.get("default_audio_only", False)
        
        # If user hasn't changed resolution from default (720), use saved default
        if self.res_var.get() == "720" and default_res != "720":
            self.res_var.set(default_res)
        
        # If audio only not set by user, use saved default
        if not self.audio_only.get() and default_audio:
            self.audio_only.set(True)
        
        # Get video info with better error handling
        try:
            self.info_label.config(text="Fetching video info...", fg='orange')
            self.frame.update()
            info = self.downloader.get_info(self.url_var.get())
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else "Unknown"
            self.info_label.config(text=f"📹 {title} ({duration_str})", fg='gray')
        except Exception as e:
            title = self.url_var.get()[:50]
            self.info_label.config(text="Could not fetch title, using URL", fg='orange')
        
        # Create queue item
        queue_item = {
            "url": self.url_var.get(),
            "path": self.path_var.get(),
            "resolution": self.res_var.get(),
            "audio_only": self.audio_only.get(),
            "title": title,
            "status": "pending",
            "date_added": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Add to queue
        self.queue.append(queue_item)
        save_queue(self.queue)
        self.refresh_queue_display()
        
        # Clear URL and reset to defaults for next input
        self.url_var.set("")
        
        # Reset to saved defaults for next addition
        self.res_var.set(self.app.settings.get("default_resolution", "720"))
        self.audio_only.set(self.app.settings.get("default_audio_only", False))
        
        # Show success message
        messagebox.showinfo("Success", f"Added to queue: {title}\n\nQueue position: {len(self.queue)}")
        
        self.update_stats_display()
    
    def remove_selected(self):
        selection = self.queue_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.queue):
                del self.queue[index]
                save_queue(self.queue)
                self.refresh_queue_display()
                self.update_stats_display()
    
    def move_up(self):
        selection = self.queue_listbox.curselection()
        if selection and selection[0] > 0:
            index = selection[0]
            self.queue[index], self.queue[index-1] = self.queue[index-1], self.queue[index]
            save_queue(self.queue)
            self.refresh_queue_display()
            self.queue_listbox.selection_set(index-1)
            self.update_stats_display()
    
    def move_down(self):
        selection = self.queue_listbox.curselection()
        if selection and selection[0] < len(self.queue) - 1:
            index = selection[0]
            self.queue[index], self.queue[index+1] = self.queue[index+1], self.queue[index]
            save_queue(self.queue)
            self.refresh_queue_display()
            self.queue_listbox.selection_set(index+1)
            self.update_stats_display()
    
    def clear_queue(self):
        if messagebox.askyesno("Clear Queue", "Are you sure you want to clear the entire queue?"):
            self.queue = []
            save_queue(self.queue)
            self.refresh_queue_display()
            self.update_stats_display()
    
    def get_queue_stats(self):
        """Get queue statistics"""
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
        """Update the statistics display"""
        stats = self.get_queue_stats()
        self.stats_label.config(
            text=f"📊 Total: {stats['total']} | ⏳ Pending: {stats['pending']} | "
                 f"▶️ Downloading: {stats['downloading']} | ✅ Completed: {stats['completed']} | ❌ Failed: {stats['failed']}"
        )
    
    def refresh_queue_display(self):
        """Update the queue listbox display with better formatting"""
        self.queue_listbox.delete(0, tk.END)
        for i, item in enumerate(self.queue, 1):
            status = item.get("status", "pending")
            if status == "pending":
                status_icon = "⏳"
            elif status == "downloading":
                status_icon = "▶️"
            elif status == "completed":
                status_icon = "✅"
            elif status == "failed":
                status_icon = "❌"
            else:
                status_icon = "❓"
            
            # Truncate long titles
            title = item.get('title', 'Unknown')
            if len(title) > 50:
                title = title[:47] + "..."
            
            display_text = f"{i:2}. {status_icon} {title} - {item.get('resolution', 'N/A')}"
            if item.get('audio_only'):
                display_text += " (Audio)"
            
            self.queue_listbox.insert(tk.END, display_text)
            
            # Color code based on status
            if status == "completed":
                self.queue_listbox.itemconfig(i-1, fg='green')
            elif status == "failed":
                self.queue_listbox.itemconfig(i-1, fg='red')
            elif status == "downloading":
                self.queue_listbox.itemconfig(i-1, fg='blue')
        
        self.update_stats_display()
    
    def start_queue(self):
        """Start processing the queue"""
        if self.downloading:
            return
        
        # Check if there are pending items
        pending = any(item.get("status") == "pending" for item in self.queue)
        if not pending:
            messagebox.showinfo("Queue Empty", "No pending downloads in queue")
            return
        
        self.downloading = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.status_label.config(text="Queue processing started...")
        
        # Start queue processor in a separate thread
        thread = threading.Thread(target=self.process_queue, daemon=True)
        thread.start()
    
    def stop_queue(self):
        """Stop processing the queue"""
        self.downloading = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.status_label.config(text="Queue stopped by user")
        self.update_stats_display()
    
    def process_queue(self):
        """Process items in the queue one by one"""
        for i, item in enumerate(self.queue):
            if not self.downloading:
                break
            
            if item.get("status") == "pending":
                # Update status to downloading
                item["status"] = "downloading"
                save_queue(self.queue)
                
                # Update UI
                self.frame.after(0, lambda: self.refresh_queue_display())
                self.frame.after(0, lambda t=item['title']: self.current_title.config(text=f"Downloading: {t}"))
                
                # Download the item
                self.download_item(item)
                
                # Wait for download to complete (status will be updated by download_item)
                while item.get("status") == "downloading" and self.downloading:
                    import time
                    time.sleep(0.5)
                    self.frame.after(0, self.update_stats_display)
        
        self.downloading = False
        self.frame.after(0, lambda: self.start_btn.config(state='normal'))
        self.frame.after(0, lambda: self.stop_btn.config(state='disabled'))
        self.frame.after(0, lambda: self.status_label.config(text="Queue processing completed!"))
        self.frame.after(0, lambda: self.current_title.config(text="No active download"))
        self.frame.after(0, self.update_stats_display)
    
    def download_item(self, item):
        """Download a single queue item"""
        download_complete = threading.Event()
        
        def update_progress(data):
            def update():
                if '_percent' in data:
                    percent = data['_percent']
                    self.progress['value'] = percent
                    self.percent_label.config(text=f"{percent:.1f}%")
                elif '_percent_str' in data:
                    percent_str = data['_percent_str'].strip('%')
                    try:
                        percent = float(percent_str)
                        self.progress['value'] = percent
                        self.percent_label.config(text=f"{percent:.1f}%")
                    except ValueError:
                        pass
                
                if '_speed_str' in data and data['_speed_str']:
                    self.speed_label.config(text=f"⚡ {data['_speed_str']}")
                else:
                    self.speed_label.config(text="")
                
                if '_eta_str' in data and data['_eta_str']:
                    self.eta_label.config(text=f"⏱ {data['_eta_str']}")
                else:
                    self.eta_label.config(text="")
                
                if '_downloaded_bytes_str' in data and '_total_bytes_str' in data:
                    self.status_label.config(text=f"Downloading: {data['_downloaded_bytes_str']} / {data['_total_bytes_str']}")
                elif '_percent_str' in data:
                    self.status_label.config(text=f"Downloading: {data['_percent_str']}")
                elif data.get('status') == 'finished':
                    self.status_label.config(text="Processing download...")
            
            self.frame.after(0, update)
        
        def done_callback(msg):
            def finalize():
                if "completed" in msg.lower():
                    item["status"] = "completed"
                    self.status_label.config(text="✅ Download completed!")
                    save_history({
                        "url": item["url"],
                        "resolution": item["resolution"] if not item["audio_only"] else "Audio Only",
                        "status": msg
                    })
                    # Notify app to refresh library tabs
                    self.app.on_download_complete()
                else:
                    item["status"] = "failed"
                    self.status_label.config(text=f"❌ {msg}")
                
                save_queue(self.queue)
                self.refresh_queue_display()
                
                # Reset progress display
                self.progress['value'] = 0
                self.percent_label.config(text="0%")
                self.speed_label.config(text="")
                self.eta_label.config(text="")
                
                download_complete.set()
            
            self.frame.after(0, finalize)
        
        # Create a downloader instance for this item
        downloader = Downloader()
        downloader.download(
            item["url"],
            item["path"],
            item["resolution"],
            update_progress,
            done_callback,
            audio_only=item["audio_only"]
        )
        
        # Wait for download to complete or be cancelled
        download_complete.wait()
    
    def show(self):
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.refresh_queue_display()
        self.update_stats_display()
        # Focus the URL entry for quick pasting
        if hasattr(self, 'url_entry'):
            self.url_entry.focus_set()
    
    def hide(self):
        self.frame.pack_forget()
    
    def apply_theme(self, theme):
        self.frame.configure(bg=theme["bg"])
        for widget in self.frame.winfo_children():
            self.apply_theme_to_widget(widget, theme)
    
    def apply_theme_to_widget(self, widget, theme):
        try:
            if isinstance(widget, (tk.Frame, tk.LabelFrame, tk.Label)):
                widget.configure(bg=theme["bg"])
                if isinstance(widget, tk.Label):
                    current_fg = widget.cget("fg")
                    if current_fg not in ["orange", "red", "gray", "#ffa500", "#ff0000", "#808080", "blue", "green"]:
                        widget.configure(fg=theme["fg"])
            elif isinstance(widget, tk.Button):
                current_bg = widget.cget("bg")
                if current_bg not in ["#2196F3", "#4CAF50", "#f44336", "#4caf50", "#388e3c"]:
                    widget.configure(bg=theme["button_bg"], fg=theme["button_fg"])
            elif isinstance(widget, tk.Entry):
                widget.configure(bg=theme["entry_bg"], fg=theme["entry_fg"])
            elif isinstance(widget, ttk.Combobox):
                pass
        except:
            pass
        
        for child in widget.winfo_children():
            self.apply_theme_to_widget(child, theme)