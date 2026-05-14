#!/bin/bash
BRIGHTNESS=$(brightnessctl get)
MAX=$(brightnessctl max)
PERCENT=$(( BRIGHTNESS * 100 / MAX ))

ID_FILE="/tmp/brightness-notify-id"
PREV_ID=$(cat "$ID_FILE" 2>/dev/null || echo "0")

notify-send "☀️ Яркость" " " \
    --urgency=low \
    --expire-time=1500 \
    --hint=int:transient:1 \
    --hint=int:value:$PERCENT \
    --replace-id=$PREV_ID \
    --print-id > "$ID_FILE"

