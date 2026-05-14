#!/usr/bin/env python3
import os
import subprocess
import sys
from datetime import datetime

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, GLib, Gtk, GtkLayerShell

SAVE_DIR = os.path.expanduser("~/Pictures/Screenshots")
os.makedirs(SAVE_DIR, exist_ok=True)

CSS = b"""
* {
    font-family: "JetBrains Mono", monospace;
}
window {
    background: transparent;
}
.popup-box {
    background-color: rgba(20, 20, 30, 0.95);
    border-radius: 14px;
    padding: 10px 16px;
    border: 1px solid rgba(127, 119, 221, 0.4);
}
.btn {
    background-color: transparent;
    color: #ccc;
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.08);
    font-size: 13px;
    min-width: 90px;
    min-height: 64px;
    margin: 4px;
    padding: 8px 12px;
}
.btn-label {
    color: #888;
    font-size: 10px;
    margin-top: 4px;
}
.btn-icon {
    font-size: 42px;
    color: #ccc;
}
.btn-icon-shifted {
    margin-left: -15px;
}
.btn-active {
    background-color: rgba(127, 119, 221, 0.25);
    border: 1px solid rgba(127, 119, 221, 0.7);
    color: #fff;
}
.btn-active .btn-icon {
    color: #fff;
}
.btn-active .btn-label {
    color: #aaa;
}
.hint {
    color: rgba(255,255,255,0.2);
    font-size: 9px;
    margin-top: 6px;
}
"""

BUTTONS = [
    ("󰩭", "Zone", "zone"),
    ("󱂬", "Window", "window"),
    ("󰍹", "Monitor", "monitor"),
    ("󰍺", "All", "all"),
]


def get_timestamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def copy_to_clipboard(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
        proc = subprocess.Popen(
            ["wl-copy", "--type", "image/png"],
            stdin=subprocess.PIPE
        )
        proc.stdin.write(data)
        proc.stdin.close()
    except Exception as e:
        print(f"[screenshot] clipboard error: {e}")


def do_screenshot(mode):
    ts = get_timestamp()
    out = os.path.join(SAVE_DIR, f"screenshot-{ts}.png")

    try:
        if mode == "zone":
            geo = (
                subprocess.check_output(["slurp"], stderr=subprocess.DEVNULL)
                .decode()
                .strip()
            )
            if not geo:
                return
            subprocess.run(["grim", "-g", geo, out], check=True)

        elif mode == "window":
            clients = subprocess.check_output(["hyprctl", "clients", "-j"]).decode()
            import json

            windows = json.loads(clients)
            hints = "\n".join(
                f"{w['at'][0]},{w['at'][1]} {w['size'][0]}x{w['size'][1]}"
                for w in windows
                if w["size"][0] > 0 and w["size"][1] > 0
            )
            geo = (
                subprocess.check_output(
                    ["slurp"], input=hints.encode(), stderr=subprocess.DEVNULL
                )
                .decode()
                .strip()
            )
            if not geo:
                return
            subprocess.run(["grim", "-g", geo, out], check=True)

        elif mode == "monitor":
            monitors_json = subprocess.check_output(
                ["hyprctl", "monitors", "-j"]
            ).decode()
            import json

            monitors = json.loads(monitors_json)
            hints = "\n".join(
                f"{m['x']},{m['y']} {m['width']}x{m['height']}" for m in monitors
            )
            geo = (
                subprocess.check_output(
                    ["slurp"], input=hints.encode(), stderr=subprocess.DEVNULL
                )
                .decode()
                .strip()
            )
            if not geo:
                return
            subprocess.run(["grim", "-g", geo, out], check=True)

        elif mode == "all":
            subprocess.run(["grim", out], check=True)

        if os.path.exists(out):
            copy_to_clipboard(out)
            subprocess.Popen(
                [
                    "notify-send",
                    "󰩭 Screenshot",
                    f"Saved: {os.path.basename(out)}",
                    "--expire-time=2000",
                ]
            )

    except subprocess.CalledProcessError:
        pass
    except Exception as e:
        print(f"[screenshot] error: {e}")


class ScreenshotPicker(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.current = 0
        self.btns = []

        self.set_decorated(False)

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, False)

        screen = self.get_screen()

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.get_style_context().add_class("popup-box")
        self.add(outer)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        outer.pack_start(row, False, False, 0)

        for i, (icon, label, mode) in enumerate(BUTTONS):
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            col.set_halign(Gtk.Align.CENTER)

            btn = Gtk.Button()
            btn.get_style_context().add_class("btn")
            btn.set_relief(Gtk.ReliefStyle.NONE)

            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            inner.set_halign(Gtk.Align.CENTER)

            icon_lbl = Gtk.Label(label=icon)
            icon_lbl.get_style_context().add_class("btn-icon")
            if i != 0:
                icon_lbl.get_style_context().add_class("btn-icon-shifted")
            inner.pack_start(icon_lbl, False, False, 0)

            text_lbl = Gtk.Label(label=label)
            text_lbl.get_style_context().add_class("btn-label")
            inner.pack_start(text_lbl, False, False, 0)

            btn.add(inner)
            btn.connect("clicked", lambda b, m=mode: self.choose(m))
            col.pack_start(btn, False, False, 0)
            row.pack_start(col, False, False, 0)
            self.btns.append(btn)

        hint = Gtk.Label(label="← → navigate  •  Enter confirm  •  Esc cancel")
        hint.get_style_context().add_class("hint")
        hint.set_halign(Gtk.Align.CENTER)
        outer.pack_start(hint, False, False, 0)

        self.connect("key-press-event", self.on_key)
        self.connect("focus-out-event", lambda w, e: self.close_win())
        self.update_selection()

        self.show_all()

    def update_selection(self):
        for i, btn in enumerate(self.btns):
            ctx = btn.get_style_context()
            if i == self.current:
                ctx.add_class("btn-active")
            else:
                ctx.remove_class("btn-active")

    def choose(self, mode):
        self.hide()
        while Gtk.events_pending():
            Gtk.main_iteration()
        do_screenshot(mode)
        Gtk.main_quit()

    def close_win(self):
        self.destroy()
        Gtk.main_quit()

    def on_key(self, widget, event):
        key = Gdk.keyval_name(event.keyval)
        if key == "Escape":
            self.close_win()
        elif key in ("Return", "KP_Enter"):
            self.choose(BUTTONS[self.current][2])
        elif key == "Right":
            self.current = (self.current + 1) % len(BUTTONS)
            self.update_selection()
        elif key == "Left":
            self.current = (self.current - 1) % len(BUTTONS)
            self.update_selection()
        elif key and key.isdigit():
            idx = int(key) - 1
            if 0 <= idx < len(BUTTONS):
                self.choose(BUTTONS[idx][2])
        return True


if __name__ == "__main__":
    ScreenshotPicker()
    Gtk.main()
