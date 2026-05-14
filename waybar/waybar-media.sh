#!/bin/bash
TOGGLE="/tmp/waybar-media-mode"

get_app_icon() {
    case "$1" in
        chromium|google-chrome) echo "󰊯" ;;
        firefox)                echo "󰈹" ;;
        code|vscodium)          echo "󰨞" ;;
        kitty|alacritty|foot)   echo "󰊠" ;;
        thunar|nautilus|nemo)   echo "󰝰" ;;
        telegram-desktop)       echo "" ;;
        viber)                  echo "" ;;
        spotify)                echo "󰓇" ;;
        discord)                echo "󰙯" ;;
        blueman-manager)        echo "󰂯" ;;
        steam)                  echo "󰓓" ;;
        freecad|org.freecadweb.freecad) echo "󰻑" ;;
        inkscape)               echo "󰋩" ;;
        gimp)                   echo "󰏘" ;;
        blender)                echo "󰂫" ;;
        vlc)                    echo "󰕼" ;;
        mpv)                    echo "󰃽" ;;
        obs)                    echo "󰤉" ;;
        libreoffice*)           echo "󱐋" ;;
        evince|okular|zathura)  echo "󰈦" ;;
        imv)                    echo "󰉏" ;;
        *)                      echo "󰣆" ;;
    esac
}

if [ -f "$TOGGLE" ]; then
    APPS=$(hyprctl clients -j | python3 -c "
import json,sys
c=json.load(sys.stdin)
print(' '.join(dict.fromkeys(x['class'].lower() for x in c if x['class'])))
")
    ICONS=""
    for app in $APPS; do
        ICONS="$ICONS$(get_app_icon $app) "
    done
    echo "{\"text\": \"$ICONS\", \"tooltip\": \"Right-click to show media\"}"
else
    if ! playerctl status &>/dev/null 2>&1; then
        echo "{\"text\": \"󰎆\", \"tooltip\": \"No media\"}"; exit 0
    fi
    STATUS=$(playerctl status 2>/dev/null)
    TITLE=$(playerctl metadata title 2>/dev/null | cut -c1-35)
    ARTIST=$(playerctl metadata artist 2>/dev/null | cut -c1-20)
    PLAYER=$(playerctl metadata --format "{{playerName}}" 2>/dev/null)
    APP_ICON=$(get_app_icon "$PLAYER")
    if [ "$STATUS" = "Playing" ]; then
        TEXT="$APP_ICON ⏸ $TITLE — $ARTIST"
    else
        TEXT="$APP_ICON ▶ $TITLE — $ARTIST"
    fi
    echo "{\"text\": \"$TEXT\", \"tooltip\": \"$PLAYER\"}"
fi
