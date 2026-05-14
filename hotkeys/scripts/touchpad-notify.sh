#!/bin/bash
ID_FILE="/tmp/touchpad-notify-id"
PREV_ID=$(cat "$ID_FILE" 2>/dev/null || echo "0")

if [ "$1" = "on" ]; then
    notify-send "🖱️ Touchpad" "On" \
        --urgency=low \
        --expire-time=2000 \
        --hint=int:transient:1 \
        --replace-id=$PREV_ID \
        --print-id > "$ID_FILE"
else
    notify-send "🖱️ Touchpad" "Off" \
        --urgency=low \
        --expire-time=2000 \
        --hint=int:transient:1 \
        --replace-id=$PREV_ID \
        --print-id > "$ID_FILE"
fi
