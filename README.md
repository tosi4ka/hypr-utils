# hypr-utils

Utility scripts for Hyprland: screenshot tool, hotkeys, notifications

## Structure
hypr-utils/
├── screenshot/
│   ├── screenshot.sh       # Screenshot tool with rofi menu
│   └── screenshot.rasi     # Rofi theme for screenshot menu
└── hotkeys/
├── scripts/
│   ├── volume-notify.sh      # Volume change notification
│   ├── brightness-notify.sh  # Brightness change notification
│   └── mic-toggle.sh         # Microphone toggle
└── acpi/
├── mute
├── volumeup
├── volumedown
├── brightnessup
└── brightnessdown

## Dependencies

| Tool | Purpose |
|------|---------|
| grim, slurp | Screenshot capture |
| swappy, hyprshot | Screenshot editor |
| rofi-wayland | Screenshot menu |
| wl-clipboard | Clipboard support |
| ttf-nerd-fonts-symbols | Icons |
| pamixer, brightnessctl | Volume/brightness control |
| acpid, dunst | Hotkey daemon, notifications |

## Installation

```bash
git clone git@github.com:tosi4ka/hypr-utils.git
cd hypr-utils
./install.sh
```
