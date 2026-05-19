#!/bin/bash
set -e

echo "Installing hypr-utils..."

mkdir -p ~/.local/bin

echo "[1/7] Installing dependencies..."
sudo pacman -S --needed --noconfirm \
    grim slurp wl-clipboard \
    python-gobject python-dbus python-evdev \
    gtk-layer-shell \
    socat wtype \
    hyprpaper swaync hypridle \
    playerctl pamixer brightnessctl rfkill \
    python-google-api-python-client python-google-auth-oauthlib

echo "[2/7] Installing hotkey scripts..."
cp hotkeys/scripts/volume-notify.sh ~/.local/bin/
cp hotkeys/scripts/brightness-notify.sh ~/.local/bin/
cp hotkeys/scripts/mic-toggle.sh ~/.local/bin/
cp hotkeys/scripts/rfkill-notify.sh ~/.local/bin/
cp hotkeys/scripts/touchpad-notify.sh ~/.local/bin/
cp hotkeys/scripts/auto-layout.sh ~/.local/bin/
cp hotkeys/scripts/power-cycle.sh ~/.local/bin/
cp hotkeys/scripts/wallpaper-picker.sh ~/.local/bin/
cp hotkeys/scripts/wallpaper-slideshow.sh ~/.local/bin/
cp hotkeys/scripts/wallpaper-startup.sh ~/.local/bin/
cp hotkeys/scripts/wallpaper-preview.py ~/.local/bin/
cp hotkeys/scripts/restart-scripts.sh ~/.local/bin/
cp hotkeys/scripts/minimize-active.sh ~/.local/bin/
cp hotkeys/scripts/hypridle-battery-suspend.sh ~/.local/bin/
chmod +x ~/.local/bin/volume-notify.sh ~/.local/bin/brightness-notify.sh \
         ~/.local/bin/mic-toggle.sh ~/.local/bin/rfkill-notify.sh \
         ~/.local/bin/touchpad-notify.sh ~/.local/bin/auto-layout.sh \
         ~/.local/bin/power-cycle.sh ~/.local/bin/wallpaper-picker.sh \
         ~/.local/bin/wallpaper-slideshow.sh ~/.local/bin/wallpaper-startup.sh \
         ~/.local/bin/wallpaper-preview.py ~/.local/bin/restart-scripts.sh \
         ~/.local/bin/minimize-active.sh ~/.local/bin/hypridle-battery-suspend.sh

echo "[3/7] Installing waybar scripts..."
cp waybar/*.sh ~/.local/bin/
chmod +x ~/.local/bin/waybar-*.sh
cp waybar/waybar-tray-popup.py ~/.local/bin/
cp waybar/sni-watcher.py ~/.local/bin/
chmod +x ~/.local/bin/waybar-tray-popup.py ~/.local/bin/sni-watcher.py

echo "[4/7] Installing screenshot and monitor tools..."
cp screenshot/screenshot-tool.py ~/.local/bin/
cp monitor/monitor-picker.py ~/.local/bin/
chmod +x ~/.local/bin/screenshot-tool.py ~/.local/bin/monitor-picker.py

echo "[5/7] Installing dock, launcher, window-switcher, power menu..."
cp dock.py ~/.local/bin/
cp window-switcher.py ~/.local/bin/
cp launcher/app-launcher.py ~/.local/bin/
cp power/power-menu.py ~/.local/bin/
chmod +x ~/.local/bin/dock.py ~/.local/bin/window-switcher.py \
         ~/.local/bin/app-launcher.py ~/.local/bin/power-menu.py

echo "[6/7] Installing keyboard char-picker..."
cp keyboard/char-picker.py ~/.local/bin/
cp keyboard/char-picker-popup.py ~/.local/bin/
cp keyboard/char-picker-status.sh ~/.local/bin/
cp keyboard/char-picker-toggle.sh ~/.local/bin/
chmod +x ~/.local/bin/char-picker.py ~/.local/bin/char-picker-popup.py \
         ~/.local/bin/char-picker-status.sh ~/.local/bin/char-picker-toggle.sh

echo "[7/7] Installing calendar scripts..."
cp calendar/waybar-calendar.py ~/.local/bin/
cp calendar/waybar-calendar-oauth.py ~/.local/bin/
cp calendar/waybar-calendar-notify.py ~/.local/bin/
chmod +x ~/.local/bin/waybar-calendar.py ~/.local/bin/waybar-calendar-oauth.py \
         ~/.local/bin/waybar-calendar-notify.py

echo ""
echo "Done! All scripts installed to ~/.local/bin/"
echo ""
echo "NOTE: For Google Calendar, place your credentials.json in:"
echo "  ~/.config/waybar-calendar/credentials.json"
echo "Then open the calendar popup (right-click clock in waybar) and click Connect."
echo ""
echo "NOTE: char-picker requires input group access:"
echo "  sudo usermod -aG input \$USER  → then reboot"
