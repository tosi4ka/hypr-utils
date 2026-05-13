#!/bin/bash
TEMP=$(( $(cat /sys/class/hwmon/hwmon6/temp1_input) / 1000 ))
TOOLTIP="CPU Temperature: ${TEMP}°C"
if [ -f "/tmp/waybar-stats-mode" ]; then
    echo "{\"text\": \"󰔐 ${TEMP}°C\", \"tooltip\": \"${TOOLTIP}\"}"
else
    echo "{\"text\": \"󰔐\", \"tooltip\": \"${TOOLTIP}\"}"
fi
