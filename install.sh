#!/bin/bash
set -e

echo "Installing hypr-utils..."

mkdir -p ~/.local/bin

echo "[1/5] Installing dependencies..."
sudo pacman -S --needed --noconfirm grim slurp wl-clipboard python-gobject python-dbus gtk-layer-shell socat hyprpaper swaync playerctl pamixer brightnessctl rfkill python-google-api-python-client python-google-auth-oauthlib

echo "[2/5] Installing hotkey scripts..."
cp hotkeys/scripts/volume-notify.sh ~/.local/bin/
cp hotkeys/scripts/brightness-notify.sh ~/.local/bin/
cp hotkeys/scripts/mic-toggle.sh ~/.local/bin/
cp hotkeys/scripts/rfkill-notify.sh ~/.local/bin/
cp hotkeys/scripts/touchpad-notify.sh ~/.local/bin/
cp hotkeys/scripts/auto-layout.sh ~/.local/bin/
cp hotkeys/scripts/power-cycle.sh ~/.local/bin/
cp hotkeys/scripts/wallpaper-picker.sh ~/.local/bin/
cp hotkeys/scripts/wallpaper-slideshow.sh ~/.local/bin/
cp hotkeys/scripts/restart-scripts.sh ~/.local/bin/
chmod +x ~/.local/bin/volume-notify.sh ~/.local/bin/brightness-notify.sh \
         ~/.local/bin/mic-toggle.sh ~/.local/bin/rfkill-notify.sh \
         ~/.local/bin/touchpad-notify.sh ~/.local/bin/auto-layout.sh \
         ~/.local/bin/power-cycle.sh ~/.local/bin/wallpaper-picker.sh \
         ~/.local/bin/wallpaper-slideshow.sh ~/.local/bin/restart-scripts.sh

echo "[3/5] Installing waybar scripts..."
cp waybar/*.sh ~/.local/bin/
chmod +x ~/.local/bin/waybar-*.sh
cp waybar/waybar-tray-popup.py ~/.local/bin/
cp waybar/sni-watcher.py ~/.local/bin/
chmod +x ~/.local/bin/waybar-tray-popup.py ~/.local/bin/sni-watcher.py

echo "[4/5] Installing screenshot and monitor tools..."
cp screenshot/screenshot-tool.py ~/.local/bin/
cp monitor/monitor-picker.py ~/.local/bin/
chmod +x ~/.local/bin/screenshot-tool.py ~/.local/bin/monitor-picker.py

echo "[5/5] Installing calendar scripts..."

cp calendar/waybar-calendar.py ~/.local/bin/
cp calendar/waybar-calendar-oauth.py ~/.local/bin/
cp calendar/waybar-calendar-notify.py ~/.local/bin/
chmod +x ~/.local/bin/waybar-calendar.py ~/.local/bin/waybar-calendar-oauth.py \
         ~/.local/bin/waybar-calendar-notify.py

echo "Done!"
echo ""
echo "NOTE: For Google Calendar, place your credentials.json in:"
echo "  ~/.config/waybar-calendar/credentials.json"
echo "Then open the calendar popup (right-click clock in waybar) and click Connect."
