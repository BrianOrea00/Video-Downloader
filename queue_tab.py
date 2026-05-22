import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from downloader import Downloader
from config import RESOLUTIONS
from utils import save_history, load_queue, save_queue

class QueueTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.frame = tk.Frame(parent)
        self.downloader = Downloader()
        self.queue = load_queue()
        self.current_downloads = []
        
        self.build_ui()
    
    def build_ui(self):
        main_frame = tk.Frame(self.frame, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # URL Input Section
        tk.Label(main_frame, text="Video URL:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        self.url_var = tk.StringVar()
        url_entry = tk.Entry(main_frame, textvariable=self.url_var, width=70, font=('Arial', 10))
        url_entry.pack(fill=tk.X, pady=(5, 10))
        
        # Save Path
        tk.Label(main_frame, text="Save Path:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        path_frame = tk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=(5, 10))
        
        self.path_var = tk.StringVar()
        tk.Entry(path_frame, textvariable=self.path_var, width=55, font=('Arial', 10)).pack(side=tk.LEFT, fill=tk.X, expand=True)
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
        
        # Progress Section (will be enhanced later)
        progress_frame = tk.LabelFrame(main_frame, text="Current Download", padx=10, pady=10)
        progress_frame.pack(fill=tk.X, pady=10)
        
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
        
        # Get video info
        try:
            info = self.downloader.get_info(self.url_var.get())
            title = info.get('title', 'Unknown')
        except:
            title = self.url_var.get()[:50]
        
        queue_item = {
            "url": self.url_var.get(),
            "path": self.path_var.get(),
            "resolution": self.res_var.get(),
            "audio_only": self.audio_only.get(),
            "title": title,
            "status": "pending"
        }
        
        self.queue.append(queue_item)
        save_queue(self.queue)
        self.refresh_queue_display()
        
        # Clear URL for next input
        self.url_var.set("")
        self.info_label.config(text="")
        
        messagebox.showinfo("Success", f"Added to queue: {title}")
    
    def remove_selected(self):
        selection = self.queue_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.queue):
                del self.queue[index]
                save_queue(self.queue)
                self.refresh_queue_display()
    
    def move_up(self):
        selection = self.queue_listbox.curselection()
        if selection and selection[0] > 0:
            index = selection[0]
            self.queue[index], self.queue[index-1] = self.queue[index-1], self.queue[index]
            save_queue(self.queue)
            self.refresh_queue_display()
            self.queue_listbox.selection_set(index-1)
    
    def move_down(self):
        selection = self.queue_listbox.curselection()
        if selection and selection[0] < len(self.queue) - 1:
            index = selection[0]
            self.queue[index], self.queue[index+1] = self.queue[index+1], self.queue[index]
            save_queue(self.queue)
            self.refresh_queue_display()
            self.queue_listbox.selection_set(index+1)
    
    def clear_queue(self):
        if messagebox.askyesno("Clear Queue", "Are you sure you want to clear the entire queue?"):
            self.queue = []
            save_queue(self.queue)
            self.refresh_queue_display()
    
    def refresh_queue_display(self):
        self.queue_listbox.delete(0, tk.END)
        for item in self.queue:
            status_icon = "⏳" if item.get("status") == "pending" else "✅" if item.get("status") == "completed" else "❌"
            display_text = f"{status_icon} {item.get('title', 'Unknown')} - {item.get('resolution', 'N/A')}"
            if item.get('audio_only'):
                display_text += " (Audio)"
            self.queue_listbox.insert(tk.END, display_text)
    
    def show(self):
        self.frame.pack(fill=tk.BOTH, expand=True)
    
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
                    # Only change fg if it's not a special color
                    current_fg = widget.cget("fg")
                    if current_fg not in ["orange", "red", "gray", "#ffa500", "#ff0000", "#808080"]:
                        widget.configure(fg=theme["fg"])
            elif isinstance(widget, tk.Button):
                current_bg = widget.cget("bg")
                # Don't change colored buttons (blue, green, red)
                if current_bg not in ["#2196F3", "#4CAF50", "#f44336", "#4caf50", "#388e3c"]:
                    widget.configure(bg=theme["button_bg"], fg=theme["button_fg"])
            elif isinstance(widget, tk.Entry):
                widget.configure(bg=theme["entry_bg"], fg=theme["entry_fg"])
            elif isinstance(widget, ttk.Combobox):
                # Skip ttk widgets as they handle styling differently
                pass
        except:
            pass
        
        for child in widget.winfo_children():
            self.apply_theme_to_widget(child, theme)