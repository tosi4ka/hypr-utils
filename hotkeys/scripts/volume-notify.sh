#!/bin/bash
VOL=$(pamixer --get-volume)
MUTED=$(pamixer --get-mute)

SINK=$(pactl get-default-sink)

if [[ "$SINK" == *"bluez"* ]]; then
    ICON="🎧"
elif [[ "$SINK" == *"Headphones"* ]]; then
    ICON="🎧"
elif [[ "$SINK" == *"Speaker"* ]]; then
    ICON="🔊"
else
    ICON="🔊"
fi

if [ "$MUTED" = "true" ]; then
    notify-send "🔇 Volume" " " \
        --urgency=normal \
        --expire-time=1500 \
        --hint=string:x-dunst-stack-tag:volume \
        --hint=int:value:0
else
    notify-send "$ICON Volume" " " \
        --urgency=normal \
        --expire-time=1500 \
        --hint=string:x-dunst-stack-tag:volume \
        --hint=int:value:$VOL
fi
