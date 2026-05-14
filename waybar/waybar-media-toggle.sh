#!/bin/bash
TOGGLE="/tmp/waybar-media-mode"
[ -f "$TOGGLE" ] && rm "$TOGGLE" || touch "$TOGGLE"
pkill -SIGRTMIN+13 waybar
