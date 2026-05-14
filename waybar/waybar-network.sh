#!/bin/bash
INFO=$(nmcli -t -f SIGNAL,SSID,ACTIVE dev wifi 2>/dev/null | grep ':yes$' | head -1)
SIGNAL=$(echo "$INFO" | cut -d: -f1)
SSID=$(echo "$INFO" | cut -d: -f2)

if [ -z "$SIGNAL" ]; then
    echo "{\"text\": \"󰤭\", \"tooltip\": \"Disconnected\"}"; exit 0
fi

if   [ "$SIGNAL" -ge 75 ]; then ICON="󰤨"
elif [ "$SIGNAL" -ge 50 ]; then ICON="󰤥"
elif [ "$SIGNAL" -ge 25 ]; then ICON="󰤢"
else ICON="󰤟"; fi

echo "{\"text\": \"$ICON\", \"tooltip\": \"$SSID  $SIGNAL%\"}"
