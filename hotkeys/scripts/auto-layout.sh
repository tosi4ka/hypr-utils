#!/bin/bash
SOCKET="$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.socket2.sock"
prev_layout=0
in_kitty=0

socat -U - UNIX-CONNECT:"$SOCKET" | while IFS= read -r line; do
    event="${line%%>>*}"
    data="${line#*>>}"

    case "$event" in
        activelayout)
            kb="${data%%,*}"
            layout="${data#*,}"
            if [[ "$kb" == *"keyboard"* && "$in_kitty" -eq 0 ]]; then
                [[ "$layout" == *"Russian"* ]] && prev_layout=1 || prev_layout=0
            fi
            ;;
        activewindow)
            class="${data%%,*}"
            if [[ "$class" == "kitty" ]]; then
                in_kitty=1
                [[ "$prev_layout" -eq 1 ]] && hyprctl switchxkblayout all 0 >/dev/null
            else
                if [[ "$in_kitty" -eq 1 ]]; then
                    in_kitty=0
                    [[ "$prev_layout" -eq 1 ]] && hyprctl switchxkblayout all 1 >/dev/null
                fi
            fi
            ;;
    esac
done
