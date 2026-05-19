#!/bin/bash
BAT="/sys/class/power_supply/BAT1"
STATE_FILE="/tmp/waybar-battery-mode"

capacity=$(< "$BAT/capacity")
status=$(< "$BAT/status")
charge_now=$(< "$BAT/charge_now")
charge_full=$(< "$BAT/charge_full")
charge_full_design=$(< "$BAT/charge_full_design")
current_now=$(< "$BAT/current_now")
voltage_now=$(< "$BAT/voltage_now")
{ cycle_count=$(< "$BAT/cycle_count"); } 2>/dev/null || cycle_count="?"

remaining=$((charge_full - charge_now))

read -r power health time_h_dis time_m_dis time_h_chg time_m_chg < <(awk \
    -v cn="$current_now" -v vn="$voltage_now" \
    -v cf="$charge_full" -v cfd="$charge_full_design" \
    -v cnow="$charge_now" -v rem="$remaining" \
    'BEGIN {
        power  = (cn > 0 && vn > 0) ? cn * vn / 1e12 : 0
        health = cf / cfd * 100
        td = (cn > 0) ? cnow / cn : 0
        tc = (cn > 0) ? rem  / cn : 0
        printf "%.1f %.1f %d %d %d %d\n",
            power, health,
            int(td), int((td - int(td)) * 60),
            int(tc), int((tc - int(tc)) * 60)
    }')

# Time string
if [ "$status" = "Discharging" ] && [ "$current_now" -gt 0 ]; then
    time_str="${time_h_dis}h ${time_m_dis}min"
    time_label="Empty in"
elif [ "$status" = "Charging" ] && [ "$current_now" -gt 0 ]; then
    time_str="${time_h_chg}h ${time_m_chg}min"
    time_label="Full in"
else
    time_str="—"
    time_label="Status"
fi

# Icons
ICO_BOLT=$(printf '\xef\x83\xa7')
ICO_FULL=$(printf '\xF3\xB0\x81\xB9')
ICO_HIGH=$(printf '\xF3\xB0\x82\x81')
ICO_MED=$(printf '\xF3\xB0\x81\xBE')
ICO_LOW=$(printf '\xF3\xB0\x81\xBB')

if   [ "$capacity" -ge 75 ]; then bat_icon="$ICO_FULL"
elif [ "$capacity" -ge 50 ]; then bat_icon="$ICO_HIGH"
elif [ "$capacity" -ge 25 ]; then bat_icon="$ICO_MED"
else                               bat_icon="$ICO_LOW"
fi

if [ "$status" = "Charging" ]; then icon="$ICO_BOLT $bat_icon"
else                                 icon="$bat_icon"
fi

# CSS class
if   [ "$status" = "Charging" ];  then css_class="charging"
elif [ "$capacity" -le 15 ];      then css_class="critical"
elif [ "$capacity" -le 30 ];      then css_class="warning"
else                                    css_class="normal"
fi

# Mode
{ mode=$(< "$STATE_FILE"); } 2>/dev/null || mode="icon"
if   [ "$mode" = "percent" ]; then text="$icon ${capacity}%"
elif [ "$mode" = "time" ];    then text="$icon $time_str"
else                               text="$icon"
fi

tooltip="$time_label $time_str\n⚡ Usage: ${power}W\n🔄 Condition: ${health}%\n🔁 Total: $cycle_count cycles"

echo "{\"text\": \"$text\", \"tooltip\": \"$tooltip\", \"class\": \"$css_class\"}"
