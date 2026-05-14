#!/bin/bash
EPP=$(cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference)

ECO=$(python3 -c "print(chr(0xf032a), end='')")
BAL=$(python3 -c "print(chr(0xe23a), end='')")
PERF=$(python3 -c "print(chr(0xf427), end='')")

case "$EPP" in
    power)
        echo "{\"text\": \"$ECO\", \"tooltip\": \"Eco\nEPP: power\", \"class\": \"eco\"}"
        ;;
    balance_power|balance_performance|default)
        echo "{\"text\": \"$BAL\", \"tooltip\": \"Balanced\nEPP: $EPP\", \"class\": \"balanced\"}"
        ;;
    performance)
        echo "{\"text\": \"$PERF\", \"tooltip\": \"Performance\nEPP: performance\", \"class\": \"performance\"}"
        ;;
esac
