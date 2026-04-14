import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from downloader import Downloader
from config import RESOLUTIONS
from utils import save_history

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Downloader")
        self.root.geometry("500x400")

        self.downloader = Downloader()

        self.url_var = tk.StringVar()
        self.path_var = tk.StringVar()
        self.res_var = tk.StringVar(value="720")

        self.build_ui()

    def build_ui(self):

        tk.Label(self.root, text="Video URL").pack()
        tk.Entry(self.root, textvariable=self.url_var, width=60).pack(pady=5)

        tk.Label(self.root, text="Save Path").pack()
        frame = tk.Frame(self.root)
        frame.pack()

        tk.Entry(frame, textvariable=self.path_var, width=40).pack(side=tk.LEFT)
        tk.Button(frame, text="Browse", command=self.browse).pack(side=tk.LEFT)

        tk.Label(self.root, text="Resolution").pack()
        ttk.Combobox(self.root, values=RESOLUTIONS, textvariable=self.res_var).pack()

        tk.Button(self.root, text="Preview Info", command=self.preview).pack(pady=5)

        self.info_label = tk.Label(self.root, text="")
        self.info_label.pack()

        self.progress = ttk.Progressbar(self.root, length=300)
        self.progress.pack(pady=10)

        self.status = tk.Label(self.root, text="")
        self.status.pack()

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Download", command=self.start_download).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=5)

    def browse(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)

    def preview(self):
        try:
            info = self.downloader.get_info(self.url_var.get())
            self.info_label.config(text=f"{info['title']} ({info['duration']}s)")
        except:
            messagebox.showerror("Error", "Failed to fetch info")

    def update_progress(self, data):
        percent = data.get('_percent_str', '0%').strip('%')
        try:
            self.progress['value'] = float(percent)
        except:
            pass

        self.status.config(text=f"{data.get('_speed_str','')} ETA: {data.get('_eta_str','')}")

    def done(self, msg):
        messagebox.showinfo("Status", msg)

        save_history({
            "url": self.url_var.get(),
            "status": msg
        })

    def start_download(self):
        self.downloader.download(
            self.url_var.get(),
            self.path_var.get(),
            self.res_var.get(),
            self.update_progress,
            self.done
        )

    def cancel(self):
        self.downloader.cancel()