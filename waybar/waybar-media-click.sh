#!/bin/bash
TOGGLE="/tmp/waybar-media-mode"
[ ! -f "$TOGGLE" ] && playerctl play-pause
