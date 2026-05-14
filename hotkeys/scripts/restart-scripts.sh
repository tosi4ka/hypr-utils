#!/bin/bash
pkill -f auto-layout.sh
killall waybar 2>/dev/null
sleep 0.3
gsettings set org.gnome.desktop.interface color-scheme prefer-dark
waybar &
~/.local/bin/auto-layout.sh &
notify-send "Scripts" "Restarted" --urgency=low --expire-time=1500 --hint=int:transient:1


