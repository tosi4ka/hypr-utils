#!/bin/bash
if systemctl --user is-active --quiet char-picker; then
    systemctl --user stop char-picker
    notify-send "⌨ Character Picker" "Выключен" --expire-time=1500
else
    systemctl --user start char-picker
    notify-send "⌨ Character Picker" "Включён" --expire-time=1500
fi
