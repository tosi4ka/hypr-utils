#!/bin/bash
if [ "$1" = "on" ]; then
    notify-send "🖱️ Touchpad" "On" \
        --urgency=normal \
        --expire-time=2000 \
        --hint=string:x-dunst-stack-tag:touchpad
else
    notify-send "🖱️ Touchpad" "Off" \
        --urgency=normal \
        --expire-time=2000 \
        --hint=string:x-dunst-stack-tag:touchpad
fi
