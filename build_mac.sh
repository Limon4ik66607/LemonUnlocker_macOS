#!/bin/bash
# Build script for LemonUnlocker macOS
# Run this on a macOS machine with Python 3 installed

set -e

echo "=== LemonUnlocker macOS Build ==="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Please install Python 3."
    exit 1
fi

# Install dependencies
echo "[1/4] Installing dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install PyQt6 requests pyinstaller

# Install and bundle 7-Zip
echo ""
echo "[2/4] Setting up bundled 7-Zip..."

# Install p7zip via Homebrew if not present
if ! command -v 7za &> /dev/null && ! command -v 7z &> /dev/null; then
    echo "Installing p7zip via Homebrew..."
    if command -v brew &> /dev/null; then
        brew install p7zip
    else
        echo "WARNING: Homebrew not found. Please install p7zip manually."
        echo "  Install Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo "  Then run: brew install p7zip"
        exit 1
    fi
fi

# Copy 7za binary to 7z/ directory for bundling
mkdir -p 7z
if command -v 7za &> /dev/null; then
    SZ_BIN=$(which 7za)
elif command -v 7z &> /dev/null; then
    SZ_BIN=$(which 7z)
else
    echo "ERROR: 7z/7za not found after installation."
    exit 1
fi
cp "$SZ_BIN" 7z/7za
chmod +x 7z/7za
echo "Bundled 7za from: $SZ_BIN"

# Build
echo ""
echo "[3/4] Building with PyInstaller..."
python3 -m PyInstaller LemonUnlocker_mac.spec --clean --noconfirm

# Done
echo ""
echo "[4/4] Build complete!"
echo ""
echo "Output: dist/LemonUnlocker.app"
echo ""
echo "To run:"
echo "  open dist/LemonUnlocker.app"
echo ""
echo "To distribute:"
echo "  Create a DMG or zip of the .app bundle"
echo ""
