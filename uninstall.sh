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

warning() {
    echo -e "${Y}[!]${NC} $1"
}

error() {
    echo -e "${R}[-]${NC} $1"
}

echo -e "${B}ASMR18 Downloader Uninstaller${NC}\n"

FOUND=0
SYSTEM_INSTALL="/opt/asmr18-downloader"
SYSTEM_BIN="/usr/local/bin/asmr18"
USER_INSTALL="$HOME/.local/share/asmr18-downloader"
USER_BIN="$HOME/.local/bin/asmr18"
CONFIG_DIR="$HOME/.asmr18"

info "Detecting installations..."

if [ -d "$SYSTEM_INSTALL" ] || [ -f "$SYSTEM_BIN" ]; then
    warning "System-wide installation detected"
    warning "Requires root privileges"
    FOUND=1
    INSTALL_TYPE="system"
    INSTALL_DIR="$SYSTEM_INSTALL"
    BIN_FILE="$SYSTEM_BIN"
fi

if [ -d "$USER_INSTALL" ] || [ -f "$USER_BIN" ]; then
    if [ $FOUND -eq 1 ]; then
        warning "Both system and user installations found!"
        echo ""
        echo "1) Remove system installation (requires sudo)"
        echo "2) Remove user installation"
        echo "3) Remove both"
        echo "4) Cancel"
        read -p "Select option [1-4]: " choice
        case $choice in
            1) INSTALL_TYPE="system"; INSTALL_DIR="$SYSTEM_INSTALL"; BIN_FILE="$SYSTEM_BIN" ;;
            2) INSTALL_TYPE="user"; INSTALL_DIR="$USER_INSTALL"; BIN_FILE="$USER_BIN" ;;
            3) INSTALL_TYPE="both" ;;
            *) info "Cancelled"; exit 0 ;;
        esac
    else
        info "User installation detected"
        FOUND=1
        INSTALL_TYPE="user"
        INSTALL_DIR="$USER_INSTALL"
        BIN_FILE="$USER_BIN"
    fi
fi

if [ $FOUND -eq 0 ]; then
    error "No installation found!"
    info "Checked locations:"
    echo "  - $SYSTEM_INSTALL"
    echo "  - $SYSTEM_BIN"
    echo "  - $USER_INSTALL"
    echo "  - $USER_BIN"
    exit 1
fi

echo ""
warning "This will remove ASMR18 Downloader"
if [ "$INSTALL_TYPE" = "system" ] || [ "$INSTALL_TYPE" = "both" ]; then
    warning "System files (may require sudo password)"
fi
read -p "Continue? [y/N]: " -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    info "Cancelled"
    exit 0
fi

remove_installation() {
    local idir=$1
    local bfile=$2
    local needs_sudo=$3

    if [ "$needs_sudo" = "yes" ]; then
        if [ -d "$idir" ]; then
            info "Removing $idir (sudo required)"
            sudo rm -rf "$idir" && success "Installation directory removed" || error "Failed to remove $idir"
        fi
        if [ -f "$bfile" ]; then
            info "Removing $bfile (sudo required)"
            sudo rm -f "$bfile" && success "Command removed" || error "Failed to remove $bfile"
        fi
    else
        if [ -d "$idir" ]; then
            info "Removing $idir"
            rm -rf "$idir" && success "Installation directory removed" || error "Failed to remove $idir"
        fi
        if [ -f "$bfile" ]; then
            info "Removing $bfile"
            rm -f "$bfile" && success "Command removed" || error "Failed to remove $bfile"
        fi
    fi
}

if [ "$INSTALL_TYPE" = "both" ]; then
    info "Removing system installation..."
    remove_installation "$SYSTEM_INSTALL" "$SYSTEM_BIN" "yes"
    echo ""
    info "Removing user installation..."
    remove_installation "$USER_INSTALL" "$USER_BIN" "no"
elif [ "$INSTALL_TYPE" = "system" ]; then
    remove_installation "$SYSTEM_INSTALL" "$SYSTEM_BIN" "yes"
else
    remove_installation "$USER_INSTALL" "$USER_BIN" "no"
fi

DESKTOP_FILE="$HOME/.local/share/applications/asmr18-downloader.desktop"
if [ -f "$DESKTOP_FILE" ]; then
    info "Removing desktop entry"
    rm -f "$DESKTOP_FILE" && success "Desktop entry removed"
fi

if [ -d "$CONFIG_DIR" ]; then
    echo ""
    read -p "Remove configuration directory ($CONFIG_DIR)? [y/N]: " -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$CONFIG_DIR" && success "Configuration removed"
    else
        info "Configuration kept at $CONFIG_DIR"
    fi
fi

echo ""
success "Uninstallation complete!"

if command -v asmr18 &>/dev/null; then
    warning "Command 'asmr18' still found in PATH"
    info "You may need to restart your terminal or run: hash -r"
else
    success "Command 'asmr18' removed from PATH"
fi
