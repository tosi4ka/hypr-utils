#!/bin/bash
# ============================================================
# hypr-utils install script
# Screenshot tool + ACPI hotkeys for Hyprland/Wayland
# ============================================================

set -e

echo "Installing hypr-utils..."

# Screenshot
echo "[1/3] Installing screenshot tool..."
mkdir -p ~/.local/bin ~/.config/rofi
cp screenshot/screenshot.sh ~/.local/bin/
cp screenshot/screenshot.rasi ~/.config/rofi/
chmod +x ~/.local/bin/screenshot.sh

# Hotkey scripts
echo "[2/3] Installing hotkey scripts..."
cp hotkeys/scripts/volume-notify.sh ~/.local/bin/
cp hotkeys/scripts/brightness-notify.sh ~/.local/bin/
cp hotkeys/scripts/mic-toggle.sh ~/.local/bin/
chmod +x ~/.local/bin/volume-notify.sh
chmod +x ~/.local/bin/brightness-notify.sh
chmod +x ~/.local/bin/mic-toggle.sh

# ACPI events
echo "[3/3] Installing ACPI events..."
sudo cp hotkeys/acpi/* /etc/acpi/events/
sudo systemctl enable --now acpid
sudo systemctl restart acpid

echo "Done! hypr-utils installed successfully."
