#!/bin/bash
# Sphero RVR Chat Uninstall Script

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================"
echo "  Sphero RVR Chat Uninstaller"
echo "========================================"
echo ""

# Ask about config files
read -p "Delete configuration and history? (~/.sphero-rvr-chat) [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf ~/.sphero-rvr-chat
    echo -e "  ${GREEN}✓${NC} Configuration deleted"
fi

# Remove virtual environment
if [ -d "$SCRIPT_DIR/.venv" ]; then
    rm -rf "$SCRIPT_DIR/.venv"
    echo -e "  ${GREEN}✓${NC} Virtual environment removed"
fi

# Ask about Ollama
read -p "Uninstall Ollama and models? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v ollama &> /dev/null; then
        # Stop service
        sudo systemctl stop ollama 2>/dev/null || true
        sudo systemctl disable ollama 2>/dev/null || true

        # Remove binary
        sudo rm -f /usr/local/bin/ollama

        # Remove models
        rm -rf ~/.ollama

        echo -e "  ${GREEN}✓${NC} Ollama removed"
    fi
fi

echo ""
echo -e "${GREEN}Uninstallation complete.${NC}"
echo ""
