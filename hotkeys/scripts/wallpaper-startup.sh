#!/bin/bash
SYMLINK=~/.config/hypr/wallpaper
[ -L "$SYMLINK" ] || exit 0
FULL=$(readlink -f "$SYMLINK")
[ -f "$FULL" ] || exit 0

until pgrep -x hyprpaper > /dev/null; do sleep 0.3; done
sleep 0.5

MONITORS=$(hyprctl monitors -j | python3 -c "import sys,json; [print(m['name']) for m in json.load(sys.stdin)]")

{
    echo "splash = false"
    echo "preload = $FULL"
    while IFS= read -r MON; do
        echo "wallpaper = $MON,$FULL"
    done <<< "$MONITORS"
} > ~/.config/hypr/hyprpaper.conf

while IFS= read -r MON; do
    hyprctl hyprpaper preload "$FULL" 2>/dev/null
    hyprctl hyprpaper wallpaper "$MON,$FULL" 2>/dev/null
done <<< "$MONITORS"
