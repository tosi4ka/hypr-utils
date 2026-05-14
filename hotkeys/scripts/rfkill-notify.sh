#!/bin/bash
sleep 0.2

ID_FILE="/tmp/rfkill-notify-id"
PREV_ID=$(cat "$ID_FILE" 2>/dev/null || echo "0")

if rfkill list all | grep -q "Soft blocked: yes"; then
    notify-send "✈️ Airplane Mode" "On" \
        --urgency=low \
        --expire-time=2000 \
        --hint=int:transient:1 \
        --replace-id=$PREV_ID \
        --print-id > "$ID_FILE"
else
    notify-send "📶 Airplane Mode" "Off" \
        --urgency=low \
        --expire-time=2000 \
        --hint=int:transient:1 \
        --replace-id=$PREV_ID \
        --print-id > "$ID_FILE"
fi
