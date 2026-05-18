#!/usr/bin/env python3

import glob
import json
import os
import select
import socket
import struct
import subprocess
import sys
import threading

import gi
gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, GLib, Gtk, GtkLayerShell

ACTIONS = [
    ("󰌾", "Блокировка", "hyprlock",           "lock"),
    ("󰤄", "Сон",         "systemctl suspend",  "suspend"),
    ("󰜉", "Перезагрузка","systemctl reboot",   "reboot"),
    ("󰐥", "Выключение",  "systemctl poweroff", "shutdown"),
]

CSS = b"""
window { background: transparent; }
.dim { background: rgba(0, 0, 0, 0.55); }
.popup {
    background: rgba(20, 20, 28, 0.97);
    border-radius: 16px;
    border: 1px solid rgba(127, 119, 221, 0.2);
    padding: 28px 20px 20px;
}
.title {
    color: rgba(127, 119, 221, 0.7);
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 2px;
    margin-bottom: 20px;
}
.btn {
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 12px;
    min-width: 86px;
    padding: 0;
    margin: 4px;
}
.btn-icon {
    font-size: 30px;
    margin-bottom: 4px;
}
.btn-lbl {
    font-size: 10px;
    color: #666;
}
.btn-lock   .btn-icon { color: #7f77dd; }
.btn-suspend .btn-icon { color: #7f77dd; }
.btn-reboot  .btn-icon { color: #fac775; }
.btn-shutdown .btn-icon { color: #f09595; }

.btn-lock:hover,    .btn-lock.btn-active    { background: rgba(127,119,221,0.12); border-color: rgba(127,119,221,0.5); }
.btn-suspend:hover, .btn-suspend.btn-active { background: rgba(127,119,221,0.12); border-color: rgba(127,119,221,0.5); }
.btn-reboot:hover,  .btn-reboot.btn-active  { background: rgba(250,199,117,0.10); border-color: rgba(250,199,117,0.5); }
.btn-shutdown:hover,.btn-shutdown.btn-active { background: rgba(240,149,149,0.10); border-color: rgba(240,149,149,0.5); }

.hint {
    color: rgba(255, 255, 255, 0.12);
    font-size: 9px;
    margin-top: 16px;
}
"""


def _hypr_cursorpos():
    sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
    runtime = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    for base in (runtime, "/tmp"):
        path = f"{base}/hypr/{sig}/.socket.sock"
        if os.path.exists(path):
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                    s.connect(path)
                    s.sendall(b"j/cursorpos")
                    data = s.recv(4096)
                pos = json.loads(data.decode())
                return pos["x"], pos["y"]
            except Exception:
                pass
    return None, None


def watch_mouse_clicks(on_click, mon_x, mon_y, mon_w, mon_h):
    EV_KEY, BTN_LEFT, BTN_TOUCH = 1, 0x110, 0x14A
    fds = []
    for dev in sorted(glob.glob("/dev/input/event*")):
        try:
            fds.append(open(dev, "rb", buffering=0))
        except OSError:
            pass
    if not fds:
        return
    try:
        while True:
            r, _, _ = select.select(fds, [], [], 1.0)
            for f in r:
                try:
                    raw = os.read(f.fileno(), 24 * 64)
                except OSError:
                    continue
                for off in range(0, len(raw) - 23, 24):
                    _, _, type_, code, value = struct.unpack_from("QQHHi", raw, off)
                    if type_ == EV_KEY and code in (BTN_LEFT, BTN_TOUCH) and value == 1:
                        cx, cy = _hypr_cursorpos()
                        if cx is not None:
                            if not (mon_x <= cx < mon_x + mon_w and mon_y <= cy < mon_y + mon_h):
                                GLib.idle_add(on_click)
                                return
    except Exception:
        pass
    finally:
        for f in fds:
            try:
                f.close()
            except Exception:
                pass


def watch_hyprland(on_focus_change):
    sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
    runtime = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    candidates = [
        f"/tmp/hypr/{sig}/.socket2.sock",
        f"{runtime}/hypr/{sig}/.socket2.sock",
    ]
    path = next((p for p in candidates if os.path.exists(p)), candidates[0])
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(path)
        buf = ""
        while True:
            data = sock.recv(4096).decode("utf-8", errors="ignore")
            if not data:
                break
            buf += data
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                if line.startswith("activewindow>>"):
                    cls = line.split(">>", 1)[1].split(",")[0]
                    if cls:
                        GLib.idle_add(on_focus_change)
                        return
                if line.startswith("workspace>>"):
                    GLib.idle_add(on_focus_change)
                    return
    except Exception:
        pass


class PowerMenu(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.set_app_paintable(True)

        vis = self.get_screen().get_rgba_visual()
        if vis:
            self.set_visual(vis)

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        for edge in [GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                     GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT]:
            GtkLayerShell.set_anchor(self, edge, True)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("button-press-event", self._on_bg_click)
        self.connect("key-press-event", self._on_key)

        dim = Gtk.Box()
        dim.get_style_context().add_class("dim")
        self.add(dim)

        popup = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        popup.get_style_context().add_class("popup")
        popup.set_halign(Gtk.Align.CENTER)
        popup.set_valign(Gtk.Align.CENTER)
        dim.pack_start(popup, True, False, 0)
        self._popup = popup

        content_eb = Gtk.EventBox()
        content_eb.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        content_eb.connect("button-press-event", lambda w, e: True)
        popup.pack_start(content_eb, True, True, 0)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_eb.add(content)

        title = Gtk.Label(label="ПИТАНИЕ")
        title.get_style_context().add_class("title")
        title.set_halign(Gtk.Align.CENTER)
        content.pack_start(title, False, False, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        row.set_halign(Gtk.Align.CENTER)
        content.pack_start(row, False, False, 0)

        self._buttons = []
        self._current_idx = 0

        for icon, label, _cmd, css_key in ACTIONS:
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            inner.set_margin_top(18)
            inner.set_margin_bottom(14)
            inner.set_margin_start(10)
            inner.set_margin_end(10)

            icon_lbl = Gtk.Label(label=icon)
            icon_lbl.get_style_context().add_class("btn-icon")
            icon_lbl.set_halign(Gtk.Align.CENTER)
            inner.pack_start(icon_lbl, False, False, 0)

            text_lbl = Gtk.Label(label=label)
            text_lbl.get_style_context().add_class("btn-lbl")
            text_lbl.set_halign(Gtk.Align.CENTER)
            inner.pack_start(text_lbl, False, False, 0)

            btn = Gtk.Button()
            btn.get_style_context().add_class("btn")
            btn.get_style_context().add_class(f"btn-{css_key}")
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.add(inner)
            btn.connect("clicked", self._on_action, _cmd)
            row.pack_start(btn, False, False, 0)
            self._buttons.append((btn, css_key))

        hint = Gtk.Label(label="← → навигация  •  Enter выбор  •  Esc отмена")
        hint.get_style_context().add_class("hint")
        hint.set_halign(Gtk.Align.CENTER)
        content.pack_start(hint, False, False, 0)

        self.show_all()
        self._update_selection()

        cx, cy = _hypr_cursorpos()
        if cx is None:
            cx, cy = 0, 0
        else:
            cx, cy = int(cx), int(cy)
        display = Gdk.Display.get_default()
        active_monitor = display.get_monitor(0)
        for i in range(display.get_n_monitors()):
            mon = display.get_monitor(i)
            geo = mon.get_geometry()
            if geo.x <= cx < geo.x + geo.width and geo.y <= cy < geo.y + geo.height:
                active_monitor = mon
                break
        geo = active_monitor.get_geometry()
        threading.Thread(
            target=watch_mouse_clicks,
            args=(Gtk.main_quit, geo.x, geo.y, geo.width, geo.height),
            daemon=True,
        ).start()
        GLib.timeout_add(400, self._start_ipc_watcher)

    def _start_ipc_watcher(self):
        threading.Thread(target=watch_hyprland, args=(Gtk.main_quit,), daemon=True).start()
        return False

    def _on_bg_click(self, _win, event):
        alloc = self._popup.get_allocation()
        cx, cy = self._popup.translate_coordinates(self, 0, 0)
        if not (cx <= event.x <= cx + alloc.width and cy <= event.y <= cy + alloc.height):
            Gtk.main_quit()

    def _on_action(self, _btn, cmd):
        Gtk.main_quit()
        subprocess.Popen(cmd, shell=True)

    def _on_key(self, _win, event):
        name = Gdk.keyval_name(event.keyval)
        if name == "Escape":
            Gtk.main_quit()
        elif name == "Return":
            _btn, _key = self._buttons[self._current_idx]
            _, _, cmd, _ = ACTIONS[self._current_idx]
            Gtk.main_quit()
            subprocess.Popen(cmd, shell=True)
        elif name == "Right":
            self._current_idx = (self._current_idx + 1) % len(ACTIONS)
            self._update_selection()
        elif name == "Left":
            self._current_idx = (self._current_idx - 1) % len(ACTIONS)
            self._update_selection()
        return True

    def _update_selection(self):
        for i, (btn, _) in enumerate(self._buttons):
            ctx = btn.get_style_context()
            if i == self._current_idx:
                ctx.add_class("btn-active")
            else:
                ctx.remove_class("btn-active")


if __name__ == "__main__":
    _lock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        _lock.bind("\0power-menu")
    except OSError:
        sys.exit(0)

    PowerMenu()
    Gtk.main()
