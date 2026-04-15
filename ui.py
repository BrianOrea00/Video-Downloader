import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from downloader import Downloader
from config import RESOLUTIONS
from utils import save_history

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Downloader")
        self.root.geometry("650x550")

        self.downloader = Downloader()
        self.current_download = None
        self.last_percent = 0

        self.url_var = tk.StringVar()
        self.path_var = tk.StringVar()
        self.res_var = tk.StringVar(value="720")
        self.audio_only = tk.BooleanVar()

        self.root.after(1000, self.check_clipboard)
        self.build_ui()

    def build_ui(self):
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="Video URL:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        url_entry = tk.Entry(main_frame, textvariable=self.url_var, width=70, font=('Arial', 10))
        url_entry.pack(fill=tk.X, pady=(5, 10))

        tk.Label(main_frame, text="Save Path:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        path_frame = tk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=(5, 10))
        
        tk.Entry(path_frame, textvariable=self.path_var, width=55, font=('Arial', 10)).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(path_frame, text="Browse", command=self.browse, width=10).pack(side=tk.LEFT, padx=(5, 0))

        options_frame = tk.LabelFrame(main_frame, text="Download Options", padx=10, pady=10)
        options_frame.pack(fill=tk.X, pady=10)
        
        tk.Checkbutton(options_frame, text="Audio Only (MP3)", variable=self.audio_only, font=('Arial', 10)).pack(anchor=tk.W)
        
        resolution_frame = tk.Frame(options_frame)
        resolution_frame.pack(anchor=tk.W, pady=(5, 0))
        tk.Label(resolution_frame, text="Resolution:", font=('Arial', 10)).pack(side=tk.LEFT)
        resolution_combo = ttk.Combobox(resolution_frame, values=RESOLUTIONS, textvariable=self.res_var, width=10, state='readonly')
        resolution_combo.pack(side=tk.LEFT, padx=(10, 0))

        preview_frame = tk.Frame(main_frame)
        preview_frame.pack(fill=tk.X, pady=10)
        tk.Button(preview_frame, text="Preview Info", command=self.preview, width=15).pack(side=tk.LEFT)
        self.info_label = tk.Label(preview_frame, text="", font=('Arial', 9, 'italic'), fg='gray')
        self.info_label.pack(side=tk.LEFT, padx=(10, 0))

        progress_frame = tk.LabelFrame(main_frame, text="Download Progress", padx=10, pady=10)
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.percent_label = tk.Label(progress_frame, text="0%", font=('Arial', 10, 'bold'), fg='blue')
        self.percent_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.progress = ttk.Progressbar(progress_frame, length=400, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(0, 10))
        
        self.status_frame = tk.Frame(progress_frame)
        self.status_frame.pack(fill=tk.X)
        
        self.status_label = tk.Label(self.status_frame, text="Ready", font=('Arial', 9), anchor=tk.W, justify=tk.LEFT)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.speed_label = tk.Label(self.status_frame, text="", font=('Arial', 9), fg='blue')
        self.speed_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.eta_label = tk.Label(self.status_frame, text="", font=('Arial', 9), fg='green')
        self.eta_label.pack(side=tk.RIGHT, padx=(10, 0))

        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Download", command=self.start_download, width=12, bg='#4CAF50', fg='white', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=self.cancel, width=12, bg='#f44336', fg='white', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)

    def browse(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)

    def check_clipboard(self):
        try:
            text = self.root.clipboard_get()
            if "http" in text or "youtu" in text:
                self.url_var.set(text)
        except:
            pass
        self.root.after(3000, self.check_clipboard)

    def preview(self):
        if not self.url_var.get():
            messagebox.showwarning("Warning", "Please enter a URL first")
            return
            
        try:
            self.info_label.config(text="Fetching video info...", fg='orange')
            self.root.update()
            
            info = self.downloader.get_info(self.url_var.get())
            duration = info.get('duration', 0)
            duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else "Unknown"
            self.info_label.config(text=f"📹 {info['title']} ({duration_str})", fg='gray')
        except Exception as e:
            self.info_label.config(text="Failed to fetch info", fg='red')
            messagebox.showerror("Error", f"Failed to fetch video info:\n{str(e)}")

    def update_progress(self, data):
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
            else:
                self.status_label.config(text="Downloading...")
            
            self.root.update_idletasks()
        
        self.root.after(0, update)

    def done(self, msg):
        def show_done():
            if "Error" in msg or "Cancelled" in msg:
                messagebox.showerror("Download Status", msg)
                self.status_label.config(text=f"❌ {msg}")
            else:
                messagebox.showinfo("Download Status", msg)
                self.status_label.config(text=f"✅ {msg}")
            
            self.progress['value'] = 0
            self.percent_label.config(text="0%")
            self.speed_label.config(text="")
            self.eta_label.config(text="")
            
            save_history({
                "url": self.url_var.get(),
                "resolution": self.res_var.get() if not self.audio_only.get() else "Audio Only",
                "status": msg
            })
            
            if "completed" in msg.lower():
                self.url_var.set("")
        
        self.root.after(0, show_done)

    def start_download(self):
        if not self.url_var.get():
            messagebox.showwarning("Warning", "Please enter a video URL")
            return
        
        if not self.path_var.get():
            messagebox.showwarning("Warning", "Please select a save path")
            return
        
        self.progress['value'] = 0
        self.percent_label.config(text="0%")
        self.status_label.config(text="Starting download...")
        self.speed_label.config(text="")
        self.eta_label.config(text="")
        
        self.downloader.download(
            self.url_var.get(),
            self.path_var.get(),
            self.res_var.get(),
            self.update_progress,
            self.done,
            audio_only=self.audio_only.get()
        )

    def cancel(self):
        self.downloader.cancel()
        self.status_label.config(text="Cancelling download...")
