# main.py
import customtkinter as ctk
from ui import App
from theme_manager import theme_manager
from logger import logger

# Set default appearance mode to dark (your primary palette)
ctk.set_appearance_mode("dark")

# Apply your custom theme
theme_manager.apply_custom_theme()

logger.info("Starting Video Downloader")

root = ctk.CTk()
app = App(root)
root.mainloop()

logger.info("Application closed")
