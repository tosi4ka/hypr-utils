#!/bin/bash
set -e

echo "Installing hypr-utils..."

mkdir -p ~/.local/bin ~/.config/rofi

echo "[1/4] Installing screenshot tool..."
sudo pacman -S --needed --noconfirm grim slurp wl-clipboard python-gobject gtk-layer-shell socat hyprpaper
cp screenshot/screenshot-tool.py ~/.local/bin/
chmod +x ~/.local/bin/screenshot-tool.py

echo "[2/4] Installing hotkey scripts..."
cp hotkeys/scripts/volume-notify.sh ~/.local/bin/
cp hotkeys/scripts/brightness-notify.sh ~/.local/bin/
cp hotkeys/scripts/mic-toggle.sh ~/.local/bin/
cp hotkeys/scripts/rfkill-notify.sh ~/.local/bin/
cp hotkeys/scripts/touchpad-notify.sh ~/.local/bin/
cp hotkeys/scripts/auto-layout.sh ~/.local/bin/
cp hotkeys/scripts/wallpaper-picker.sh ~/.local/bin/
cp hotkeys/scripts/wallpaper-slideshow.sh ~/.local/bin/
cp hotkeys/scripts/restart-scripts.sh ~/.local/bin/
chmod +x ~/.local/bin/wallpaper-picker.sh ~/.local/bin/wallpaper-slideshow.sh ~/.local/bin/restart-scripts.sh
chmod +x ~/.local/bin/auto-layout.sh
chmod +x ~/.local/bin/volume-notify.sh ~/.local/bin/brightness-notify.sh ~/.local/bin/mic-toggle.sh ~/.local/bin/rfkill-notify.sh ~/.local/bin/touchpad-notify.sh

echo "[3/4] Installing ACPI events..."
sudo cp hotkeys/acpi/* /etc/acpi/events/
sudo systemctl enable --now acpid
sudo systemctl restart acpid

echo "[4/4] Installing monitor picker..."
cp monitor/monitor-picker.py ~/.local/bin/
chmod +x ~/.local/bin/monitor-picker.py

echo "Done!"
