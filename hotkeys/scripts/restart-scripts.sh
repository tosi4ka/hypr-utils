#!/bin/bash
pkill -f auto-layout.sh
pkill -f waybar-calendar-notify.py 2>/dev/null
killall waybar 2>/dev/null
sleep 0.3
gsettings set org.gnome.desktop.interface color-scheme prefer-dark
waybar &
~/.local/bin/auto-layout.sh &
~/.local/bin/waybar-calendar-notify.py &
nmcli device wifi rescan &>/dev/null &
notify-send "Scripts" "Restarted" --urgency=low --expire-time=1500 --hint=int:transient:1
