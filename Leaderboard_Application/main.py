import sys
import json
import os
from PySide6.QtWidgets import QApplication

from GUI_windows.login import LoginWindow
from GUI_windows.confirm import AttemptConfirmDialog

def load_theme(app):
    """
    Loads the theme name from settings.json and applies the corresponding .qss file.
    """
    theme_name = "dark-blue" # Default theme if the file or key doesn't exist
    
    # Attempt to load from settings.json
    try:
        if os.path.exists("settings.json"):
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
                theme_name = settings.get("theme", "dark-blue")
    except Exception as e:
        print(f"Error loading settings.json: {e}")

    # Path to the stylesheet file
    theme_path = os.path.join("themes", f"{theme_name}.qss")
    
    # Apply the stylesheet
    if os.path.exists(theme_path):
        with open(theme_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    else:
        print(f"Warning: Theme file '{theme_path}' not found.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Load and apply the theme right at startup
    load_theme(app)
    
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())