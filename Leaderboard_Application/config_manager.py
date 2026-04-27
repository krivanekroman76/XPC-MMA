import os
import sys
import json
from pathlib import Path

class ConfigManager:
    """Manages paths to resources both in development and in .app bundle"""
    
    @staticmethod
    def get_app_data_dir():
        """Get the directory where user config files should be stored"""
        if getattr(sys, 'frozen', False):
            # Running as .app bundle
            # sys.executable is: MyApp.app/Contents/MacOS/MyApp
            app_bundle = ConfigManager._get_app_bundle_path()
            # Return folder containing MyApp.app
            return os.path.dirname(app_bundle)
        else:
            # Development environment - use project root
            return os.path.dirname(os.path.abspath(__file__))
    
    @staticmethod
    def _get_app_bundle_path():
        """Get path to the .app bundle"""
        executable_path = os.path.abspath(sys.executable)
        # Go up: MacOS/MyApp -> Contents/MacOS -> Contents -> MyApp.app
        while executable_path and not executable_path.endswith('.app'):
            executable_path = os.path.dirname(executable_path)
        return executable_path
    
    @staticmethod
    def get_resource_path(relative_path):
        """Get full path to a resource file"""
        base_path = ConfigManager.get_app_data_dir()
        return os.path.join(base_path, relative_path)
    
    @staticmethod
    def load_json(relative_path, default=None):
        """Load a JSON file, with fallback to default"""
        path = ConfigManager.get_resource_path(relative_path)
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                #print(f"Warning: {path} not found")
                return default or {}
        except Exception as e:
            #print(f"Error loading {path}: {e}")
            return default or {}
    
    @staticmethod
    def save_json(relative_path, data):
        """Save data as JSON file"""
        path = ConfigManager.get_resource_path(relative_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            #print(f"Error saving {path}: {e}")
            return False
