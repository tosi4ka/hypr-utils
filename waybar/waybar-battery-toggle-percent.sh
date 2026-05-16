#!/bin/bash
STATE_FILE="/tmp/waybar-battery-mode"
mode=$(cat "$STATE_FILE" 2>/dev/null || echo "icon")
if [ "$mode" = "percent" ]; then
    echo "icon" > "$STATE_FILE"
else
    echo "percent" > "$STATE_FILE"
fi
pkill -SIGRTMIN+10 waybar
