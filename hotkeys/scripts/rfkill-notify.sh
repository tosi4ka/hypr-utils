#!/bin/bash
sleep 0.2
if rfkill list all | grep -q "Soft blocked: yes"; then
    notify-send "✈️ Airplane Mode" "On" \
        --urgency=normal \
        --expire-time=2000 \
        --hint=string:x-dunst-stack-tag:rfkill
else
    notify-send "📶 Airplane Mode" "Off" \
        --urgency=normal \
        --expire-time=2000 \
        --hint=string:x-dunst-stack-tag:rfkill
fi