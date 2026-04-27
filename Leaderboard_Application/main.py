import sys
import os
from PySide6.QtWidgets import QApplication

from core import ConfigManager
from GUI_windows.login import LoginWindow

# Add this: Force the app to use its own location as the starting point
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))
    
def load_theme(app):
    """
    Loads the theme name from settings.json and applies the corresponding .qss file.
    """
    theme_name = "dark-blue" # Default theme if the file or key doesn't exist
    
    # Load settings from ConfigManager
    settings = ConfigManager.load_json("settings.json")
    if settings:
        theme_name = settings.get("theme", "dark-blue")

    # Path to the stylesheet file
    theme_path = ConfigManager.get_resource_path(f"themes/{theme_name}.qss")
    
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