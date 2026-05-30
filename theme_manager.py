import customtkinter as ctk

COLORS = {
    "dark": {
        "bg":             "#000103",   # Void - App background
        "surface":        "#0F3029",   # Deep Forest - Sidebar
        "card":           "#0D1F1B",   # Lifted card - queue items, content panels
        "mid":            "#1B7774",   # Abyss Teal - progress track, inactive badges
        "border":         "#1A3D35",   # Subtle border - edges, dividers
        "accent":         "#2BB2A9",   # Teal - primary buttons, active nav
        "secondary":      "#659E85",   # Sage - section labels, secondary buttons
        "muted":          "#8BA594",   # Dusty Green - icons, muted text
        "greige":         "#B9B9A0",   # Warm Greige - secondary text
        "text_primary":   "#FFFFFF",   # White - primary text
        "error":          "#E05252",
        "success":        "#2BB2A9",
        "warning":        "#F0A500",
    },
    "light": {
        "bg":             "#F2F5F3",   # Mist - App background
        "surface":        "#E8EDE9",   # Seafoam Haze - Sidebar
        "card":           "#FFFFFF",   # White card for light mode
        "border":         "#C9D4CB",   # Pale Sage - Borders
        "hover":          "#A8D8D5",   # Teal Bloom - Hover
        "accent":         "#2BB2A9",   # Teal - Primary buttons
        "mid":            "#A8D8D5",   # Teal Bloom
        "text_secondary": "#4A6B5D",   # Forest - Secondary text
        "text_primary":   "#1A2E28",   # Deep Canopy - Primary text
        "error":          "#C0392B",
        "success":        "#2BB2A9",
        "warning":        "#E67E22",
    }
}

class ThemeManager:

    @staticmethod
    def get_color(color_name):
        current_mode = ctk.get_appearance_mode().lower()
        return COLORS[current_mode].get(color_name, "#000000")

    @staticmethod
    def get_current_theme_colors():
        current_mode = ctk.get_appearance_mode().lower()
        return COLORS[current_mode].copy()

    @staticmethod
    def apply_custom_theme():
        current_mode = ctk.get_appearance_mode().lower()
        c = COLORS[current_mode]

        surface = c.get("surface", c["bg"])
        card = c.get("card", surface)
        border = c.get("border", "#333333")
        tp = c["text_primary"]
        ts = c.get("greige", c.get("text_secondary", "#888888"))
        accent = c["accent"]
        muted = c.get("muted", ts)

        def _set(widget, key, value):
            if widget in ctk.ThemeManager.theme and key in ctk.ThemeManager.theme[widget]:
                ctk.ThemeManager.theme[widget][key] = [value, value]

        # CTkFrame - use card color for content frames
        _set("CTkFrame", "fg_color", card)
        _set("CTkFrame", "border_color", border)

        # CTkButton
        _set("CTkButton", "fg_color", accent)
        _set("CTkButton", "hover_color", surface)
        _set("CTkButton", "text_color", "#FFFFFF")

        # CTkLabel
        _set("CTkLabel", "text_color", tp)

        # CTkEntry
        _set("CTkEntry", "fg_color", surface)
        _set("CTkEntry", "text_color", tp)
        _set("CTkEntry", "border_color", border)
        _set("CTkEntry", "placeholder_text_color", muted)

        # CTkSwitch (replacing checkbox)
        _set("CTkSwitch", "fg_color", muted)
        _set("CTkSwitch", "progress_color", accent)
        _set("CTkSwitch", "button_color", "#FFFFFF")
        _set("CTkSwitch", "text_color", tp)

        # CTkRadioButton
        _set("CTkRadioButton", "fg_color", accent)
        _set("CTkRadioButton", "hover_color", surface)
        _set("CTkRadioButton", "text_color", tp)

        # CTkProgressBar
        _set("CTkProgressBar", "progress_color", accent)
        _set("CTkProgressBar", "fg_color", border)

        # CTkSlider
        _set("CTkSlider", "progress_color", accent)
        _set("CTkSlider", "button_color", accent)
        _set("CTkSlider", "button_hover_color", surface)
        _set("CTkSlider", "fg_color", border)

        # CTkComboBox
        _set("CTkComboBox", "fg_color", surface)
        _set("CTkComboBox", "button_color", accent)
        _set("CTkComboBox", "button_hover_color", surface)
        _set("CTkComboBox", "text_color", tp)
        _set("CTkComboBox", "border_color", border)

        # CTkOptionMenu
        _set("CTkOptionMenu", "fg_color", surface)
        _set("CTkOptionMenu", "button_color", accent)
        _set("CTkOptionMenu", "button_hover_color", surface)
        _set("CTkOptionMenu", "text_color", tp)

        # CTkScrollbar
        _set("CTkScrollbar", "button_color", accent)
        _set("CTkScrollbar", "button_hover_color", surface)

        # CTkTextbox
        _set("CTkTextbox", "fg_color", surface)
        _set("CTkTextbox", "text_color", tp)
        _set("CTkTextbox", "border_color", border)

        # CTkTabview
        _set("CTkTabview", "fg_color", c["bg"])
        _set("CTkTabview", "segmented_button_fg_color", surface)
        _set("CTkTabview", "segmented_button_selected_color", accent)
        _set("CTkTabview", "segmented_button_selected_hover_color", surface)
        _set("CTkTabview", "segmented_button_unselected_color", surface)
        _set("CTkTabview", "segmented_button_unselected_hover_color", card)
        _set("CTkTabview", "text_color", tp)


# Global instance
theme_manager = ThemeManager()