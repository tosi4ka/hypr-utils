#!/bin/bash
IMG_DIR="$HOME/SomeFiles/img"
SECS=$(( ${1:-10} * 60 ))

while true; do
    SELECTED=$(ls "$IMG_DIR" | grep -iE "\.(jpg|jpeg|png|webp)$" | shuf -n1)
    FULL="$IMG_DIR/$SELECTED"
    MONITORS=$(hyprctl monitors -j | python3 -c "import sys,json; [print(m['name']) for m in json.load(sys.stdin)]")
    {
        echo "splash = false"
        while IFS= read -r MON; do
            echo "preload = $FULL"
            echo "wallpaper = $MON,$FULL"
        done <<< "$MONITORS"
    } > ~/.config/hypr/hyprpaper.conf
    while IFS= read -r MON; do
        hyprctl hyprpaper preload "$FULL" 2>/dev/null
        hyprctl hyprpaper wallpaper "$MON,$FULL" 2>/dev/null
    done <<< "$MONITORS"
    sleep "$SECS"
done
