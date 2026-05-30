import customtkinter as ctk
from ui import App
from theme_manager import theme_manager

# Set default appearance mode to dark (your primary palette)
ctk.set_appearance_mode("dark")

# Apply your custom theme
theme_manager.apply_custom_theme()

root = ctk.CTk()
app = App(root)
root.mainloop()