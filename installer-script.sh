#!/bin/bash

# Colors for messages
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1;37m'
NC='\033[0m' # No Color
CHECK_MARK="${GREEN}✓${NC}"
CROSS_MARK="${RED}✗${NC}"

# Define paths
SCRIPT_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/gmail-notifier"
DESKTOP_FILE="$HOME/.config/autostart/gmail-notifier.desktop"
SCRIPT_PATH="$SCRIPT_DIR/gmail-notifier"
VENV_DIR="$CONFIG_DIR/venv"

# Show banner
show_banner() {
    cat << EOF
╔═════════════════════════════════════════════════════════╗
║                ⚡ GMAIL NOTIFIER FOR KDE ⚡             ║
║                                                         ║
║          _____                _ _                       ║
║         / ____|              (_) |                      ║
║        | |  __  _ __ ___   __ _| |                      ║
║        | | |_ || '_ \` _ \\ / _\` | |                      ║
║        | |__| || | | | | | (_| | |                      ║
║         \\_____||_| |_| |_|\\__,_|_|                      ║
║                                                         ║
║  ┌─────────┐  ┌─────────┐  ┌─────────┐                  ║
║  │ Google  │  │Workspace│  │  KDE    │                  ║
║  │ Monitor │  │ Notifier│  │ System  │                  ║
║  └─────────┘  └─────────┘  └─────────┘                  ║
║                                                         ║
║  📬 Monitor your Google Workspace email                ║
║  🔔 System tray notifications                          ║
║  🚀 No need to keep an email client open               ║
║  🔒 Secure password storage via system keyring            ║
║  🛠️ Github: https://github.com/utajum/gmail-notifier      ║
║  👨‍💻 Maintained & Enhanced by: utajum macedonia            ║
║     (Forked from P4NX0S © 2025 - CHILE)                  ║
║                                                         ║
╚═════════════════════════════════════════════════════════╝
EOF
}

# Show help
show_help() {
    cat << EOF
${CYAN}USAGE:${NC}
  $0 [OPTION]

${CYAN}DESCRIPTION:${NC}
  Installation/uninstallation script for Gmail Notifier.
  Automatically monitors your Google Workspace email and displays notifications.

${CYAN}OPTIONS:${NC}
  No arguments      Installs Gmail Notifier on the system
  -h, --help         Shows this help message
  -r, --remove       Uninstalls Gmail Notifier from the system
  -u, --uninstall    Alias for --remove

${CYAN}EXAMPLES:${NC}
  $0                 Installs Gmail Notifier
  $0 --help          Shows this help message
  $0 --remove        Uninstalls Gmail Notifier

${CYAN}NOTES:${NC}
  - A Python virtual environment is used to avoid conflicts with the system
  - You need an app password for your Google account
  - You can find the application icon in the system tray
EOF
}

# Stop running Gmail Notifier processes
stop_running_instances() {
    # Use specific patterns to avoid killing unrelated processes
    local patterns=("python.*gmail_notifier" "python.*gmail-notifier" "gmail-notifier$")
    local found=0
    
    for pattern in "${patterns[@]}"; do
        if pgrep -f "$pattern" > /dev/null 2>&1; then
            found=1
            break
        fi
    done
    
    if [ $found -eq 1 ]; then
        echo -e "${BLUE}Stopping running Gmail Notifier instances...${NC}"
        
        # Try graceful termination first
        for pattern in "${patterns[@]}"; do
            pkill -f "$pattern" 2>/dev/null
        done
        
        # Wait up to 5 seconds for processes to terminate
        local waited=0
        while [ $waited -lt 5 ]; do
            local still_running=0
            for pattern in "${patterns[@]}"; do
                if pgrep -f "$pattern" > /dev/null 2>&1; then
                    still_running=1
                    break
                fi
            done
            
            if [ $still_running -eq 0 ]; then
                echo -e "  ${CHECK_MARK} Gmail Notifier stopped"
                return 0
            fi
            
            sleep 1
            waited=$((waited + 1))
        done
        
        # Force kill if still running
        echo -e "${YELLOW}Process didn't terminate gracefully, forcing...${NC}"
        for pattern in "${patterns[@]}"; do
            pkill -9 -f "$pattern" 2>/dev/null
        done
        sleep 1
        echo -e "  ${CHECK_MARK} Gmail Notifier force stopped"
    else
        echo -e "${BLUE}No running Gmail Notifier instances found.${NC}"
    fi
}

# Uninstall function
uninstall() {
    echo -e "${YELLOW}===== Uninstalling Gmail Notifier =====${NC}"
    
    # Stop any running instances
    stop_running_instances
    
    # Remove files and directories
    echo -e "${BLUE}Removing files...${NC}"
    
    # Remove scripts
    if [ -f "$SCRIPT_PATH" ]; then
        rm "$SCRIPT_PATH"
        echo -e "  ${CHECK_MARK} Wrapper script removed"
    else
        echo -e "  ${CROSS_MARK} Wrapper script not found"
    fi
    
    if [ -f "$CONFIG_DIR/gmail-notifier.py" ]; then
        rm "$CONFIG_DIR/gmail-notifier.py"
        echo -e "  ${CHECK_MARK} Main script removed"
    else
        echo -e "  ${CROSS_MARK} Main script not found"
    fi
    
    # Remove package directory
    if [ -d "$CONFIG_DIR/gmail_notifier" ]; then
        rm -rf "$CONFIG_DIR/gmail_notifier"
        echo -e "  ${CHECK_MARK} Package directory removed"
    else
        echo -e "  ${CROSS_MARK} Package directory not found"
    fi
    
    # Remove desktop file
    if [ -f "$DESKTOP_FILE" ]; then
        rm "$DESKTOP_FILE"
        echo -e "  ${CHECK_MARK} Autostart file removed"
    else
        echo -e "  ${CROSS_MARK} Autostart file not found"
    fi
    
    # Remove start menu desktop file
    if [ -f "$HOME/.local/share/applications/gmail-notifier.desktop" ]; then
        rm "$HOME/.local/share/applications/gmail-notifier.desktop"
        echo -e "  ${CHECK_MARK} Start menu file removed"
    else
        echo -e "  ${CROSS_MARK} Start menu file not found"
    fi
    
    # Remove configuration directory
    if [ -d "$CONFIG_DIR" ]; then
        echo -e "${YELLOW}Do you want to delete all configuration data including your credentials? (y/n)${NC}"
        read -r DELETE_CONFIG
        
        if [[ "$DELETE_CONFIG" =~ ^[Yy]$ ]]; then
            rm -rf "$CONFIG_DIR"
            echo -e "  ${CHECK_MARK} Configuration directory removed"
        else
            echo -e "  ${CHECK_MARK} Configuration directory kept at $CONFIG_DIR"
            
            # Remove only the virtual environment
            if [ -d "$VENV_DIR" ]; then
                rm -rf "$VENV_DIR"
                echo -e "  ${CHECK_MARK} Virtual environment removed"
            else
                echo -e "  ${CROSS_MARK} Virtual environment not found"
            fi
        fi
    else
        echo -e "  ${CROSS_MARK} Configuration directory not found"
    fi
    
    echo -e "${GREEN}Uninstallation completed. Gmail Notifier has been removed from the system.${NC}"
    
    # Show banner at the end
    echo
    show_banner
    
    exit 0
}

# Installation function
install() {
    # Stop any running instances of Gmail Notifier
    stop_running_instances

    # Check system dependencies
    echo -e "${BLUE}Checking system dependencies...${NC}"
    echo

    # Detect package manager
    if command -v pacman &> /dev/null; then
        PKG_MANAGER="pacman"
        DEPS=("python" "python-virtualenv" "python-pyqt5")
        CHECK_CMD="pacman -Q"
        INSTALL_CMD="sudo pacman -S --needed"
    elif command -v apt-get &> /dev/null; then
        PKG_MANAGER="apt"
        DEPS=("python3" "python3-venv" "python3-pyqt5" "python3-dbus")
        CHECK_CMD="dpkg -l"
        INSTALL_CMD="sudo apt-get install -y"
    else
        echo -e "${RED}Unsupported package manager. Please install dependencies manually.${NC}"
        exit 1
    fi

    MISSING=()
    
    # Table header
    printf "  %-20s %-10s\n" "Dependency" "Status"
    printf "  %-20s %-10s\n" "------------" "------"

    for dep in "${DEPS[@]}"; do
        if $CHECK_CMD "$dep" &> /dev/null; then
            printf "  %-20s ${CHECK_MARK} %s\n" "$dep" "Installed"
        else
            printf "  %-20s ${CROSS_MARK} %s\n" "$dep" "Not found"
            MISSING+=("$dep")
        fi
    done
    
    echo

    if [ ${#MISSING[@]} -ne 0 ]; then
        echo -e "${RED}The following dependencies are required:${NC}"
        for dep in "${MISSING[@]}"; do
            echo -e "  - $dep"
        done
        
        echo -e "${BLUE}Do you want to install these dependencies now? (y/n)${NC}"
        read -r INSTALL_DEPS
        
        if [[ "$INSTALL_DEPS" =~ ^[Yy]$ ]]; then
            echo -e "${BLUE}Installing dependencies...${NC}"
            $INSTALL_CMD "${MISSING[@]}"
            if [ $? -ne 0 ]; then
                echo -e "${RED}Error installing dependencies. Aborting.${NC}"
                exit 1
            fi
            echo -e "${GREEN}Dependencies installed successfully.${NC}"
        else
            echo -e "${RED}Dependencies are required to continue. Aborting.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}All dependencies are installed.${NC}"
    fi

    # Create installation directories
    echo -e "${BLUE}Creating installation directories...${NC}"
    mkdir -p "$SCRIPT_DIR"
    mkdir -p "$CONFIG_DIR"
    
    # Copy the package directory to the configuration directory
    echo -e "${BLUE}Copying application files...${NC}"
    
    # Remove old package directory if it exists (idempotent reinstall)
    if [ -d "$CONFIG_DIR/gmail_notifier" ]; then
        rm -rf "$CONFIG_DIR/gmail_notifier"
        echo -e "  ${CHECK_MARK} Removed old package directory"
    fi
    
    # Copy the gmail_notifier package
    if [ -d "gmail_notifier" ]; then
        cp -r gmail_notifier "$CONFIG_DIR/"
        if [ $? -eq 0 ]; then
            echo -e "  ${CHECK_MARK} Package directory copied to $CONFIG_DIR/gmail_notifier"
        else
            echo -e "  ${CROSS_MARK} Error copying the package directory"
            exit 1
        fi
    else
        echo -e "  ${CROSS_MARK} Package directory 'gmail_notifier' not found"
        echo -e "${RED}Make sure you are running this script from the gmail-notifier directory.${NC}"
        exit 1
    fi
    
    # Remove old entry point if it exists
    if [ -f "$CONFIG_DIR/gmail-notifier.py" ]; then
        rm "$CONFIG_DIR/gmail-notifier.py"
    fi
    
    # Copy the main entry point script
    cp gmail-notifier.py "$CONFIG_DIR/gmail-notifier.py"
    if [ $? -eq 0 ]; then
        echo -e "  ${CHECK_MARK} Entry point script copied to $CONFIG_DIR/gmail-notifier.py"
    else
        echo -e "  ${CROSS_MARK} Error copying the entry point script"
        echo -e "${RED}Make sure the gmail-notifier.py file exists in the current directory.${NC}"
        exit 1
    fi
    
    # Create or update virtual environment
    echo -e "${BLUE}Setting up Python virtual environment...${NC}"
    
    # Check if venv exists and is valid
    if [ -f "$VENV_DIR/bin/python" ] && [ -f "$VENV_DIR/bin/pip" ]; then
        echo -e "  ${CHECK_MARK} Virtual environment already exists"
    else
        # Remove broken venv if it exists
        if [ -d "$VENV_DIR" ]; then
            echo -e "  ${YELLOW}Removing broken virtual environment...${NC}"
            rm -rf "$VENV_DIR"
        fi
        
        # Create new venv
        python -m venv "$VENV_DIR"
        if [ $? -eq 0 ]; then
            echo -e "  ${CHECK_MARK} Virtual environment created in $VENV_DIR"
        else
            echo -e "  ${CROSS_MARK} Error creating the virtual environment"
            echo -e "${RED}Verify that python-virtualenv is installed correctly.${NC}"
            exit 1
        fi
    fi
    
    # Install/upgrade dependencies in the virtual environment
    echo -e "${BLUE}Installing dependencies in the virtual environment...${NC}"
    "$VENV_DIR/bin/pip" install --upgrade pip -q
    "$VENV_DIR/bin/pip" install --upgrade PyQt5 keyring -q
    if [ $? -eq 0 ]; then
        echo -e "  ${CHECK_MARK} Dependencies installed successfully"
    else
        echo -e "  ${CROSS_MARK} Error installing dependencies in the virtual environment"
        exit 1
    fi
    
    # Create wrapper script
    echo -e "${BLUE}Creating startup script...${NC}"
    cat > "$SCRIPT_PATH" << EOF
#!/bin/bash
source "$VENV_DIR/bin/activate"
cd "$CONFIG_DIR"
python -m gmail_notifier
EOF
    
    chmod +x "$SCRIPT_PATH"
    if [ $? -eq 0 ]; then
        echo -e "  ${CHECK_MARK} Wrapper script created at $SCRIPT_PATH"
    else
        echo -e "  ${CROSS_MARK} Error creating the wrapper script"
        exit 1
    fi

    # Create .desktop file for autostart
    echo -e "${BLUE}Creating .desktop file for autostart...${NC}"
    mkdir -p "$HOME/.config/autostart"
    
    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=Gmail Notifier
Comment=Gmail Notifier for KDE
Exec=$SCRIPT_PATH
Icon=internet-mail
Terminal=false
Type=Application
Categories=Network;Email;
StartupNotify=true
X-GNOME-Autostart-enabled=true
EOF

    if [ $? -eq 0 ]; then
        echo -e "  ${CHECK_MARK} .desktop file created at $DESKTOP_FILE"
    else
        echo -e "  ${CROSS_MARK} Error creating the .desktop file"
        exit 1
    fi

    # Create .desktop file for start menu
    echo -e "${BLUE}Creating .desktop file for start menu...${NC}"
    mkdir -p "$HOME/.local/share/applications"
    
    cat > "$HOME/.local/share/applications/gmail-notifier.desktop" << EOF
[Desktop Entry]
Name=Gmail Notifier
Comment=Gmail Notifier for KDE
Exec=$SCRIPT_PATH
Icon=internet-mail
Terminal=false
Type=Application
Categories=Network;Email;
StartupNotify=true
EOF

    if [ $? -eq 0 ]; then
        echo -e "  ${CHECK_MARK} .desktop file for start menu created"
    else
        echo -e "  ${CROSS_MARK} Error creating the .desktop file for start menu"
        exit 1
    fi

    echo -e "${GREEN}Installation completed successfully!${NC}"
    echo
    
    # Information about app passwords
    cat << EOF
${YELLOW}===========================================================${NC}
  ${BOLD}IMPORTANT: About App Passwords${NC}
  
  Gmail Notifier needs an "App Password" to work:
  
  1. Go to your Google Account > Security
  2. Enable "2-Step Verification" if you haven't already
  3. Find "App passwords"
  4. Create a new password for "Mail" > "Other"
     (naming it "Gmail Notifier")
  
  This specific password will allow you to connect securely
  without using your main Google password.
${YELLOW}===========================================================${NC}
EOF

    echo -e "${BLUE}Do you want to start Gmail Notifier now? (y/n)${NC}"
    read -r START_NOW

    if [[ "$START_NOW" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Starting Gmail Notifier...${NC}"
        nohup "$SCRIPT_PATH" >/dev/null 2>&1 &
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Gmail Notifier is running in the system tray.${NC}"
            echo -e "${BLUE}A window will open to configure your account.${NC}"
        else
            echo -e "${RED}Error starting Gmail Notifier.${NC}"
            echo -e "${YELLOW}Try running it manually with the command 'gmail-notifier'${NC}"
        fi
    else
        echo -e "${BLUE}You can start Gmail Notifier later by running:${NC}"
        echo -e "  ${GREEN}gmail-notifier${NC}"
    fi
    
    # Show banner at the end
    echo
    show_banner
}

# Check arguments
case "$1" in
    -h|--help)
        show_banner
        echo
        show_help
        ;;
    -r|--remove|-u|--uninstall)
        show_banner
        echo
        uninstall
        ;;
    *)
        show_banner
        echo
        install
        ;;
esac
