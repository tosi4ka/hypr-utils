#!/bin/bash
if systemctl --user is-active --quiet char-picker; then
    echo "<txt> ⌨ ON </txt><tool>Character Picker ВКЛ\nКлик для выключения</tool>"
else
    echo "<txt> ⌨ OFF </txt><tool>Character Picker ВЫКЛ\nКлик для включения</tool>"
fi
