#!/bin/bash
BRIGHTNESS=$(brightnessctl get)
MAX=$(brightnessctl max)
PERCENT=$(( BRIGHTNESS * 100 / MAX ))

notify-send "☀️ Яркость" " " \
    --urgency=normal \
    --expire-time=1500 \
    --hint=string:x-dunst-stack-tag:brightness \
    --hint=int:value:$PERCENT
