#!/bin/bash
VOL=$(pamixer --get-volume)
MUTED=$(pamixer --get-mute)
SINK=$(pactl get-default-sink)

if [ "$MUTED" = "true" ]; then
    ICON="󰝟"
elif [[ "$SINK" == *"bluez"* ]]; then
    ICON="󰂰"
elif [[ "$SINK" == *"Headphones"* || "$SINK" == *"headphone"* ]]; then
    ICON="󰋋"
elif [ "$VOL" -lt 33 ]; then
    ICON="󰕿"
elif [ "$VOL" -lt 66 ]; then
    ICON="󰖀"
else
    ICON="󰕾"
fi

TOOLTIP="$VOL% — $(pactl get-default-sink | sed 's/.*\.//')"

if [ -f "/tmp/waybar-volume-mode" ]; then
    echo "{\"text\": \"$ICON $VOL%\", \"tooltip\": \"$TOOLTIP\"}"
else
    echo "{\"text\": \"$ICON\", \"tooltip\": \"$TOOLTIP\"}"
fi
