# hypr-utils

Utility scripts and tools for Hyprland on Arch-based Linux.  
Covers hotkeys, notifications, waybar modules, screenshot picker, and monitor mode switching.

## What's inside

| Component          | Description                                                                          |
| ------------------ | ------------------------------------------------------------------------------------ |
| `screenshot/`      | GTK3 popup for choosing screenshot mode (zone, window, monitor, all)                 |
| `monitor/`         | GTK3 popup for switching display modes (laptop, mirror, extend, external)            |
| `waybar/`          | Custom waybar module scripts (CPU, RAM, temp, disk, media, power)                    |
| `hotkeys/scripts/` | Notification scripts, wallpaper picker, auto-layout switcher                         |

## Structure

```
hypr-utils/
├── screenshot/
│   └── screenshot-tool.py
├── monitor/
│   └── monitor-picker.py
├── waybar/
│   ├── waybar-memory.sh / waybar-cpu.sh / waybar-temp.sh / waybar-disk.sh
│   ├── waybar-power.sh / waybar-media.sh / waybar-media-toggle.sh
│   └── waybar-stats-toggle.sh
├── hotkeys/
│   └── scripts/
│       ├── auto-layout.sh
│       ├── power-cycle.sh
│       ├── wallpaper-picker.sh
│       ├── wallpaper-slideshow.sh
│       ├── restart-scripts.sh
│       ├── volume-notify.sh
│       ├── brightness-notify.sh
│       ├── mic-toggle.sh
│       ├── rfkill-notify.sh
│       └── touchpad-notify.sh
└── install.sh
```

## Dependencies

| Tool                                | Purpose                       |
| ----------------------------------- | ----------------------------- |
| `grim`, `slurp`                     | Screenshot capture            |
| `wl-clipboard`                      | Clipboard support             |
| `python-gobject`, `gtk-layer-shell` | GTK3 popup windows on Wayland |
| `pamixer`, `brightnessctl`          | Volume and brightness control |
| `playerctl`                         | Media player control (MPRIS)  |
| `rfkill`                            | Airplane mode toggle          |
| `socat`                             | Hyprland event socket reader  |
| `hyprpaper`                         | Wallpaper daemon              |
| `swaync`                            | Notification daemon and control center |

## Installation

```bash
git clone https://github.com/tosi4ka/hypr-utils.git
cd hypr-utils
./install.sh
```

Then add bindings to `hyprland.conf`:

```
bind = $mod, F3, exec, ~/.local/bin/screenshot-tool.py
bind = $mod, P,  exec, ~/.local/bin/monitor-picker.py

bindel = , XF86AudioRaiseVolume,  exec, pamixer -i 5 && ~/.local/bin/volume-notify.sh
bindel = , XF86AudioLowerVolume,  exec, pamixer -d 5 && ~/.local/bin/volume-notify.sh
bindel = , XF86AudioMute,         exec, pamixer -t && ~/.local/bin/volume-notify.sh
bindel = , XF86MonBrightnessUp,   exec, brightnessctl s +5% && ~/.local/bin/brightness-notify.sh
bindel = , XF86MonBrightnessDown, exec, brightnessctl s 5%- && ~/.local/bin/brightness-notify.sh

bind = , XF86Launch6,     exec, ~/.local/bin/mic-toggle.sh
bind = , XF86RFKill,      exec, ~/.local/bin/rfkill-notify.sh
bind = , XF86TouchpadOff, exec, ~/.local/bin/touchpad-notify.sh off
bind = , XF86TouchpadOn,  exec, ~/.local/bin/touchpad-notify.sh on
bind = $mod, W,           exec, ~/.local/bin/wallpaper-picker.sh
bind = $mod SHIFT, R,     exec, ~/.local/bin/restart-scripts.sh

# auto-layout (starts automatically)
exec-once = ~/.local/bin/auto-layout.sh
exec-once = swaync
```

## Stack

Python · GTK3 · GtkLayerShell · Bash · Wayland · Hyprland
