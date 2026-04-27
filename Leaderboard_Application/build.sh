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
    echo "Your app is ready at: ./dist/Leaderboard.app"
    echo ""
    echo "📦 IMPORTANT: Place these files next to the Leaderboard.app folder:"
    echo "   - settings.json"
    echo "   - sport_presets.json"
    echo "   - categories.json"
    echo "   - firebase-config.json"
    echo "   - lang/ (folder with language files)"
    echo ""
    echo "To run the app:"
    echo "   open ./dist/Leaderboard.app"
    echo ""
else
    echo "❌ Build failed!"
    exit 1
fi
