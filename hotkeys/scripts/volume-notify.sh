#!/bin/bash
VOL=$(pamixer --get-volume)
MUTED=$(pamixer --get-mute)

SINK=$(pactl get-default-sink)
if [[ "$SINK" == *"bluez"* || "$SINK" == *"Headphones"* ]]; then
    ICON="🎧"
else
    ICON="🔊"
fi

ID_FILE="/tmp/volume-notify-id"
PREV_ID=$(cat "$ID_FILE" 2>/dev/null || echo "0")

if [ "$MUTED" = "true" ]; then
    notify-send "🔇 Звук" " " \
        --urgency=low \
        --expire-time=1500 \
        --hint=int:transient:1 \
        --hint=int:value:0 \
        --replace-id=$PREV_ID \
        --print-id > "$ID_FILE"
else
    notify-send "$ICON Звук" " " \
        --urgency=low \
        --expire-time=1500 \
        --hint=int:transient:1 \
        --hint=int:value:$VOL \
        --replace-id=$PREV_ID \
        --print-id > "$ID_FILE"
fi
