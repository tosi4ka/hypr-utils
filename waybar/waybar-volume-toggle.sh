#!/bin/bash
TOGGLE="/tmp/waybar-volume-mode"
[ -f "$TOGGLE" ] && rm "$TOGGLE" || touch "$TOGGLE"
pkill -SIGRTMIN+9 waybar

