#!/bin/bash
PCT=$(df / | awk 'NR==2{print $5}')
USED=$(df -h / | awk 'NR==2{print $3}')
TOTAL=$(df -h / | awk 'NR==2{print $2}')
TOOLTIP="Disk: ${USED} / ${TOTAL} (${PCT})"
if [ -f "/tmp/waybar-stats-mode" ]; then
    echo "{\"text\": \"󰋊 ${PCT}\", \"tooltip\": \"${TOOLTIP}\"}"
else
    echo "{\"text\": \"󰋊\", \"tooltip\": \"${TOOLTIP}\"}"
fi
