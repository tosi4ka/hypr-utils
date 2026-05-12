# hypr-utils

Utility scripts and tools for Hyprland on Arch-based Linux.  
Covers hotkeys, notifications, screenshot picker, and monitor mode switching.

## What's inside

| Component          | Description                                                                          |
| ------------------ | ------------------------------------------------------------------------------------ |
| `screenshot/`      | GTK3 popup for choosing screenshot mode (zone, window, monitor, all)                 |
| `monitor/`         | GTK3 popup for switching display modes (laptop, mirror, extend, external)            |
| `hotkeys/scripts/` | Notification scripts for hardware keys (volume, brightness, mic, airplane, touchpad) |
| `hotkeys/acpi/`    | ACPI event handlers for keys that bypass Wayland                                     |

## Structure

```
hypr-utils/
├── screenshot/
│   └── screenshot-tool.py
├── monitor/
│   └── monitor-picker.py
├── hotkeys/
│   ├── scripts/
│   │   ├── auto-layout.sh
│   │   ├── volume-notify.sh
│   │   ├── brightness-notify.sh
│   │   ├── mic-toggle.sh
│   │   ├── rfkill-notify.sh
│   │   └── touchpad-notify.sh
│   └── acpi/
│       ├── mute
│       ├── volumeup / volumedown
│       └── brightnessup / brightnessdown
└── install.sh
```

## Dependencies

| Tool                                | Purpose                       |
| ----------------------------------- | ----------------------------- |
| `grim`, `slurp`                     | Screenshot capture            |
| `wl-clipboard`                      | Clipboard support             |
| `python-gobject`, `gtk-layer-shell` | GTK3 popup windows on Wayland |
| `pamixer`, `brightnessctl`          | Volume and brightness control |
| `rfkill`                            | Airplane mode toggle          |
| `acpid`, `dunst`                    | ACPI events, notifications    |

## Installation

```bash
git clone git@github.com:tosi4ka/hypr-utils.git
cd hypr-utils
./install.sh
```

Then add bindings to `hyprland.conf`:

```
bind = $mod, F3, exec, ~/.local/bin/screenshot-tool.py
bind = $mod, P,  exec, ~/.local/bin/monitor-picker.py

bind = , XF86RFKill,      exec, ~/.local/bin/rfkill-notify.sh
bind = , XF86TouchpadOff, exec, ~/.local/bin/touchpad-notify.sh off
bind = , XF86TouchpadOn,  exec, ~/.local/bin/touchpad-notify.sh on

# auto-layout (starts automatically)
exec-once = ~/.local/bin/auto-layout.sh
```

## Stack

Python · GTK3 · GtkLayerShell · Bash · Wayland · Hyprland
