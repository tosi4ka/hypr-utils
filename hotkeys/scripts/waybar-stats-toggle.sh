#!/bin/bash
TOGGLE="/tmp/waybar-stats-mode"
[ -f "$TOGGLE" ] && rm "$TOGGLE" || touch "$TOGGLE"
pkill -SIGRTMIN+8 waybar
