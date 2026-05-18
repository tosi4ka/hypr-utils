#!/usr/bin/env python3
import os
import subprocess
import sys

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk

CSS = b"""
window { background: transparent; }
.popup-box {
    background-color: rgba(235, 235, 235, 0.97);
    border-radius: 12px;
    padding: 10px 14px 6px 14px;
    border: 1px solid rgba(0,0,0,0.12);
}
.char-btn {
    background-color: transparent;
    color: #1a1a1a;
    border-radius: 6px;
    border: none;
    font-size: 18px;
    min-width: 32px;
    min-height: 32px;
    margin: 0 2px;
    padding: 0;
}
.char-btn-selected {
    background-color: rgba(74, 144, 217, 0.85);
    color: white;
    border-radius: 6px;
}
.num-label { color: #999999; font-size: 9px; margin-top: 1px; }
"""


def get_cursor_pos():
    if len(sys.argv) >= 4:
        try:
            x, y = int(sys.argv[2]), int(sys.argv[3])
            if x >= 0 and y >= 0:
                return x, y
        except (ValueError, IndexError):
            pass
    try:
        env = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")}
        out = subprocess.check_output(["xdotool", "getmouselocation"], env=env).decode()
        x = int([p for p in out.split() if p.startswith("x:")][0].split(":")[1])
        y = int([p for p in out.split() if p.startswith("y:")][0].split(":")[1])
        return x, y
    except Exception:
        return 960, 500


def main():
    if len(sys.argv) < 2:
        sys.exit(1)
    variants = sys.argv[1].split()
    if not variants:
        sys.exit(1)

    selected = [None]
    current = [0]
    buttons = []

    provider = Gtk.CssProvider()
    provider.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    win.set_decorated(False)
    win.set_app_paintable(True)
    win.set_keep_above(True)
    win.set_skip_taskbar_hint(True)
    win.set_skip_pager_hint(True)
    win.set_accept_focus(True)
    win.set_focus_on_map(True)

    screen = win.get_screen()
    visual = screen.get_rgba_visual()
    if visual:
        win.set_visual(visual)

    outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    outer.get_style_context().add_class("popup-box")
    win.add(outer)

    def update_selection():
        for i, btn in enumerate(buttons):
            ctx = btn.get_style_context()
            ctx.remove_class("char-btn-selected")
            if i == current[0]:
                ctx.add_class("char-btn-selected")

    def choose(char):
        selected[0] = char
        win.destroy()
        Gtk.main_quit()

    def close():
        win.destroy()
        Gtk.main_quit()

    for i, char in enumerate(variants, 1):
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        col.set_halign(Gtk.Align.CENTER)

        btn = Gtk.Button(label=char)
        btn.get_style_context().add_class("char-btn")
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.connect("clicked", lambda b, c=char: choose(c))
        col.pack_start(btn, False, False, 0)
        buttons.append(btn)

        num = Gtk.Label(label=str(i))
        num.get_style_context().add_class("num-label")
        col.pack_start(num, False, False, 0)

        outer.pack_start(col, False, False, 0)

    update_selection()
    win.show_all()
    win.realize()

    # Позиция
    cx, cy = get_cursor_pos()
    display = Gdk.Display.get_default()
    monitor = display.get_monitor_at_point(cx, cy)
    geom = monitor.get_geometry()
    w, h = win.get_size()
    x = max(geom.x, min(cx - w // 2, geom.x + geom.width - w))
    y = cy + 10
    if y + h > geom.y + geom.height:
        y = cy - h - 30
    win.move(x, y)

    # Захват клавиатуры
    def grab_kb():
        win.present()
        win.grab_focus()
        seat = Gdk.Display.get_default().get_default_seat()
        seat.grab(
            win.get_window(),
            Gdk.SeatCapabilities.KEYBOARD,
            False,
            None,
            None,
            None,
            None,
        )
        return False

    GLib.timeout_add(150, grab_kb)

    def on_key(widget, event):
        key = Gdk.keyval_name(event.keyval)
        if key == "Escape":
            close()
        elif key in ("Return", "KP_Enter"):
            choose(variants[current[0]])
        elif key == "Right":
            current[0] = (current[0] + 1) % len(variants)
            update_selection()
        elif key == "Left":
            current[0] = (current[0] - 1) % len(variants)
            update_selection()
        elif key and key.isdigit():
            idx = int(key) - 1
            if 0 <= idx < len(variants):
                choose(variants[idx])
        return True

    win.connect("key-press-event", on_key)
    win.connect("focus-out-event", lambda w, e: close())

    Gtk.main()

    if selected[0]:
        print(selected[0], end="")


if __name__ == "__main__":
    main()
