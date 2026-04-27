#!/bin/bash
# Build script for creating Leaderboard.app

echo "=========================================="
echo "Leaderboard Application Build Script"
echo "=========================================="
echo ""

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "❌ PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Check if all required packages are installed
echo "Checking dependencies..."
python -c "
import sys
required = ['PySide6', 'firebase_admin', 'requests']
missing = []
for pkg in required:
    try:
        __import__(pkg)
    except ImportError:
        missing.append(pkg)

if missing:
    print(f'❌ Missing packages: {missing}')
    print('Install with: pip install ' + ' '.join(missing))
    sys.exit(1)
else:
    print('✅ All dependencies found')
"

if [ $? -ne 0 ]; then
    echo "Please install missing packages before building."
    exit 1
fi

echo ""
echo "Building Leaderboard.app..."
echo ""

# Run PyInstaller with the spec file
pyinstaller build.spec --distpath ./dist

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Build successful!"
    echo ""
    echo "📦 Copying config files into the app bundle..."
    
    # Create necessary directories inside the .app
    mkdir -p "./dist/StopwatchControl.app/lang"
    mkdir -p "./dist/StopwatchControl.app/themes"
    
    # Copy files to the root of the .app (next to Contents folder)
    cp -r ./lang/* "./dist/StopwatchControl.app/lang/" 2>/dev/null || true
    cp -r ./themes/* "./dist/StopwatchControl.app/themes/" 2>/dev/null || true
    cp firebase-config.json "./dist/StopwatchControl.app/" 2>/dev/null || true
    cp settings.json "./dist/StopwatchControl.app/" 2>/dev/null || true
    cp sport_presets.json "./dist/StopwatchControl.app/" 2>/dev/null || true
    cp categories.json "./dist/StopwatchControl.app/" 2>/dev/null || true
    
    echo "✅ Files copied!"
    echo ""
    echo "Your app is ready at: ./dist/StopwatchControl.app"
    echo ""
    echo "The app is completely self-contained with all config files inside!"
    echo ""
    echo "To run the app:"
    echo "   open ./dist/StopwatchControl.app"
    echo ""
else
    echo "❌ Build failed!"
    exit 1
fi
