#!/bin/bash
pkill -f auto-layout.sh
sleep 0.3
~/.local/bin/auto-layout.sh &
notify-send "🔄 Scripts" "Restarted" --expire-time=1500
