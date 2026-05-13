#!/bin/bash
LOAD=$(awk '{printf "%.2f", $1}' /proc/loadavg)
USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{printf "%d", $2}')
TOOLTIP="Load: ${LOAD}  Usage: ${USAGE}%"
if [ -f "/tmp/waybar-stats-mode" ]; then
    echo "{\"text\": \"󰻠 ${LOAD}\", \"tooltip\": \"${TOOLTIP}\"}"
else
    echo "{\"text\": \"󰻠\", \"tooltip\": \"${TOOLTIP}\"}"
fi
