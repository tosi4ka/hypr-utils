#!/bin/bash
IMG_DIR="$HOME/SomeFiles/img"
PID_FILE="/tmp/wallpaper-slideshow.pid"

apply_wallpaper() {
    local FULL="$1"
    local MONITORS
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
}

MODE=$(printf "🖼 Set wallpaper\n🔄 Slideshow\n⏹ Stop slideshow" | rofi -dmenu -p "Wallpaper")
[ -z "$MODE" ] && exit 0

case "$MODE" in
    "🖼 Set wallpaper")
        [ -f "$PID_FILE" ] && kill "$(cat "$PID_FILE")" 2>/dev/null && rm -f "$PID_FILE"
        SELECTED=$(printf "← Back\n%s" "$(ls "$IMG_DIR" | grep -iE "\.(jpg|jpeg|png|webp)$")" | rofi -dmenu -p "Select")
        [ -z "$SELECTED" ] && exit 0
        [ "$SELECTED" = "← Back" ] && exec "$0"
        apply_wallpaper "$IMG_DIR/$SELECTED"
        notify-send "🖼 Wallpaper" "$SELECTED" --expire-time=2000
        ;;
    "🔄 Slideshow")
        INTERVAL=$(printf "5 min\n10 min\n15 min\n30 min\n60 min" | rofi -dmenu -p "Change every")
        [ -z "$INTERVAL" ] && exit 0
        MINS=$(echo "$INTERVAL" | grep -o '[0-9]*')
        [ -f "$PID_FILE" ] && kill "$(cat "$PID_FILE")" 2>/dev/null
        ~/.local/bin/wallpaper-slideshow.sh "$MINS" &
        echo $! > "$PID_FILE"
        notify-send "🔄 Slideshow" "Every $MINS min" --expire-time=2000
        ;;
    "⏹ Stop slideshow")
        [ -f "$PID_FILE" ] && kill "$(cat "$PID_FILE")" 2>/dev/null && rm -f "$PID_FILE"
        notify-send "⏹ Slideshow" "Stopped" --expire-time=2000
        ;;
esac
