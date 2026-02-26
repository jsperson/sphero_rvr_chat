#!/bin/bash
# Sphero RVR Chat Installation Script
# Installs Ollama, downloads model, and sets up sphero-rvr-chat

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "  Sphero RVR Chat Installer"
echo "========================================"
echo ""

# Detect script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
MODEL="${SPHERO_RVR_CHAT_MODEL:-qwen2.5:7b}"

# -----------------------------------------------------------------------------
# Step 1: System Dependencies
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[1/5]${NC} Checking system dependencies..."

# Check for Python 3.10+
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        echo -e "  ${GREEN}✓${NC} Python $PYTHON_VERSION"
    else
        echo -e "  ${RED}✗${NC} Python $PYTHON_VERSION (need 3.10+)"
        exit 1
    fi
else
    echo -e "  ${RED}✗${NC} Python 3 not found"
    exit 1
fi

# Check for pip
if command -v pip3 &> /dev/null || python3 -m pip --version &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} pip available"
else
    echo -e "  ${RED}✗${NC} pip not found"
    echo "  Install with: sudo apt install python3-pip"
    exit 1
fi

# -----------------------------------------------------------------------------
# Step 2: Install Ollama
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[2/5]${NC} Installing Ollama..."

if command -v ollama &> /dev/null; then
    OLLAMA_VERSION=$(ollama --version 2>/dev/null || echo "unknown")
    echo -e "  ${GREEN}✓${NC} Ollama already installed ($OLLAMA_VERSION)"
else
    echo "  Downloading Ollama installer..."
    curl -fsSL https://ollama.com/install.sh | sh

    if command -v ollama &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} Ollama installed successfully"
    else
        echo -e "  ${RED}✗${NC} Ollama installation failed"
        exit 1
    fi
fi

# -----------------------------------------------------------------------------
# Step 3: Start Ollama and pull model
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[3/5]${NC} Setting up Ollama model ($MODEL)..."

# Check if Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "  Starting Ollama service..."
    # Try systemd first
    if systemctl is-enabled ollama &> /dev/null 2>&1; then
        sudo systemctl start ollama
        sleep 2
    else
        # Start manually in background
        ollama serve &> /dev/null &
        sleep 3
    fi
fi

# Check if model exists
if ollama list 2>/dev/null | grep -q "^${MODEL%:*}"; then
    echo -e "  ${GREEN}✓${NC} Model $MODEL already available"
else
    echo "  Pulling model $MODEL (this may take a while)..."
    ollama pull "$MODEL"

    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}✓${NC} Model $MODEL downloaded"
    else
        echo -e "  ${RED}✗${NC} Failed to download model"
        exit 1
    fi
fi

# -----------------------------------------------------------------------------
# Step 4: Install sphero-rvr-chat
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[4/5]${NC} Installing sphero-rvr-chat..."

cd "$SCRIPT_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate and install
source .venv/bin/activate
echo "  Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -e .

echo -e "  ${GREEN}✓${NC} sphero-rvr-chat installed"

# -----------------------------------------------------------------------------
# Step 5: Verify sphero-rvr-mcp
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[5/5]${NC} Checking sphero-rvr-mcp..."

if command -v sphero-rvr-mcp &> /dev/null || python3 -c "import sphero_rvr_mcp" &> /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} sphero-rvr-mcp available"
else
    echo -e "  ${YELLOW}!${NC} sphero-rvr-mcp not found in PATH"
    echo "  Make sure sphero_rvr_mcp is installed and accessible"
    echo "  You may need to update the mcp_command in ~/.sphero-rvr-chat/config.yaml"
fi

# -----------------------------------------------------------------------------
# Done!
# -----------------------------------------------------------------------------
echo ""
echo "========================================"
echo -e "  ${GREEN}Installation Complete!${NC}"
echo "========================================"
echo ""
echo "To run sphero-rvr-chat:"
echo ""
echo "  cd $SCRIPT_DIR"
echo "  source .venv/bin/activate"
echo "  sphero-rvr-chat"
echo ""
echo "Or add this to your shell profile:"
echo ""
echo "  alias sphero-rvr-chat='$SCRIPT_DIR/.venv/bin/sphero-rvr-chat'"
echo ""
echo "Configuration: ~/.sphero-rvr-chat/config.yaml"
echo "Conversations: ~/.sphero-rvr-chat/history/"
echo ""
