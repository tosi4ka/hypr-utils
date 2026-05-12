#!/usr/bin/env python3
import fcntl
import json
import os
import subprocess
import time

lock_file = open("/tmp/monitor-picker.lock", "w")
try:
    fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    exit(0)

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, GLib, Gtk, GtkLayerShell

MODE_FILE = "/tmp/hypr-monitor-mode"
LAPTOP = "eDP-1"

CSS = b"""
window {
    background: transparent;
}
.popup-box {
    background-color: rgba(15, 15, 20, 0.97);
    border-radius: 16px;
    padding: 24px;
    border: 1px solid rgba(127, 119, 221, 0.6);
}
.title {
    color: #7f77dd;
    font-family: "JetBrains Mono";
    font-size: 13px;
    font-weight: bold;
    margin-bottom: 16px;
}
.btn {
    background: transparent;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 20px 16px;
    min-width: 80px;
    min-height: 80px;
    color: #cccccc;
    font-family: "Symbols Nerd Font";
    font-size: 36px;
    margin: 4px;
}
.btn:hover {
    background: rgba(127, 119, 221, 0.15);
    border-color: rgba(127, 119, 221, 0.5);
    color: #ffffff;
}
.btn-active {
    background: rgba(127, 119, 221, 0.25);
    border: 1px solid rgba(127, 119, 221, 0.8);
    color: #ffffff;
}
.hint {
    color: rgba(255,255,255,0.2);
    font-family: "JetBrains Mono";
    font-size: 9px;
    margin-top: 12px;
}
"""

MODES = [
    ("󰌢", "laptop"),
    ("󰍺", "mirror"),
    ("󰍹󰌢", "extend"),
    ("󰍹", "external"),
]


def get_current_mode():
    if os.path.exists(MODE_FILE):
        with open(MODE_FILE) as f:
            return f.read().strip()
    return "extend"


def get_external_monitor():
    import pathlib

    drm = pathlib.Path("/sys/class/drm")
    for connector in sorted(drm.iterdir()):
        status = connector / "status"
        if status.exists() and status.read_text().strip() == "connected":
            name = connector.name
            for prefix in ("card0-", "card1-", "card2-"):
                name = name.replace(prefix, "")
            if name != LAPTOP:
                return name
    return None


def get_clients():
    r = subprocess.run(["hyprctl", "clients", "-j"], capture_output=True, text=True)
    return json.loads(r.stdout)


def get_workspaces():
    r = subprocess.run(["hyprctl", "workspaces", "-j"], capture_output=True, text=True)
    return json.loads(r.stdout)


def move_windows_to_workspace(target_ws):
    for c in get_clients():
        if c["workspace"]["id"] != target_ws:
            subprocess.run(
                [
                    "hyprctl",
                    "dispatch",
                    "movetoworkspacesilent",
                    f"{target_ws},address:{c['address']}",
                ]
            )
    subprocess.run(["hyprctl", "dispatch", "workspace", str(target_ws)])


def move_windows_from_monitor(monitor, target_ws):
    ws_ids = {w["id"] for w in get_workspaces() if w["monitor"] == monitor}
    for c in get_clients():
        if c["workspace"]["id"] in ws_ids:
            subprocess.run(
                [
                    "hyprctl",
                    "dispatch",
                    "movetoworkspacesilent",
                    f"{target_ws},address:{c['address']}",
                ]
            )


def wait_for_monitor(name, timeout=4):
    start = time.time()
    while time.time() - start < timeout:
        r = subprocess.run(
            ["hyprctl", "monitors", "-j"], capture_output=True, text=True
        )
        if any(m["name"] == name for m in json.loads(r.stdout)):
            return True
        time.sleep(0.1)
    return False


def run_monitor(mode):
    ext = get_external_monitor()
    if not ext and mode != "laptop":
        return

    with open(MODE_FILE, "w") as f:
        f.write(mode)

    if mode == "laptop":
        move_windows_from_monitor(ext, 1)
        time.sleep(0.3)
        subprocess.run(f"hyprctl keyword monitor {ext},disabled", shell=True)
        subprocess.run("hyprctl keyword monitor eDP-1,1920x1080@60,0x0,1", shell=True)

    elif mode == "mirror":
        move_windows_to_workspace(1)
        time.sleep(0.3)
        subprocess.run("hyprctl keyword monitor eDP-1,1920x1080@60,0x0,1", shell=True)
        subprocess.run(
            f"hyprctl keyword monitor {ext},1920x1080@60,0x0,1,mirror,eDP-1", shell=True
        )

    elif mode == "extend":
        subprocess.run(f"hyprctl keyword monitor {ext},1920x1080@60,1920x0,1", shell=True)
        wait_for_monitor(ext)
        subprocess.run("hyprctl keyword monitor eDP-1,1920x1080@60,0x0,1", shell=True)

    elif mode == "external":
        subprocess.run(f"hyprctl keyword monitor {ext},1920x1080@60,1920x0,1", shell=True)
        wait_for_monitor(ext)
        ws_ids = {w["id"] for w in get_workspaces() if w["monitor"] == ext}
        target = min(ws_ids) if ws_ids else 3
        move_windows_from_monitor(LAPTOP, target)
        time.sleep(0.3)
        subprocess.run(f"hyprctl keyword monitor {LAPTOP},disabled", shell=True)
        subprocess.run(f"hyprctl keyword monitor {ext},1920x1080@60,0x0,1", shell=True)

    subprocess.Popen("sleep 0.5 && killall waybar; waybar &", shell=True)

    icons = {"laptop": "󰌢", "mirror": "󰍺", "extend": "󰍹󰌢", "external": "󰍹"}
    names = {
        "laptop": "Laptop only",
        "mirror": "Mirror",
        "extend": "Extended",
        "external": "External only",
    }
    subprocess.Popen(
        [
            "notify-send",
            icons[mode] + " Display",
            names[mode],
            "--hint=string:x-dunst-stack-tag:monitor",
            "--expire-time=2000",
        ]
    )


class MonitorPicker(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.set_decorated(False)
        self.current_mode = get_current_mode()

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, False)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.get_style_context().add_class("popup-box")
        self.add(outer)

        title = Gtk.Label(label="󰍹  DISPLAY MODE")
        title.get_style_context().add_class("title")
        title.set_halign(Gtk.Align.CENTER)
        outer.pack_start(title, False, False, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        row.set_halign(Gtk.Align.CENTER)
        outer.pack_start(row, False, False, 0)

        self.buttons = []
        for icon, mode in MODES:
            btn = Gtk.Button(label=icon)
            btn.get_style_context().add_class("btn")
            if mode == self.current_mode:
                btn.get_style_context().add_class("btn-active")
            btn.connect("clicked", self.on_click, mode)
            row.pack_start(btn, False, False, 0)
            self.buttons.append((btn, mode))

        hint = Gtk.Label(label="← → navigate  •  Enter confirm  •  Esc cancel")
        hint.get_style_context().add_class("hint")
        hint.set_halign(Gtk.Align.CENTER)
        outer.pack_start(hint, False, False, 0)

        self.connect("key-press-event", self.on_key)

        self.current_idx = next(
            (i for i, (_, m) in enumerate(MODES) if m == self.current_mode), 2
        )

        self.show_all()

    def on_click(self, btn, mode):
        run_monitor(mode)
        Gtk.main_quit()

    def on_key(self, widget, event):
        name = Gdk.keyval_name(event.keyval)
        if name == "Escape":
            Gtk.main_quit()
        elif name == "Return":
            _, mode = MODES[self.current_idx]
            run_monitor(mode)
            Gtk.main_quit()
        elif name == "Right":
            self.current_idx = (self.current_idx + 1) % len(MODES)
            self.update_selection()
        elif name == "Left":
            self.current_idx = (self.current_idx - 1) % len(MODES)
            self.update_selection()
        return True

    def update_selection(self):
        for i, (btn, mode) in enumerate(self.buttons):
            ctx = btn.get_style_context()
            ctx.remove_class("btn-active")
            if i == self.current_idx:
                ctx.add_class("btn-active")


if __name__ == "__main__":
    win = MonitorPicker()
    Gtk.main()
