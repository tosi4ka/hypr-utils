#!/bin/bash
EPP=$(cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference)

set_mode() {
    local gov=$1
    local epp=$2
    sudo /usr/local/bin/set-power-mode "$gov" "$epp"
}

case "$EPP" in
    power)
        set_mode powersave balance_power
        ;;
    balance_power|balance_performance|default)
        set_mode performance performance
        ;;
    performance)
        set_mode powersave power
        ;;
esac

pkill -SIGRTMIN+12 waybar
