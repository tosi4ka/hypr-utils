#!/usr/bin/env python3
"""Alt+Tab window switcher for Hyprland."""

import json
import subprocess

import gi
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, Gtk, GtkLayerShell

ICON_SIZE = 64
BTN_PAD   = 12   # padding around icon inside button

CSS = b"""
window { background: transparent; }

.switcher-bg {
    background: rgba(20, 20, 28, 0.92);
    border-radius: 18px;
    padding: 24px 28px 20px;
    border: 1px solid rgba(127, 119, 221, 0.30);
}
.win-cell {
    border-radius: 12px;
    padding: 10px;
    min-width: 80px;
    min-height: 80px;
}
.win-cell-selected {
    background: rgba(127, 119, 221, 0.30);
}
.win-title {
    color: #cccccc;
    font-size: 13px;
    margin-top: 14px;
}
.win-sub {
    color: #555555;
    font-size: 11px;
    margin-top: 2px;
}
"""


def _get_windows():
    try:
        r = subprocess.run(["hyprctl", "clients", "-j"],
                           capture_output=True, text=True, timeout=1)
        clients = json.loads(r.stdout or "[]")
        return [c for c in clients
                if c.get("mapped")
                and not c["workspace"]["name"].startswith("special")]
    except Exception:
        return []


def _get_active_addr():
    try:
        r = subprocess.run(["hyprctl", "activewindow", "-j"],
                           capture_output=True, text=True, timeout=0.5)
        w = json.loads(r.stdout or "{}")
        return w.get("address", "")
    except Exception:
        return ""


def _load_icon(cls):
    theme = Gtk.IconTheme.get_default()
    for name in (cls, cls.lower(), cls.capitalize()):
        try:
            pb = theme.load_icon(name, ICON_SIZE, Gtk.IconLookupFlags.FORCE_SIZE)
            img = Gtk.Image.new_from_pixbuf(pb)
            img.set_halign(Gtk.Align.CENTER)
            return img
        except Exception:
            pass
    img = Gtk.Image.new_from_icon_name("application-x-executable",
                                       Gtk.IconSize.DIALOG)
    img.set_halign(Gtk.Align.CENTER)
    return img


class Switcher(Gtk.Window):
    def __init__(self, windows, start_idx):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.windows  = windows
        self.selected = start_idx
        self.cells    = []

        self.set_decorated(False)
        self.set_app_paintable(True)
        vis = self.get_screen().get_rgba_visual()
        if vis:
            self.set_visual(vis)

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
        for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                     GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(self, edge, True)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)

        bg = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        bg.get_style_context().add_class("switcher-bg")
        outer.pack_start(bg, False, False, 0)

        # Icon row
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.set_halign(Gtk.Align.CENTER)
        bg.pack_start(row, False, False, 0)

        for win in windows:
            cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            cell.get_style_context().add_class("win-cell")
            cell.pack_start(_load_icon(win["class"]), False, False, 0)
            self.cells.append(cell)
            row.pack_start(cell, False, False, 0)

        self.lbl_sub = Gtk.Label(label="")
        self.lbl_sub.get_style_context().add_class("win-sub")
        bg.pack_start(self.lbl_sub, False, False, 0)

        self.add(outer)
        self._refresh()
        self.show_all()

        self.connect("key-press-event",   self._on_press)
        self.connect("key-release-event", self._on_release)
        self.connect("focus-out-event",   lambda *_: self._close())

    def _refresh(self):
        for i, cell in enumerate(self.cells):
            ctx = cell.get_style_context()
            if i == self.selected:
                ctx.add_class("win-cell-selected")
            else:
                ctx.remove_class("win-cell-selected")

        if self.windows:
            w = self.windows[self.selected]
            self.lbl_sub.set_text(f"Workspace {w['workspace']['name']}")

    def _confirm(self):
        if self.windows:
            addr = self.windows[self.selected]["address"]
            subprocess.Popen(["hyprctl", "dispatch", "focuswindow",
                              f"address:{addr}"])
        self._close()

    def _close(self):
        Gtk.main_quit()

    def _on_press(self, _w, event):
        key = Gdk.keyval_name(event.keyval)
        if key == "Escape":
            self._close()
        elif key in ("Return", "KP_Enter"):
            self._confirm()
        elif key in ("Tab", "Right"):
            self.selected = (self.selected + 1) % len(self.windows)
            self._refresh()
        elif key in ("ISO_Left_Tab", "Left"):
            self.selected = (self.selected - 1) % len(self.windows)
            self._refresh()
        return True

    def _on_release(self, _w, event):
        key = Gdk.keyval_name(event.keyval)
        if key in ("Alt_L", "Alt_R"):
            self._confirm()
        return True


def main():
    windows = _get_windows()
    if not windows:
        return

    provider = Gtk.CssProvider()
    provider.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    active = _get_active_addr()
    cur = next((i for i, w in enumerate(windows) if w["address"] == active), -1)
    start = (cur + 1) % len(windows) if len(windows) > 1 else 0

    Switcher(windows, start)
    Gtk.main()


if __name__ == "__main__":
    main()
