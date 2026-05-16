#!/bin/bash
STATE_FILE="/tmp/waybar-battery-mode"
mode=$(cat "$STATE_FILE" 2>/dev/null || echo "icon")
if [ "$mode" = "time" ]; then
    echo "icon" > "$STATE_FILE"
else
    echo "time" > "$STATE_FILE"
fi
pkill -SIGRTMIN+10 waybar
