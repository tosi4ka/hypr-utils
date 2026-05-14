#!/bin/bash
MIC="alsa_input.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__Mic2__source"

MUTED=$(pactl get-source-mute "$MIC" | grep -c "yes")

ID_FILE="/tmp/mic-notify-id"
PREV_ID=$(cat "$ID_FILE" 2>/dev/null || echo "0")

if [ "$MUTED" -eq 1 ]; then
    pactl set-source-mute "$MIC" 0
    notify-send "🎙️ Микрофон" "Включён" \
        --urgency=low --expire-time=2000 \
        --hint=int:transient:1 \
        --replace-id=$PREV_ID --print-id > "$ID_FILE"
else
    pactl set-source-mute "$MIC" 1
    notify-send "🔇 Микрофон" "Выключен" \
        --urgency=low --expire-time=2000 \
        --hint=int:transient:1 \
        --replace-id=$PREV_ID --print-id > "$ID_FILE"
fi
