# hypr-utils

Utility scripts and tools for Hyprland on Arch-based Linux.

## What's inside

| Component          | Description                                                        |
| ------------------ | ------------------------------------------------------------------ |
| `dock.py`          | macOS-style dock with minimize/restore, pinned apps, settings      |
| `window-switcher.py` | Alt+Tab window switcher (GTK3 overlay)                           |
| `launcher/`        | GTK3 app launcher (Super+D)                                        |
| `power/`           | GTK3 power menu (shutdown, reboot, suspend, lock, logout)          |
| `keyboard/`        | Hold-key accent/symbol picker (char-picker) for Latin layout       |
| `screenshot/`      | GTK3 popup for choosing screenshot mode                            |
| `monitor/`         | GTK3 popup for switching display modes                             |
| `waybar/`          | Custom waybar module scripts (CPU, RAM, temp, disk, battery, media)|
| `hotkeys/scripts/` | Notification scripts, wallpaper picker, auto-layout, minimize      |
| `calendar/`        | Google Calendar integration for waybar clock                       |

## Structure

```
hypr-utils/
├── dock.py
├── window-switcher.py
├── launcher/
│   └── app-launcher.py
├── power/
│   └── power-menu.py
├── keyboard/
│   ├── char-picker.py
│   ├── char-picker-popup.py
│   ├── char-picker-status.sh
│   └── char-picker-toggle.sh
├── screenshot/
│   └── screenshot-tool.py
├── monitor/
│   └── monitor-picker.py
├── waybar/
│   ├── waybar-battery.sh
│   ├── waybar-memory.sh / waybar-cpu.sh / waybar-temp.sh / waybar-disk.sh
│   ├── waybar-power.sh / waybar-media.sh / waybar-volume.sh
│   ├── waybar-network.sh / waybar-stats-toggle.sh
│   ├── sni-watcher.py / waybar-tray-popup.py
│   └── waybar-tray-toggle.sh / waybar-tray-status.sh
├── hotkeys/
│   └── scripts/
│       ├── auto-layout.sh
│       ├── minimize-active.sh
│       ├── restart-scripts.sh
│       ├── wallpaper-picker.sh / wallpaper-startup.sh
│       ├── volume-notify.sh / brightness-notify.sh
│       ├── mic-toggle.sh / rfkill-notify.sh / touchpad-notify.sh
│       └── power-cycle.sh
├── calendar/
│   ├── waybar-calendar.py
│   ├── waybar-calendar-notify.py
│   └── waybar-calendar-oauth.py
└── install.sh
```

## Dependencies

| Tool                                | Purpose                              |
| ----------------------------------- | ------------------------------------ |
| `grim`, `slurp`                     | Screenshot capture                   |
| `wl-clipboard`                      | Clipboard support                    |
| `python-gobject`, `gtk-layer-shell` | GTK3 popup windows on Wayland        |
| `python-evdev`                      | Keyboard input for char-picker       |
| `wtype`                             | Character typing for char-picker     |
| `pamixer`, `brightnessctl`          | Volume and brightness control        |
| `playerctl`                         | Media player control (MPRIS)         |
| `rfkill`                            | Airplane mode toggle                 |
| `socat`                             | Hyprland event socket reader         |
| `hyprpaper`, `hypridle`             | Wallpaper and idle daemons           |
| `swaync`                            | Notification daemon                  |

## Installation

```bash
git clone https://github.com/tosi4ka/hypr-utils.git
cd hypr-utils
./install.sh
```

> **Note:** char-picker requires input group access:
> ```bash
> sudo usermod -aG input $USER  # then reboot
> ```

## Hyprland config

```ini
# Autostart
exec-once = waybar
exec-once = swaync
exec-once = hypridle
exec-once = hyprpaper
exec-once = ~/.local/bin/auto-layout.sh
exec-once = ~/.local/bin/sni-watcher.py
exec-once = python3 ~/.local/bin/dock.py
exec-once = python3 ~/.local/bin/char-picker.py

# Hotkeys
bind = $mod, Return,    exec, kitty
bind = $mod, D,         exec, ~/.local/bin/app-launcher.py
bind = $mod, M,         movetoworkspacesilent, special:minimized
bind = $mod, F3,        exec, ~/.local/bin/screenshot-tool.py
bind = $mod SHIFT, S,   exec, ~/.local/bin/screenshot-tool.py
bind = $mod, P,         exec, ~/.local/bin/monitor-picker.py
bind = $mod, W,         exec, ~/.local/bin/wallpaper-picker.sh
bind = $mod SHIFT, P,   exec, ~/.local/bin/power-menu.py
bind = $mod SHIFT, R,   exec, ~/.local/bin/restart-scripts.sh
bind = ALT, Tab,        exec, python3 ~/.local/bin/window-switcher.py

bindel = , XF86AudioRaiseVolume,  exec, pamixer -i 5 && ~/.local/bin/volume-notify.sh
bindel = , XF86AudioLowerVolume,  exec, pamixer -d 5 && ~/.local/bin/volume-notify.sh
bindel = , XF86AudioMute,         exec, pamixer -t && ~/.local/bin/volume-notify.sh
bindel = , XF86MonBrightnessUp,   exec, brightnessctl s +5% && ~/.local/bin/brightness-notify.sh
bindel = , XF86MonBrightnessDown, exec, brightnessctl s 5%- && ~/.local/bin/brightness-notify.sh

bind = , XF86Launch6,     exec, ~/.local/bin/mic-toggle.sh
bind = , XF86RFKill,      exec, ~/.local/bin/rfkill-notify.sh
bind = , XF86TouchpadOff, exec, ~/.local/bin/touchpad-notify.sh off
bind = , XF86TouchpadOn,  exec, ~/.local/bin/touchpad-notify.sh on
```

## Stack

Python · GTK3 · GtkLayerShell · Bash · Wayland · Hyprland
