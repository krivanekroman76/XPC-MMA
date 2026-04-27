# Leaderboard Application - Build & Deployment Guide

## Overview

This guide explains how to build and deploy your Python Leaderboard application as a macOS .app bundle using PyInstaller and the ConfigManager system.

## Project Structure

```
Leaderboard_Application/
├── config_manager.py          # NEW: Centralized config/resource management
├── build.spec                 # NEW: PyInstaller configuration
├── build.sh                   # NEW: Build automation script
├── main.py                    # Entry point (updated to use ConfigManager)
├── settings.json              # User settings (stays outside .app)
├── firebase-config.json       # Firebase credentials (stays outside .app)
├── sport_presets.json         # Sport configurations (stays outside .app)
├── categories.json            # Category list (stays outside .app)
├── themes/                    # Theme files (bundled in .app)
├── lang/                      # Language files (bundled in .app)
│   ├── en.json
│   ├── cs.json
│   └── fr.json
├── core/                      # Core modules (updated to use ConfigManager)
├── GUI_windows/               # GUI components (updated to use ConfigManager)
└── functions/                 # Cloud functions (not bundled)
```

## What Changed

### New File: `config_manager.py`

Centralized resource management system that:
- Handles paths correctly for both development and .app bundle environments
- Manages JSON file loading/saving
- Automatically handles platform-specific path resolution

**Key Methods:**
- `ConfigManager.get_resource_path(relative_path)` - Get full path to a resource
- `ConfigManager.load_json(filepath, default={})` - Load JSON with fallback
- `ConfigManager.save_json(filepath, data)` - Save JSON to file

### Updated Files

1. **main.py** - Now uses ConfigManager for settings.json and theme paths
2. **GUI_windows/login.py** - Settings loading/saving uses ConfigManager
3. **GUI_windows/pages/race_page.py** - Sport presets and recovery files use ConfigManager
4. **core/firebase_service.py** - Firebase config and language files use ConfigManager

## Building the .app

### Option 1: Using the Build Script (Recommended)

```bash
cd /Users/romankrivanek/AndroidStudioProjects/Leaderboard_Application
./build.sh
```

This script will:
- Verify PyInstaller is installed
- Check all dependencies
- Build Leaderboard.app
- Display build status and next steps

### Option 2: Manual Build

```bash
# Install PyInstaller if not already installed
pip install pyinstaller

# Build using the spec file
pyinstaller build.spec --distpath ./dist

# Result: ./dist/Leaderboard.app
```

## File Placement After Build

The build process creates:
```
dist/
└── Leaderboard.app
```

You must place configuration files **NEXT TO** (not inside) the .app bundle:

```
ApplicationFolder/
├── Leaderboard.app/
├── settings.json              ← Copy or create
├── firebase-config.json       ← Copy your Firebase config
├── sport_presets.json         ← Copy from project root
├── categories.json            ← Copy from project root
└── lang/                       ← Copy from lang/ folder
    ├── en.json
    ├── cs.json
    └── fr.json
```

### Directory Structure After Build

```
dist/
├── Leaderboard.app/
├── _internal/                 # Dependencies (auto-created)
├── settings.json              # CREATE/PLACE HERE
├── firebase-config.json       # CREATE/PLACE HERE
├── sport_presets.json         # COPY FROM PROJECT ROOT
├── categories.json            # COPY FROM PROJECT ROOT
└── lang/                       # COPY FROM PROJECT ROOT
    ├── en.json
    ├── cs.json
    └── fr.json
```

## Running the App

### From Terminal
```bash
open ./dist/Leaderboard.app
```

### From Finder
1. Navigate to `dist/` folder
2. Double-click `Leaderboard.app`

## Configuration Files

### settings.json
User preferences stored outside the app. Can be edited by users:
```json
{
    "theme": "dark-blue",
    "remember_email": false,
    "saved_email": "",
    "lang": "cs"
}
```

### firebase-config.json
Firebase credentials (keep private and outside version control):
```json
{
    "apiKey": "YOUR_API_KEY",
    "projectId": "YOUR_PROJECT_ID"
}
```

### sport_presets.json & categories.json
User-editable sport configurations and categories. Users can modify these files to customize the application.

### lang/ folder
Translation files. Can be extended by adding new language files following the same format.

## Customization

### Adding Application Icons

1. Create an .icns file for your app icon (use https://www.img2icns.com/)
2. Update `build.spec`:
   ```python
   icon='path/to/your/icon.icns',  # In exe and app definitions
   ```
3. Rebuild the app

### Changing Bundle Identifier

Edit `build.spec`:
```python
app = BUNDLE(
    exe,
    name='Leaderboard.app',
    bundle_identifier='com.yourdomain.leaderboard',  # Change this
    ...
)
```

### Adding New Configuration Files

If you add new JSON files that need to be outside the .app:

```python
# In your code:
from core.config_manager import ConfigManager

data = ConfigManager.load_json("my_config.json", default={})
ConfigManager.save_json("my_config.json", data)
```

Update `build.sh` and user documentation to include the new file in the placement instructions.

## Troubleshooting

### "Config file not found" errors

**Solution:** Make sure configuration files are placed OUTSIDE the .app bundle, not inside it.

```bash
# ✅ Correct
dist/Leaderboard.app/
dist/settings.json

# ❌ Wrong
dist/Leaderboard.app/Contents/Resources/settings.json
```

### App can't find themes or language files

**Solution:** The `build.spec` includes these directories. Make sure they exist in your project root before building:
- `themes/` folder with .qss files
- `lang/` folder with .json files

### "Module not found" errors

Add hidden imports to `build.spec`:
```python
hiddenimports=[
    'PySide6',
    'firebase_admin',
    'requests',
    # Add any other modules that aren't auto-detected
],
```

## Development vs. Production

### Development Mode
Running `python main.py` directly:
- Uses `config_manager.py` to find files in project root
- Easy to edit and test

### Production Mode
Running the .app bundle:
- `config_manager.py` detects `.app` and adjusts paths
- Files must be in the folder containing the .app
- Users can edit JSON files outside the bundle

## Tips for Users

1. **Backup your settings:** Keep copies of your JSON files
2. **Never modify files inside the .app:** Edit files in the parent folder
3. **Update files:** Simply replace .json files to update configuration
4. **Themes:** Add new .qss files to `themes/` folder (requires rebuild)

## Next Steps

1. Test the build:
   ```bash
   ./build.sh
   ```

2. Create configuration files:
   ```bash
   cp firebase-config.json dist/
   cp sport_presets.json dist/
   cp categories.json dist/
   cp -r lang dist/
   ```

3. Test the app:
   ```bash
   open dist/Leaderboard.app
   ```

4. For distribution:
   - Zip the `dist/` folder
   - Share with users
   - Include instructions for placing config files

## Support

For issues with:
- **ConfigManager:** Check that file paths are relative to project root
- **PyInstaller:** Review `build.spec` and hidden imports
- **App paths:** Verify config files are in the correct location

---

**Last Updated:** April 2026
**ConfigManager Version:** 1.0
