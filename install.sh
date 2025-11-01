#!/bin/bash
set -e
R='\033[0;31m'
G='\033[0;32m'
Y='\033[1;33m'
B='\033[0;34m'
NC='\033[0m'

info() {
    echo -e "${B}[*]${NC} $1"
}

success() {
    echo -e "${G}[+]${NC} $1"
}

error() {
    echo -e "${R}[-]${NC} $1"
}

warning() {
    echo -e "${Y}[!]${NC} $1"
}

echo -e "${B}ASMR18 Downloader Installer${NC}\n"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
INSTALL_MODE="pip"

if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/setup.py" ] && [ -f "$SCRIPT_DIR/requirements.txt" ] && [ -d "$SCRIPT_DIR/src/asmr18" ]; then
    INSTALL_MODE="local"
    info "Project directory detected - Installing from source"
else
    info "Standalone mode - Installing from pip"
fi

if ! command -v python3 &>/dev/null; then
    error "Python 3 not found!"
    echo "Install: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

PV=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if [ "$(printf '%s\n' "3.8" "$PV" | sort -V | head -n1)" != "3.8" ]; then
    error "Python 3.8+ required! Current: $PV"
    exit 1
fi
success "Python $PV detected"

if command -v ffmpeg &>/dev/null; then
    success "ffmpeg detected"
else
    warning "ffmpeg recommended for faster downloads"
    echo "Install: sudo apt install ffmpeg"
fi

if [ "$EUID" -eq 0 ]; then
    IDIR="/opt/asmr18-downloader"
    BDIR="/usr/local/bin"
else
    IDIR="$HOME/.local/share/asmr18-downloader"
    BDIR="$HOME/.local/bin"
fi

info "Installing to: $IDIR"
mkdir -p "$IDIR" "$BDIR"

if [ "$INSTALL_MODE" = "local" ]; then
    info "Copying source files..."
    cp -r "$SCRIPT_DIR"/* "$IDIR/" 2>/dev/null || true
    
    cd "$IDIR"
    
    info "Creating virtual environment..."
    python3 -m venv venv
    
    info "Activating virtual environment..."
    source venv/bin/activate
    
    info "Upgrading pip..."
    pip install --upgrade pip >/dev/null 2>&1
    
    info "Installing dependencies..."
    pip install -r requirements.txt >/dev/null 2>&1
    
    info "Installing package..."
    pip install -e . >/dev/null 2>&1
    
    info "Creating command wrapper..."
    cat > "$BDIR/asmr18" << 'EOF'
#!/bin/bash
source "$IDIR/venv/bin/activate"
python -m asmr18.cli "$@"
EOF
    sed -i "s|\$IDIR|$IDIR|g" "$BDIR/asmr18"
    
else
    info "Creating virtual environment..."
    cd "$IDIR"
    python3 -m venv venv
    
    info "Activating virtual environment..."
    source venv/bin/activate
    
    info "Upgrading pip..."
    pip install --upgrade pip >/dev/null 2>&1
    
    info "Installing asmr18 from pip..."
    pip install asmr18-downloader >/dev/null 2>&1
    
    if [ $? -ne 0 ]; then
        warning "pip installation failed, trying alternative method..."
        pip install git+https://github.com/yosefario-dev/asmr18.git >/dev/null 2>&1
        
        if [ $? -ne 0 ]; then
            error "Failed to install asmr18-downloader"
            echo ""
            echo "Alternative installation methods:"
            echo "1. Clone the repository and install locally:"
            echo "   git clone https://github.com/yosefario-dev/asmr18.git"
            echo "   cd asmr18"
            echo "   bash install.sh"
            echo ""
            echo "2. Install manually:"
            echo "   pip install asmr18-downloader"
            exit 1
        fi
    fi
    
    info "Creating command wrapper..."
    cat > "$BDIR/asmr18" << 'EOF'
#!/bin/bash
source "$IDIR/venv/bin/activate"
asmr18 "$@"
EOF
    sed -i "s|\$IDIR|$IDIR|g" "$BDIR/asmr18"
fi

chmod +x "$BDIR/asmr18"

if [[ ":$PATH:" != *":$BDIR:"* ]]; then
    echo ""
    warning "$BDIR is not in your PATH"
    info "Add this line to your ~/.bashrc or ~/.zshrc:"
    echo ""
    echo "  export PATH=\"\$PATH:$BDIR\""
    echo ""
    info "Then run: source ~/.bashrc"
    echo ""

    read -p "Add to PATH now? [y/N]: " -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -f "$HOME/.bashrc" ]; then
            echo "export PATH=\"\$PATH:$BDIR\"" >> "$HOME/.bashrc"
            success "Added to ~/.bashrc"
            info "Run: source ~/.bashrc"
        elif [ -f "$HOME/.zshrc" ]; then
            echo "export PATH=\"\$PATH:$BDIR\"" >> "$HOME/.zshrc"
            success "Added to ~/.zshrc"
            info "Run: source ~/.zshrc"
        else
            warning "Could not find shell config file"
        fi
    fi
fi

echo ""
success "Installation complete!"
echo ""
info "Usage: asmr18 \"https://asmr18.fans/boys/rj01439456/\""

if "$BDIR/asmr18" --version &>/dev/null; then
    success "Installation verified!"
else
    error "Installation verification failed!"
    exit 1
fi

if [[ ":$PATH:" == *":$BDIR:"* ]]; then
    echo ""
    success "You can now use: asmr18"
else
    echo ""
    warning "Restart your terminal or run: export PATH=\"\$PATH:$BDIR\""
fi

echo ""
info "Installation Summary:"
echo "  Mode: $INSTALL_MODE"
echo "  Location: $IDIR"
echo "  Command: $BDIR/asmr18"
if [ "$INSTALL_MODE" = "pip" ]; then
    echo "  Source: PyPI/pip"
else
    echo "  Source: Local files"
fi
