#!/bin/bash
SOCKET="$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.socket2.sock"
in_kitty=0

init=$(hyprctl devices -j | python3 -c "
import json,sys
d=json.load(sys.stdin)
kbs=[k for k in d.get('keyboards',[]) if 'keyboard' in k['name'].lower()]
print(kbs[0]['active_keymap'] if kbs else '')
" 2>/dev/null)
[[ "$init" == *"Russian"* ]] && prev_layout=1 || prev_layout=0

socat -U - UNIX-CONNECT:"$SOCKET" | while IFS= read -r line; do
    event="${line%%>>*}"
    data="${line#*>>}"

    case "$event" in
        activelayout)
            kb="${data%%,*}"
            layout="${data#*,}"
            if [[ "$kb" == *"sonix"* ]]; then
                if [[ "$in_kitty" -eq 1 ]]; then
                    [[ "$layout" == *"Russian"* ]] && hyprctl switchxkblayout all 0 >/dev/null
                else
                    [[ "$layout" == *"Russian"* ]] && prev_layout=1 || prev_layout=0
                fi
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
