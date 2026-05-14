#!/bin/bash
USED=$(free --giga | awk '/^Mem:/{printf "%.1f", $3}')
TOTAL=$(free --giga | awk '/^Mem:/{printf "%.1f", $2}')
PUSED=$(free | awk '/^Mem:/{printf "%d", $3/$2*100}')
TOOLTIP="Used: ${USED}GiB / ${TOTAL}GiB (${PUSED}%)"
if [ -f "/tmp/waybar-stats-mode" ]; then
    echo "{\"text\": \"󰆼 ${USED}GiB\", \"tooltip\": \"${TOOLTIP}\"}"
else
    echo "{\"text\": \"󰆼\", \"tooltip\": \"${TOOLTIP}\"}"
fi
