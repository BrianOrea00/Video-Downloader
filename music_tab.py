import tkinter as tk
from tkinter import ttk, messagebox

class MusicTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.frame = tk.Frame(parent)
        
        label = tk.Label(self.frame, text="Music Tab - Coming Soon", font=('Arial', 14))
        label.pack(expand=True)
        
        info_label = tk.Label(self.frame, text="Will display all downloaded music here", font=('Arial', 10), fg='gray')
        info_label.pack()
    
    def show(self):
        self.frame.pack(fill=tk.BOTH, expand=True)
    
    def hide(self):
        self.frame.pack_forget()
    
    def refresh_list(self):
        pass
    
    def apply_theme(self, theme):
        self.frame.configure(bg=theme["bg"])
        for widget in self.frame.winfo_children():
            widget.configure(bg=theme["bg"], fg=theme["fg"])