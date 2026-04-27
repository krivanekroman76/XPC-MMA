import os
import sys
import json

class ConfigManager:
    """
    Manages paths to resources (JSON, QSS, etc.) both in development 
    and inside a macOS .app bundle.
    """

    @staticmethod
    def get_resource_path(relative_path):
        """
        Searches for a resource in multiple locations with the following priority:
        1. Inside the .app bundle (Contents/Resources/) - for bundled assets
        2. Outside the .app bundle (next to the .app file) - for user overrides
        3. PyInstaller temporary folder (_MEIPASS)
        4. Development directory (project root)
        """
        search_paths = []

        if getattr(sys, 'frozen', False):
            # Path to the .app bundle (e.g., /Applications/MyApp.app)
            bundle_path = ConfigManager._get_app_bundle_path()
            
            # 1. INTERNAL: Contents/Resources (Bundled assets like lang/ or themes/)
            search_paths.append(os.path.join(bundle_path, 'Contents', 'Resources'))
            
            # 2. EXTERNAL: Next to the .app (Where users put their own config files)
            search_paths.append(os.path.dirname(bundle_path))
            
            # 3. PYINSTALLER TEMP: _MEIPASS (Fallback for internal packaging)
            if hasattr(sys, '_MEIPASS'):
                search_paths.append(sys._MEIPASS)
        else:
            # DEVELOPMENT MODE: Go up one level from the script folder to project root
            search_paths.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Search through paths and return the first one that exists
        for base in search_paths:
            full_path = os.path.normpath(os.path.join(base, relative_path))
            if os.path.exists(full_path):
                return full_path

        # Fallback for NEW files (e.g., creating a first-time log or setting):
        # We default to the directory next to the .app (search_paths[1] if frozen)
        return os.path.normpath(os.path.join(search_paths[1] if len(search_paths) > 1 else search_paths[0], relative_path))

    @staticmethod
    def _get_app_bundle_path():
        """Returns the absolute path to the .app bundle."""
        executable_path = os.path.abspath(sys.executable)
        # MacOS executable sits in MyApp.app/Contents/MacOS/MyApp
        if ".app" in executable_path:
            path = executable_path
            while not path.endswith(".app") and path != "/":
                path = os.path.dirname(path)
            return path
        return os.path.dirname(executable_path)

    @staticmethod
    def load_json(relative_path, default=None):
        """Loads a JSON file from the best available resource path."""
        path = ConfigManager.get_resource_path(relative_path)
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            print(f"[ConfigManager] Warning: {path} not found.")
            return default if default is not None else {}
        except Exception as e:
            print(f"[ConfigManager] Error loading {path}: {e}")
            return default if default is not None else {}

    @staticmethod
    def save_json(relative_path, data):
        """Saves data as a JSON file, typically next to the .app bundle."""
        path = ConfigManager.get_resource_path(relative_path)
        
        # Security Note: If the path is inside Contents/Resources, macOS might block writing.
        # This ConfigManager logic prefers the external folder for writing if internal isn't forced.
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[ConfigManager] Error saving {path}: {e}")
            return False

    @staticmethod
    def load_text(relative_path):
        """Loads a text-based file (like .qss or .txt) from the resource path."""
        path = ConfigManager.get_resource_path(relative_path)
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            return ""
        except Exception as e:
            print(f"[ConfigManager] Error loading text {path}: {e}")
            return ""