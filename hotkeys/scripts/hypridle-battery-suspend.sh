#!/bin/bash
status=$(cat /sys/class/power_supply/AC*/online 2>/dev/null | head -1)
[ "$status" = "0" ] && systemctl suspend
