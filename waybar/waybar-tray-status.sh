#!/bin/bash
if pgrep -f "waybar-tray-popup.py" > /dev/null; then
    echo '{"text": " ", "class": "open", "tooltip": "Скрыть трей"}'
else
    echo '{"text": " ", "tooltip": "Показать трей"}'
fi
