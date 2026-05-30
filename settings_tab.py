import customtkinter as ctk
from tkinter import messagebox
from config import RESOLUTIONS
from utils import save_settings
from icon_manager import icon_manager
from theme_manager import theme_manager


class SettingsTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        
        self.build_ui()
        self.load_settings()
    
    def build_ui(self):
        # Main scrollable container
        self.main_frame = ctk.CTkScrollableFrame(
            self.frame,
            fg_color="transparent",
            scrollbar_button_color=theme_manager.get_color("accent"),
            scrollbar_button_hover_color=theme_manager.get_color("surface")
        )
        self.main_frame.pack(fill="both", expand=True)
        
        # Settings sections
        self.build_section_download()
        self.build_section_defaults()
        self.build_section_general()
        self.build_section_appearance()
        self.build_section_path()
        self.build_action_buttons()
    
    def create_section_card(self, parent, title):
        """Create a styled section card"""
        card = ctk.CTkFrame(
            parent,
            fg_color=theme_manager.get_color("card"),
            border_width=1,
            border_color=theme_manager.get_color("border"),
            corner_radius=10
        )
        card.pack(fill="x", pady=(0, 16))
        
        # Header strip
        header = ctk.CTkFrame(
            card,
            height=36,
            fg_color=theme_manager.get_color("surface"),
            corner_radius=0
        )
        header.pack(fill="x")
        header.pack_propagate(False)
        
        title_label = ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=theme_manager.get_color("text_primary")
        )
        title_label.pack(side="left", padx=14, pady=8)
        
        # Divider
        divider = ctk.CTkFrame(
            card,
            height=1,
            fg_color=theme_manager.get_color("border"),
            corner_radius=0
        )
        divider.pack(fill="x")
        
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=14, pady=12)
        
        return content
    
    def create_row(self, parent, label_text, control_widget):
        """Create a labeled settings row"""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=8)
        
        label = ctk.CTkLabel(
            row,
            text=label_text,
            width=180,
            anchor="w",
            font=ctk.CTkFont(size=13),
            text_color=theme_manager.get_color("greige")
        )
        label.pack(side="left")
        
        control_widget.pack(side="right")
        
        return row
    
    def build_section_download(self):
        content = self.create_section_card(self.main_frame, "Download Settings")
        
        # Download Mode using radio buttons
        mode_frame = ctk.CTkFrame(content, fg_color="transparent")
        mode_frame.pack(fill="x", pady=8)
        
        mode_label = ctk.CTkLabel(
            mode_frame,
            text="Download Mode:",
            width=180,
            anchor="w",
            font=ctk.CTkFont(size=13),
            text_color=theme_manager.get_color("greige")
        )
        mode_label.pack(side="left")
        
        mode_radio_frame = ctk.CTkFrame(mode_frame, fg_color="transparent")
        mode_radio_frame.pack(side="right")
        
        self.download_mode_var = ctk.StringVar(value="sequential")
        
        sequential_radio = ctk.CTkRadioButton(
            mode_radio_frame,
            text="Sequential",
            variable=self.download_mode_var,
            value="sequential",
            command=self.on_mode_change
        )
        sequential_radio.pack(side="left", padx=(0, 12))
        
        parallel_radio = ctk.CTkRadioButton(
            mode_radio_frame,
            text="Parallel",
            variable=self.download_mode_var,
            value="parallel",
            command=self.on_mode_change
        )
        parallel_radio.pack(side="left")
        
        # Parallel Limit
        self.parallel_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.parallel_frame.pack(fill="x", pady=8)
        
        limit_label = ctk.CTkLabel(
            self.parallel_frame,
            text="Max Parallel Downloads:",
            width=180,
            anchor="w",
            font=ctk.CTkFont(size=13),
            text_color=theme_manager.get_color("greige")
        )
        limit_label.pack(side="left")
        
        slider_frame = ctk.CTkFrame(self.parallel_frame, fg_color="transparent")
        slider_frame.pack(side="right")
        
        self.parallel_limit_var = ctk.IntVar(value=2)
        self.parallel_scale = ctk.CTkSlider(
            slider_frame,
            from_=1,
            to=5,
            number_of_steps=4,
            variable=self.parallel_limit_var,
            width=150,
            height=4,
            button_color=theme_manager.get_color("accent"),
            progress_color=theme_manager.get_color("accent"),
            fg_color=theme_manager.get_color("border")
        )
        self.parallel_scale.pack(side="left")
        
        self.parallel_limit_value = ctk.CTkLabel(
            slider_frame,
            text="2",
            width=30,
            font=ctk.CTkFont(size=13),
            text_color=theme_manager.get_color("text_primary")
        )
        self.parallel_limit_value.pack(side="left", padx=(8, 0))
        
        def update_parallel_value(value):
            self.parallel_limit_value.configure(text=str(int(value)))
        
        self.parallel_scale.configure(command=update_parallel_value)
    
    def build_section_defaults(self):
        content = self.create_section_card(self.main_frame, "Default Options")
        
        # Default Resolution
        res_combo = ctk.CTkComboBox(
            content,
            values=RESOLUTIONS,
            width=120,
            height=32,
            fg_color=theme_manager.get_color("surface"),
            border_color=theme_manager.get_color("border"),
            button_color=theme_manager.get_color("accent"),
            text_color=theme_manager.get_color("text_primary")
        )
        self.default_res_var = ctk.StringVar(value="720")
        res_combo.configure(variable=self.default_res_var)
        self.create_row(content, "Default Resolution:", res_combo)
        
        # Default Audio Only (Switch instead of Checkbox)
        self.default_audio_var = ctk.BooleanVar(value=False)
        audio_switch = ctk.CTkSwitch(
            content,
            text="",
            variable=self.default_audio_var,
            fg_color=theme_manager.get_color("muted"),
            progress_color=theme_manager.get_color("accent"),
            button_color="#FFFFFF"
        )
        self.create_row(content, "Audio Only (MP3) by default:", audio_switch)
    
    def build_section_general(self):
        content = self.create_section_card(self.main_frame, "General Settings")
        
        # Auto Clipboard (Switch)
        self.auto_clipboard_var = ctk.BooleanVar(value=True)
        clipboard_switch = ctk.CTkSwitch(
            content,
            text="",
            variable=self.auto_clipboard_var,
            command=self.on_clipboard_toggle,
            fg_color=theme_manager.get_color("muted"),
            progress_color=theme_manager.get_color("accent"),
            button_color="#FFFFFF"
        )
        self.create_row(content, "Auto-detect URLs from clipboard:", clipboard_switch)
        
        # Clipboard Interval
        self.interval_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.interval_frame.pack(fill="x", pady=8)
        
        interval_label = ctk.CTkLabel(
            self.interval_frame,
            text="Clipboard check interval:",
            width=180,
            anchor="w",
            font=ctk.CTkFont(size=13),
            text_color=theme_manager.get_color("greige")
        )
        interval_label.pack(side="left")
        
        interval_control = ctk.CTkFrame(self.interval_frame, fg_color="transparent")
        interval_control.pack(side="right")
        
        self.clipboard_interval_var = ctk.IntVar(value=3)
        interval_spinbox = ctk.CTkEntry(
            interval_control,
            textvariable=self.clipboard_interval_var,
            width=60,
            height=32,
            fg_color=theme_manager.get_color("surface"),
            border_color=theme_manager.get_color("border"),
            text_color=theme_manager.get_color("text_primary")
        )
        interval_spinbox.pack(side="left", padx=(0, 8))
        
        interval_unit = ctk.CTkLabel(
            interval_control,
            text="seconds",
            font=ctk.CTkFont(size=12),
            text_color=theme_manager.get_color("muted")
        )
        interval_unit.pack(side="left")
    
    def build_section_appearance(self):
        content = self.create_section_card(self.main_frame, "Appearance")
        
        # Theme
        theme_combo = ctk.CTkComboBox(
            content,
            values=["light", "dark"],
            width=120,
            height=32,
            fg_color=theme_manager.get_color("surface"),
            border_color=theme_manager.get_color("border"),
            button_color=theme_manager.get_color("accent"),
            text_color=theme_manager.get_color("text_primary")
        )
        self.theme_var = ctk.StringVar(value="dark")
        theme_combo.configure(variable=self.theme_var)
        self.create_row(content, "Theme:", theme_combo)
    
    def build_section_path(self):
        content = self.create_section_card(self.main_frame, "Storage")
        
        path_row = ctk.CTkFrame(content, fg_color="transparent")
        path_row.pack(fill="x", pady=8)
        
        path_label = ctk.CTkLabel(
            path_row,
            text="Download Path:",
            width=180,
            anchor="w",
            font=ctk.CTkFont(size=13),
            text_color=theme_manager.get_color("greige")
        )
        path_label.pack(side="left")
        
        path_controls = ctk.CTkFrame(path_row, fg_color="transparent")
        path_controls.pack(side="right")
        
        self.download_path_var = ctk.StringVar()
        path_entry = ctk.CTkEntry(
            path_controls,
            textvariable=self.download_path_var,
            width=300,
            height=32,
            fg_color=theme_manager.get_color("surface"),
            border_color=theme_manager.get_color("border"),
            text_color=theme_manager.get_color("text_primary"),
            placeholder_text="Select download folder..."
        )
        path_entry.pack(side="left", padx=(0, 8))
        
        browse_btn = ctk.CTkButton(
            path_controls,
            text="Browse",
            width=80,
            height=32,
            fg_color=theme_manager.get_color("surface"),
            border_width=1,
            border_color=theme_manager.get_color("border"),
            text_color=theme_manager.get_color("muted"),
            hover_color=theme_manager.get_color("card"),
            corner_radius=6,
            command=self.browse_path
        )
        browse_btn.pack(side="left")
    
    def build_action_buttons(self):
        button_card = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent"
        )
        button_card.pack(fill="x", pady=(0, 0))
        
        button_row = ctk.CTkFrame(button_card, fg_color="transparent")
        button_row.pack()
        
        save_btn = ctk.CTkButton(
            button_row,
            text="Save Settings",
            fg_color=theme_manager.get_color("accent"),
            text_color="#FFFFFF",
            height=36,
            width=130,
            corner_radius=6,
            command=self.save_settings
        )
        save_btn.pack(side="left", padx=6)
        
        reset_btn = ctk.CTkButton(
            button_row,
            text="Reset",
            fg_color=theme_manager.get_color("surface"),
            border_width=1,
            border_color=theme_manager.get_color("warning"),
            text_color=theme_manager.get_color("warning"),
            height=36,
            width=100,
            corner_radius=6,
            command=self.reset_defaults
        )
        reset_btn.pack(side="left", padx=6)
        
        cancel_btn = ctk.CTkButton(
            button_row,
            text="Cancel",
            fg_color=theme_manager.get_color("surface"),
            border_width=1,
            border_color=theme_manager.get_color("border"),
            text_color=theme_manager.get_color("greige"),
            height=36,
            width=100,
            corner_radius=6,
            command=self.cancel_settings
        )
        cancel_btn.pack(side="left", padx=6)
        
        # Status feedback
        self.status_label = ctk.CTkLabel(
            button_card,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=theme_manager.get_color("success")
        )
        self.status_label.pack(pady=(12, 0))
    
    def browse_path(self):
        from tkinter import filedialog
        folder = filedialog.askdirectory()
        if folder:
            self.download_path_var.set(folder)
    
    def on_mode_change(self):
        if self.download_mode_var.get() == "sequential":
            self.parallel_scale.configure(state="disabled")
        else:
            self.parallel_scale.configure(state="normal")
    
    def on_clipboard_toggle(self):
        # Handled by switch state
        pass
    
    def load_settings(self):
        settings = self.app.settings
        
        mode = settings.get("download_mode", "sequential")
        self.download_mode_var.set(mode)
        self.parallel_limit_var.set(settings.get("parallel_limit", 2))
        self.parallel_limit_value.configure(text=str(settings.get("parallel_limit", 2)))
        
        if mode == "sequential":
            self.parallel_scale.configure(state="disabled")
        else:
            self.parallel_scale.configure(state="normal")
        
        self.default_res_var.set(settings.get("default_resolution", "720"))
        self.default_audio_var.set(settings.get("default_audio_only", False))
        self.auto_clipboard_var.set(settings.get("auto_clipboard", True))
        self.clipboard_interval_var.set(settings.get("clipboard_interval", 3000) // 1000)
        self.theme_var.set(settings.get("theme", "dark"))
        
        if settings.get("download_path"):
            self.download_path_var.set(settings["download_path"])
        elif hasattr(self.app, 'queue_tab'):
            current_path = self.app.queue_tab.path_var.get()
            if current_path:
                self.download_path_var.set(current_path)
    
    def save_settings(self):
        try:
            self.app.settings["download_mode"] = self.download_mode_var.get()
            self.app.settings["parallel_limit"] = self.parallel_limit_var.get()
            self.app.settings["default_resolution"] = self.default_res_var.get()
            self.app.settings["default_audio_only"] = self.default_audio_var.get()
            self.app.settings["auto_clipboard"] = self.auto_clipboard_var.get()
            self.app.settings["clipboard_interval"] = self.clipboard_interval_var.get() * 1000

            theme_changed = self.app.current_theme != self.theme_var.get()

            if self.download_path_var.get():
                self.app.settings["download_path"] = self.download_path_var.get()

            save_settings(self.app.settings)

            messagebox.showinfo("Success", "Settings saved successfully!")

            # Do the rebuild last — it destroys this tab's widgets
            if theme_changed:
                self.app.toggle_theme()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings:\n{str(e)}")
    
    def reset_defaults(self):
        from config import DEFAULT_SETTINGS
        
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to default values?"):
            self.download_mode_var.set(DEFAULT_SETTINGS.get("download_mode", "sequential"))
            self.parallel_limit_var.set(DEFAULT_SETTINGS.get("parallel_limit", 2))
            self.parallel_limit_value.configure(text=str(DEFAULT_SETTINGS.get("parallel_limit", 2)))
            self.default_res_var.set(DEFAULT_SETTINGS.get("default_resolution", "720"))
            self.default_audio_var.set(DEFAULT_SETTINGS.get("default_audio_only", False))
            self.auto_clipboard_var.set(DEFAULT_SETTINGS.get("auto_clipboard", True))
            self.clipboard_interval_var.set(DEFAULT_SETTINGS.get("clipboard_interval", 3000) // 1000)
            self.theme_var.set(DEFAULT_SETTINGS.get("theme", "dark"))
            
            self.on_mode_change()
            
            self.status_label.configure(text="Settings reset to defaults. Click Save to apply.", text_color=theme_manager.get_color("warning"))
    
    def cancel_settings(self):
        self.load_settings()
        self.status_label.configure(text="Changes cancelled.", text_color=theme_manager.get_color("greige"))
        self.frame.after(2000, lambda: self.status_label.configure(text=""))
    
    def show(self):
        self.frame.pack(fill="both", expand=True)
        self.load_settings()
    
    def hide(self):
        self.frame.pack_forget()