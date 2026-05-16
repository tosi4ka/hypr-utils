#!/bin/bash
BAT="/sys/class/power_supply/BAT1"
STATE_FILE="/tmp/waybar-battery-mode"

capacity=$(cat "$BAT/capacity")
status=$(cat "$BAT/status")
charge_now=$(cat "$BAT/charge_now")
charge_full=$(cat "$BAT/charge_full")
charge_full_design=$(cat "$BAT/charge_full_design")
current_now=$(cat "$BAT/current_now")
voltage_now=$(cat "$BAT/voltage_now")
cycle_count=$(cat "$BAT/cycle_count" 2>/dev/null || echo "?")

# Watts
if [ "$current_now" -gt 0 ] && [ "$voltage_now" -gt 0 ]; then
    power=$(awk "BEGIN {printf \"%.1f\", ($current_now * $voltage_now) / 1e12}")
else
    power="0.0"
fi

# Health
health=$(awk "BEGIN {printf \"%.1f\", ($charge_full / $charge_full_design) * 100}")

# Time
if [ "$status" = "Discharging" ] && [ "$current_now" -gt 0 ]; then
    time_h=$(awk "BEGIN {printf \"%d\", $charge_now / $current_now}")
    time_m=$(awk "BEGIN {printf \"%d\", ($charge_now / $current_now - int($charge_now / $current_now)) * 60}")
    time_str="${time_h}h ${time_m}min"
    time_label="Empty in"
elif [ "$status" = "Charging" ] && [ "$current_now" -gt 0 ]; then
    remaining=$((charge_full - charge_now))
    time_h=$(awk "BEGIN {printf \"%d\", $remaining / $current_now}")
    time_m=$(awk "BEGIN {printf \"%d\", ($remaining / $current_now - int($remaining / $current_now)) * 60}")
    time_str="${time_h}h ${time_m}min"
    time_label="Full in"
else
    time_str="—"
    time_label="Status"
fi

# Vertical battery icons (Nerd Fonts MD, copy-paste safe hex)
ICO_BOLT=$(printf '\xef\x83\xa7')        # U+F0E7  bolt
ICO_FULL=$(printf '\xF3\xB0\x81\xB9')   # U+F0079 battery 100%
ICO_HIGH=$(printf '\xF3\xB0\x82\x81')   # U+F0081 battery ~80%
ICO_MED=$(printf '\xF3\xB0\x81\xBE')    # U+F007E battery 50%
ICO_LOW=$(printf '\xF3\xB0\x81\xBB')    # U+F007B battery ~20%

# Battery level icon (4 levels)
if [ "$capacity" -ge 75 ]; then
    bat_icon="$ICO_FULL"
elif [ "$capacity" -ge 50 ]; then
    bat_icon="$ICO_HIGH"
elif [ "$capacity" -ge 25 ]; then
    bat_icon="$ICO_MED"
else
    bat_icon="$ICO_LOW"
fi

# Charging: bolt + battery icon (оба зелёные через CSS .charging)
if [ "$status" = "Charging" ]; then
    icon="$ICO_BOLT $bat_icon"
else
    icon="$bat_icon"
fi

# CSS class
if [ "$status" = "Charging" ]; then css_class="charging"
elif [ "$capacity" -le 15 ]; then css_class="critical"
elif [ "$capacity" -le 30 ]; then css_class="warning"
else css_class="normal"
fi

# Mode
mode=$(cat "$STATE_FILE" 2>/dev/null || echo "icon")
if [ "$mode" = "percent" ]; then
    text="$icon ${capacity}%"
elif [ "$mode" = "time" ]; then
    text="$icon $time_str"
else
    text="$icon"
fi


tooltip="$time_label $time_str\n⚡ Usage: ${power}W\n🔄 Condition: ${health}%\n🔁 Total: $cycle_count cycles"

echo "{\"text\": \"$text\", \"tooltip\": \"$tooltip\", \"class\": \"$css_class\"}"
