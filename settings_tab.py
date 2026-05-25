import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from config import RESOLUTIONS
from utils import save_settings

class SettingsTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.frame = tk.Frame(parent)
        
        self.build_ui()
        self.load_settings()
    
    def build_ui(self):
        # Main container with scrollbar
        main_container = tk.Frame(self.frame)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas for scrolling
        canvas = tk.Canvas(main_container, highlightthickness=0)
        scrollbar = tk.Scrollbar(main_container, orient=tk.VERTICAL, command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Main frame inside scrollable area
        main_frame = tk.Frame(self.scrollable_frame, padx=30, pady=30)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(
            main_frame, 
            text="⚙️ Application Settings", 
            font=('Arial', 16, 'bold')
        )
        title_label.pack(anchor=tk.W, pady=(0, 20))
        
        # Download Settings Section
        download_section = tk.LabelFrame(
            main_frame, 
            text="📥 Download Settings", 
            font=('Arial', 12, 'bold'),
            padx=15, 
            pady=15
        )
        download_section.pack(fill=tk.X, pady=(0, 15))
        
        # Download Mode
        self.download_mode_var = tk.StringVar(value="sequential")
        
        mode_frame = tk.Frame(download_section)
        mode_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(mode_frame, text="Download Mode:", font=('Arial', 10), width=20, anchor=tk.W).pack(side=tk.LEFT)
        
        mode_radio_frame = tk.Frame(mode_frame)
        mode_radio_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Radiobutton(
            mode_radio_frame, 
            text="Sequential (one at a time)", 
            variable=self.download_mode_var, 
            value="sequential",
            command=self.on_mode_change
        ).pack(anchor=tk.W)
        
        tk.Radiobutton(
            mode_radio_frame, 
            text="Parallel (multiple downloads)", 
            variable=self.download_mode_var, 
            value="parallel",
            command=self.on_mode_change
        ).pack(anchor=tk.W, pady=(5, 0))
        
        # Parallel Limit (only enabled in parallel mode)
        self.parallel_frame = tk.Frame(download_section)
        self.parallel_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Label(self.parallel_frame, text="Max Parallel Downloads:", font=('Arial', 10), width=20, anchor=tk.W).pack(side=tk.LEFT)
        
        self.parallel_limit_var = tk.IntVar(value=2)
        self.parallel_scale = tk.Scale(
            self.parallel_frame,
            from_=1,
            to=5,
            orient=tk.HORIZONTAL,
            variable=self.parallel_limit_var,
            length=200,
            showvalue=True,
            tickinterval=1,
            resolution=1
        )
        self.parallel_scale.pack(side=tk.LEFT, padx=(10, 0))
        
        self.parallel_limit_label = tk.Label(self.parallel_frame, text="", font=('Arial', 9))
        self.parallel_limit_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Default Options Section
        default_section = tk.LabelFrame(
            main_frame, 
            text="🎬 Default Options", 
            font=('Arial', 12, 'bold'),
            padx=15, 
            pady=15
        )
        default_section.pack(fill=tk.X, pady=(0, 15))
        
        # Default Resolution
        res_frame = tk.Frame(default_section)
        res_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(res_frame, text="Default Resolution:", font=('Arial', 10), width=20, anchor=tk.W).pack(side=tk.LEFT)
        
        self.default_res_var = tk.StringVar(value="720")
        res_combo = ttk.Combobox(
            res_frame, 
            values=RESOLUTIONS, 
            textvariable=self.default_res_var, 
            width=10, 
            state='readonly'
        )
        res_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        # Default Audio Only
        self.default_audio_var = tk.BooleanVar(value=False)
        audio_check = tk.Checkbutton(
            default_section,
            text="Audio Only (MP3) by default",
            variable=self.default_audio_var,
            font=('Arial', 10)
        )
        audio_check.pack(anchor=tk.W, pady=5)
        
        # General Settings Section
        general_section = tk.LabelFrame(
            main_frame, 
            text="🔧 General Settings", 
            font=('Arial', 12, 'bold'),
            padx=15, 
            pady=15
        )
        general_section.pack(fill=tk.X, pady=(0, 15))
        
        # Auto Clipboard
        self.auto_clipboard_var = tk.BooleanVar(value=True)
        clipboard_check = tk.Checkbutton(
            general_section,
            text="Auto-detect URLs from clipboard",
            variable=self.auto_clipboard_var,
            font=('Arial', 10),
            command=self.on_clipboard_toggle
        )
        clipboard_check.pack(anchor=tk.W, pady=5)
        
        # Clipboard Interval
        self.interval_frame = tk.Frame(general_section)
        self.interval_frame.pack(fill=tk.X, pady=5, padx=(20, 0))
        
        tk.Label(self.interval_frame, text="Clipboard check interval:", font=('Arial', 9)).pack(side=tk.LEFT)
        
        self.clipboard_interval_var = tk.IntVar(value=3)
        self.interval_spinbox = tk.Spinbox(
            self.interval_frame,
            from_=1,
            to=10,
            textvariable=self.clipboard_interval_var,
            width=5,
            state='readonly'
        )
        self.interval_spinbox.pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Label(self.interval_frame, text="seconds", font=('Arial', 9)).pack(side=tk.LEFT, padx=(5, 0))
        
        # Theme Section
        theme_section = tk.LabelFrame(
            main_frame, 
            text="🎨 Appearance", 
            font=('Arial', 12, 'bold'),
            padx=15, 
            pady=15
        )
        theme_section.pack(fill=tk.X, pady=(0, 15))
        
        theme_frame = tk.Frame(theme_section)
        theme_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(theme_frame, text="Theme:", font=('Arial', 10), width=20, anchor=tk.W).pack(side=tk.LEFT)
        
        self.theme_var = tk.StringVar(value="light")
        theme_combo = ttk.Combobox(
            theme_frame,
            values=["light", "dark"],
            textvariable=self.theme_var,
            width=10,
            state='readonly'
        )
        theme_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Label(theme_frame, text="(Requires restart for full effect)", font=('Arial', 8), fg='gray').pack(side=tk.LEFT, padx=(10, 0))
        
        # Download Path Section
        path_section = tk.LabelFrame(
            main_frame, 
            text="📁 Storage", 
            font=('Arial', 12, 'bold'),
            padx=15, 
            pady=15
        )
        path_section.pack(fill=tk.X, pady=(0, 20))
        
        path_frame = tk.Frame(path_section)
        path_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(path_frame, text="Download Path:", font=('Arial', 10), width=15, anchor=tk.W).pack(side=tk.LEFT)
        
        self.download_path_var = tk.StringVar()
        path_entry = tk.Entry(path_frame, textvariable=self.download_path_var, width=50)
        path_entry.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        
        tk.Button(
            path_frame,
            text="Browse",
            command=self.browse_path,
            width=8
        ).pack(side=tk.LEFT, padx=(5, 0))
        
        # Action Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(
            button_frame,
            text="💾 Save Settings",
            command=self.save_settings,
            bg='#4CAF50',
            fg='white',
            font=('Arial', 10, 'bold'),
            padx=20,
            pady=5
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_frame,
            text="🔄 Reset to Defaults",
            command=self.reset_defaults,
            bg='#FF9800',
            fg='white',
            font=('Arial', 10),
            padx=20,
            pady=5
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_frame,
            text="❌ Cancel",
            command=self.cancel_settings,
            bg='#f44336',
            fg='white',
            font=('Arial', 10),
            padx=20,
            pady=5
        ).pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = tk.Label(
            main_frame,
            text="",
            font=('Arial', 9),
            fg='green',
            anchor=tk.W
        )
        self.status_label.pack(fill=tk.X, pady=(10, 0))
    
    def browse_path(self):
        """Browse for download folder"""
        folder = filedialog.askdirectory()
        if folder:
            self.download_path_var.set(folder)
    
    def on_mode_change(self):
        """Handle download mode change"""
        if self.download_mode_var.get() == "sequential":
            self.parallel_scale.config(state='disabled')
            self.parallel_limit_label.config(text="(Disabled in sequential mode)")
        else:
            self.parallel_scale.config(state='normal')
            self.parallel_limit_label.config(text="")
    
    def on_clipboard_toggle(self):
        """Handle clipboard toggle"""
        if self.auto_clipboard_var.get():
            self.interval_spinbox.config(state='readonly')
        else:
            self.interval_spinbox.config(state='disabled')
    
    def load_settings(self):
        """Load settings from app settings"""
        settings = self.app.settings
        
        # Download Mode
        mode = settings.get("download_mode", "sequential")
        self.download_mode_var.set(mode)
        self.parallel_limit_var.set(settings.get("parallel_limit", 2))
        
        # Update UI based on mode
        if mode == "sequential":
            self.parallel_scale.config(state='disabled')
            self.parallel_limit_label.config(text="(Disabled in sequential mode)")
        else:
            self.parallel_scale.config(state='normal')
            self.parallel_limit_label.config(text="")
        
        # Default Options
        self.default_res_var.set(settings.get("default_resolution", "720"))
        self.default_audio_var.set(settings.get("default_audio_only", False))
        
        # General Settings
        self.auto_clipboard_var.set(settings.get("auto_clipboard", True))
        self.clipboard_interval_var.set(settings.get("clipboard_interval", 3000) // 1000)
        
        # Theme
        self.theme_var.set(settings.get("theme", "light"))
        
        # Download Path
        if settings.get("download_path"):
            self.download_path_var.set(settings["download_path"])
        elif hasattr(self.app, 'queue_tab'):
            current_path = self.app.queue_tab.path_var.get()
            if current_path:
                self.download_path_var.set(current_path)
        
        # Update clipboard interval UI state
        self.on_clipboard_toggle()
    
    def save_settings(self):
        """Save all settings"""
        try:
            # Update app settings
            self.app.settings["download_mode"] = self.download_mode_var.get()
            self.app.settings["parallel_limit"] = self.parallel_limit_var.get()
            self.app.settings["default_resolution"] = self.default_res_var.get()
            self.app.settings["default_audio_only"] = self.default_audio_var.get()
            self.app.settings["auto_clipboard"] = self.auto_clipboard_var.get()
            self.app.settings["clipboard_interval"] = self.clipboard_interval_var.get() * 1000
            self.app.settings["theme"] = self.theme_var.get()
            
            # Save download path if changed
            if self.download_path_var.get():
                self.app.settings["download_path"] = self.download_path_var.get()
                # Update queue tab path
                if hasattr(self.app, 'queue_tab'):
                    self.app.queue_tab.path_var.set(self.download_path_var.get())
            
            # Save to file
            save_settings(self.app.settings)
            
            # Apply theme if changed
            if self.app.current_theme != self.theme_var.get():
                self.app.current_theme = self.theme_var.get()
                self.app.apply_theme()
                # Update theme button text
                if self.app.current_theme == "light":
                    self.app.theme_btn.config(text="🌙 Dark Mode")
                else:
                    self.app.theme_btn.config(text="☀️ Light Mode")
            
            self.status_label.config(text="✅ Settings saved successfully!", fg='green')
            self.frame.after(3000, lambda: self.status_label.config(text=""))
            
            messagebox.showinfo("Success", "Settings saved successfully!")
            
        except Exception as e:
            self.status_label.config(text=f"❌ Error saving settings: {str(e)}", fg='red')
            messagebox.showerror("Error", f"Failed to save settings:\n{str(e)}")
    
    def reset_defaults(self):
        """Reset all settings to default values"""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to default values?"):
            from config import DEFAULT_SETTINGS
            
            # Reset UI values
            self.download_mode_var.set(DEFAULT_SETTINGS.get("download_mode", "sequential"))
            self.parallel_limit_var.set(DEFAULT_SETTINGS.get("parallel_limit", 2))
            self.default_res_var.set(DEFAULT_SETTINGS.get("default_resolution", "720"))
            self.default_audio_var.set(DEFAULT_SETTINGS.get("default_audio_only", False))
            self.auto_clipboard_var.set(DEFAULT_SETTINGS.get("auto_clipboard", True))
            self.clipboard_interval_var.set(DEFAULT_SETTINGS.get("clipboard_interval", 3000) // 1000)
            self.theme_var.set(DEFAULT_SETTINGS.get("theme", "light"))
            
            # Update UI based on mode
            self.on_mode_change()
            self.on_clipboard_toggle()
            
            self.status_label.config(text="🔄 Settings reset to defaults. Click Save to apply.", fg='orange')
    
    def cancel_settings(self):
        """Cancel changes and reload settings"""
        self.load_settings()
        self.status_label.config(text="Changes cancelled. Reloaded previous settings.", fg='gray')
        self.frame.after(2000, lambda: self.status_label.config(text=""))
    
    def show(self):
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.load_settings()
    
    def hide(self):
        self.frame.pack_forget()
    
    def apply_theme(self, theme):
        """Apply theme to settings tab"""
        self.frame.configure(bg=theme["bg"])
        for widget in self.frame.winfo_children():
            self.apply_theme_to_widget(widget, theme)
    
    def apply_theme_to_widget(self, widget, theme):
        try:
            if isinstance(widget, (tk.Frame, tk.LabelFrame, tk.Label, tk.Canvas)):
                widget.configure(bg=theme["bg"])
                if isinstance(widget, tk.Label):
                    current_fg = widget.cget("fg")
                    if current_fg not in ["orange", "red", "gray", "green", "blue"]:
                        widget.configure(fg=theme["fg"])
            elif isinstance(widget, tk.Button):
                current_bg = widget.cget("bg")
                if current_bg not in ["#4CAF50", "#f44336", "#FF9800", "#2196F3"]:
                    widget.configure(bg=theme["button_bg"], fg=theme["button_fg"])
            elif isinstance(widget, (tk.Entry, tk.Spinbox)):
                widget.configure(bg=theme["entry_bg"], fg=theme["entry_fg"])
        except:
            pass
        
        for child in widget.winfo_children():
            self.apply_theme_to_widget(child, theme)