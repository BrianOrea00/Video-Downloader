import customtkinter as ctk
from tkinter import messagebox, filedialog
from config import RESOLUTIONS, DEFAULT_SETTINGS
from utils import save_settings
from icon_manager import icon_manager
from theme_manager import theme_manager
from downloader import Downloader


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
        self.build_section_cookies()  # NEW
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
    
    def build_section_cookies(self):
        """NEW: Cookies section for handling login-required and Cloudflare-protected sites"""
        content = self.create_section_card(self.main_frame, "Cookies (For Login/Protected Sites)")
        
        # Cookie method selection
        method_frame = ctk.CTkFrame(content, fg_color="transparent")
        method_frame.pack(fill="x", pady=8)
        
        method_label = ctk.CTkLabel(
            method_frame,
            text="Cookie Source:",
            width=180,
            anchor="w",
            font=ctk.CTkFont(size=13),
            text_color=theme_manager.get_color("greige")
        )
        method_label.pack(side="left")
        
        method_radio_frame = ctk.CTkFrame(method_frame, fg_color="transparent")
        method_radio_frame.pack(side="right")
        
        self.cookie_method_var = ctk.StringVar(value="none")
        
        none_radio = ctk.CTkRadioButton(
            method_radio_frame,
            text="None",
            variable=self.cookie_method_var,
            value="none",
            command=self.on_cookie_method_change
        )
        none_radio.pack(side="left", padx=(0, 12))
        
        browser_radio = ctk.CTkRadioButton(
            method_radio_frame,
            text="Browser",
            variable=self.cookie_method_var,
            value="browser",
            command=self.on_cookie_method_change
        )
        browser_radio.pack(side="left", padx=(0, 12))
        
        file_radio = ctk.CTkRadioButton(
            method_radio_frame,
            text="Cookies.txt File",
            variable=self.cookie_method_var,
            value="file",
            command=self.on_cookie_method_change
        )
        file_radio.pack(side="left")
        
        # Browser selection (enabled when "browser" is selected)
        self.browser_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.browser_frame.pack(fill="x", pady=8)
        
        browser_label = ctk.CTkLabel(
            self.browser_frame,
            text="Browser:",
            width=180,
            anchor="w",
            font=ctk.CTkFont(size=13),
            text_color=theme_manager.get_color("greige")
        )
        browser_label.pack(side="left")
        
        self.cookie_browser_var = ctk.StringVar(value="chrome")
        browser_combo = ctk.CTkComboBox(
            self.browser_frame,
            values=["chrome", "firefox", "edge", "brave", "opera", "safari"],
            variable=self.cookie_browser_var,
            width=120,
            height=32,
            fg_color=theme_manager.get_color("surface"),
            border_color=theme_manager.get_color("border"),
            button_color=theme_manager.get_color("accent"),
            text_color=theme_manager.get_color("text_primary")
        )
        browser_combo.pack(side="right")
        
        # Cookie file path selection (enabled when "file" is selected)
        self.cookie_file_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.cookie_file_frame.pack(fill="x", pady=8)
        
        file_label = ctk.CTkLabel(
            self.cookie_file_frame,
            text="Cookies.txt Path:",
            width=180,
            anchor="w",
            font=ctk.CTkFont(size=13),
            text_color=theme_manager.get_color("greige")
        )
        file_label.pack(side="left")
        
        file_controls = ctk.CTkFrame(self.cookie_file_frame, fg_color="transparent")
        file_controls.pack(side="right")
        
        self.cookie_file_path_var = ctk.StringVar()
        cookie_file_entry = ctk.CTkEntry(
            file_controls,
            textvariable=self.cookie_file_path_var,
            width=250,
            height=32,
            fg_color=theme_manager.get_color("surface"),
            border_color=theme_manager.get_color("border"),
            text_color=theme_manager.get_color("text_primary"),
            placeholder_text="/path/to/cookies.txt"
        )
        cookie_file_entry.pack(side="left", padx=(0, 8))
        
        browse_cookie_btn = ctk.CTkButton(
            file_controls,
            text="Browse",
            width=80,
            height=32,
            fg_color=theme_manager.get_color("surface"),
            border_width=1,
            border_color=theme_manager.get_color("border"),
            text_color=theme_manager.get_color("muted"),
            hover_color=theme_manager.get_color("card"),
            corner_radius=6,
            command=self.browse_cookie_file
        )
        browse_cookie_btn.pack(side="left")
        
        # Test button row
        test_frame = ctk.CTkFrame(content, fg_color="transparent")
        test_frame.pack(fill="x", pady=(12, 8))
        
        self.test_cookies_btn = ctk.CTkButton(
            test_frame,
            text="Test Cookies",
            fg_color=theme_manager.get_color("surface"),
            border_width=1,
            border_color=theme_manager.get_color("accent"),
            text_color=theme_manager.get_color("accent"),
            height=32,
            width=120,
            corner_radius=6,
            command=self.test_cookies
        )
        self.test_cookies_btn.pack(side="left")
        
        # Test status label
        self.cookie_test_status = ctk.CTkLabel(
            test_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=theme_manager.get_color("greige")
        )
        self.cookie_test_status.pack(side="left", padx=(12, 0))
        
        # Info hint
        info_hint = ctk.CTkLabel(
            content,
            text="ℹ️ Cookies help access login-required content and bypass Cloudflare protection",
            font=ctk.CTkFont(size=11),
            text_color=theme_manager.get_color("muted"),
            anchor="w"
        )
        info_hint.pack(fill="x", pady=(8, 0))
    
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
        folder = filedialog.askdirectory()
        if folder:
            self.download_path_var.set(folder)
    
    def browse_cookie_file(self):
        """Browse for cookies.txt file"""
        file_path = filedialog.askopenfilename(
            title="Select cookies.txt file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            self.cookie_file_path_var.set(file_path)
    
    def on_cookie_method_change(self):
        """Handle cookie method selection changes"""
        method = self.cookie_method_var.get()
        
        # Hide/show browser selection
        if method == "browser":
            self.browser_frame.pack(fill="x", pady=8)
            self.cookie_file_frame.pack_forget()
        elif method == "file":
            self.browser_frame.pack_forget()
            self.cookie_file_frame.pack(fill="x", pady=8)
        else:  # none
            self.browser_frame.pack_forget()
            self.cookie_file_frame.pack_forget()
    
    def on_mode_change(self):
        if self.download_mode_var.get() == "sequential":
            self.parallel_scale.configure(state="disabled")
        else:
            self.parallel_scale.configure(state="normal")
    
    def on_clipboard_toggle(self):
        # Handled by switch state
        pass
    
    def test_cookies(self):
        """Test the current cookie configuration with a test URL"""
        method = self.cookie_method_var.get()
        
        if method == "none":
            messagebox.showinfo("Info", "No cookie method selected. Enable cookies in settings to test.")
            return
        
        # Use a test URL that commonly requires authentication or has restrictions
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        self.cookie_test_status.configure(text="Testing...", text_color=theme_manager.get_color("warning"))
        self.test_cookies_btn.configure(state="disabled")
        self.frame.update()
        
        # Build cookie settings dict
        cookie_settings = {
            "cookie_method": method,
            "cookie_browser": self.cookie_browser_var.get() if method == "browser" else "",
            "cookie_file_path": self.cookie_file_path_var.get() if method == "file" else ""
        }
        
        def run_test():
            try:
                downloader = Downloader()
                info = downloader.get_info(test_url, cookie_settings)
                
                # Success - got info
                title = info.get('title', 'Unknown')
                self.frame.after(0, lambda: self.cookie_test_status.configure(
                    text=f"✓ Success! Cookies working. Retrieved: {title[:50]}...",
                    text_color=theme_manager.get_color("success")
                ))
                self.frame.after(0, lambda: messagebox.showinfo(
                    "Cookie Test Passed",
                    f"Successfully retrieved video info with cookies!\n\nTitle: {title[:100]}"
                ))
            except Exception as e:
                error_msg = str(e)
                self.frame.after(0, lambda: self.cookie_test_status.configure(
                    text=f"✗ Failed: {error_msg[:80]}",
                    text_color=theme_manager.get_color("error")
                ))
                self.frame.after(0, lambda: messagebox.showerror(
                    "Cookie Test Failed",
                    f"Could not retrieve video info with current cookie settings.\n\nError: {error_msg}\n\nMake sure:\n- You are logged into the site in your browser (if using browser method)\n- Your cookies.txt file is valid (if using file method)"
                ))
            finally:
                self.frame.after(0, lambda: self.test_cookies_btn.configure(state="normal"))
        
        import threading
        thread = threading.Thread(target=run_test, daemon=True)
        thread.start()
    
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
        
        # Load cookie settings
        self.cookie_method_var.set(settings.get("cookie_method", "none"))
        self.cookie_browser_var.set(settings.get("cookie_browser", "chrome"))
        self.cookie_file_path_var.set(settings.get("cookie_file_path", ""))
        
        # Update UI visibility based on cookie method
        self.on_cookie_method_change()
        
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
            
            # Save cookie settings
            self.app.settings["cookie_method"] = self.cookie_method_var.get()
            self.app.settings["cookie_browser"] = self.cookie_browser_var.get()
            self.app.settings["cookie_file_path"] = self.cookie_file_path_var.get()

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
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to default values?"):
            self.download_mode_var.set(DEFAULT_SETTINGS.get("download_mode", "sequential"))
            self.parallel_limit_var.set(DEFAULT_SETTINGS.get("parallel_limit", 2))
            self.parallel_limit_value.configure(text=str(DEFAULT_SETTINGS.get("parallel_limit", 2)))
            self.default_res_var.set(DEFAULT_SETTINGS.get("default_resolution", "720"))
            self.default_audio_var.set(DEFAULT_SETTINGS.get("default_audio_only", False))
            self.auto_clipboard_var.set(DEFAULT_SETTINGS.get("auto_clipboard", True))
            self.clipboard_interval_var.set(DEFAULT_SETTINGS.get("clipboard_interval", 3000) // 1000)
            self.theme_var.set(DEFAULT_SETTINGS.get("theme", "dark"))
            
            # Reset cookie settings
            self.cookie_method_var.set(DEFAULT_SETTINGS.get("cookie_method", "none"))
            self.cookie_browser_var.set(DEFAULT_SETTINGS.get("cookie_browser", "chrome"))
            self.cookie_file_path_var.set(DEFAULT_SETTINGS.get("cookie_file_path", ""))
            
            self.on_mode_change()
            self.on_cookie_method_change()
            
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