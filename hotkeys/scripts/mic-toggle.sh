#!/bin/bash
MIC="alsa_input.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__Mic2__source"

MUTED=$(pactl get-source-mute "$MIC" | grep -c "yes")

if [ "$MUTED" -eq 1 ]; then
    pactl set-source-mute "$MIC" 0
    notify-send "🎙️ Микрофон" "Включён" \
        --urgency=normal \
        --expire-time=2000 \
        --hint=string:x-dunst-stack-tag:mic
else
    pactl set-source-mute "$MIC" 1
    notify-send "🔇 Микрофон" "Выключен" \
        --urgency=normal \
        --expire-time=2000 \
        --hint=string:x-dunst-stack-tag:mic
fi
