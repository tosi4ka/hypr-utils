#!/bin/bash
if pgrep -f "waybar-tray-popup.py" > /dev/null; then
    pkill -f "waybar-tray-popup.py"
else
    ~/.local/bin/waybar-tray-popup.py &
fi
sleep 0.1
pkill -SIGRTMIN+11 waybar
