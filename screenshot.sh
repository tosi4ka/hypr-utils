#!/bin/bash
SAVE_DIR=~/Pictures/Screenshots
mkdir -p "$SAVE_DIR"

CHOICE=$(printf "󰩭\n󱂬\n󰍹\n󰍺" | rofi -dmenu -p "" -i -selected-row 0 -theme ~/.config/rofi/screenshot.rasi)

case "$CHOICE" in
  "󰩭")
    hyprshot -m region --clipboard-only | swappy -f -;;
  "󱂬")
    hyprshot -m window --clipboard-only | swappy -f -;;
  "󰍹")
    hyprshot -m output --clipboard-only | swappy -f -;;
  "󰍺")
    grim "$SAVE_DIR/screenshot-$(date +%Y%m%d-%H%M%S).png" && \
    wl-copy < "$SAVE_DIR/screenshot-$(date +%Y%m%d-%H%M%S).png";;
esac
