#!/usr/bin/env python3
"""App launcher with category grouping, search and collapsible sections."""

import configparser
import json
import os
import re
import socket
import subprocess
import sys
import threading

import cairo
import glob
import select
import struct
import gi

gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, GtkLayerShell, Pango

ICON_SIZE = 64
APPS_DIRS = [
    "/usr/share/applications",
    os.path.expanduser("~/.local/share/applications"),
]

CATEGORY_MAP = {
    "AudioVideo": "Медиа", "Audio": "Медиа", "Video": "Медиа",
    "Development": "Разработка",
    "Education": "Образование",
    "Game": "Игры",
    "Graphics": "Графика",
    "Network": "Интернет",
    "Office": "Офис",
    "Science": "Наука",
    "Settings": "Настройки",
    "System": "Система",
    "Utility": "Утилиты",
}

CATEGORY_ORDER = [
    "Интернет", "Офис", "Медиа", "Графика", "Разработка",
    "Система", "Утилиты", "Настройки", "Игры", "Образование", "Другое",
]

CSS = b"""
window { background: transparent; }

.dim {
    background: rgba(0, 0, 0, 0.45);
}
.launcher-box {
    background: rgba(20, 20, 28, 0.97);
    border-radius: 16px;
    border: 1px solid rgba(127, 119, 221, 0.2);
}
.search-wrap {
    background: rgba(30, 30, 42, 0.95);
    border-radius: 12px;
    border: 1px solid rgba(127, 119, 221, 0.22);
    padding: 2px 12px;
}
.search-entry {
    background: transparent;
    border: none;
    box-shadow: none;
    color: #cccccc;
    font-size: 14px;
}
.search-entry:focus { box-shadow: none; }

.cat-btn {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 8px 10px;
    color: rgba(127, 119, 221, 0.9);
    font-size: 14px;
    font-weight: bold;
    letter-spacing: 1px;
}
.cat-btn:hover { background: rgba(127, 119, 221, 0.1); }

.app-btn {
    background: transparent;
    border: none;
    border-radius: 12px;
    padding: 10px 6px;
}
.app-btn:hover { background: rgba(127, 119, 221, 0.18); }

.app-label {
    color: #bbbbbb;
    font-size: 13px;
}
"""


def load_apps():
    apps = {}
    for d in APPS_DIRS:
        if not os.path.isdir(d):
            continue
        for fname in sorted(os.listdir(d)):
            if not fname.endswith(".desktop"):
                continue
            try:
                cp = configparser.RawConfigParser()
                cp.read(os.path.join(d, fname), encoding="utf-8")
                if not cp.has_section("Desktop Entry"):
                    continue
                s = cp["Desktop Entry"]
                if s.get("NoDisplay", "false").lower() == "true":
                    continue
                if s.get("Type", "") != "Application":
                    continue
                name = s.get("Name", "").strip()
                exec_ = s.get("Exec", "").strip()
                if not name or not exec_:
                    continue
                apps[fname] = {
                    "name": name,
                    "exec": exec_,
                    "icon": s.get("Icon", "").strip(),
                    "categories": s.get("Categories", ""),
                }
            except Exception:
                continue
    return apps


def categorize(apps):
    groups = {}
    for app in apps.values():
        assigned = "Другое"
        for c in app["categories"].split(";"):
            c = c.strip()
            if c in CATEGORY_MAP:
                assigned = CATEGORY_MAP[c]
                break
        groups.setdefault(assigned, []).append(app)
    for g in groups.values():
        g.sort(key=lambda a: a["name"].lower())
    return groups


def make_icon(icon_name):
    img = Gtk.Image()
    img.set_pixel_size(ICON_SIZE)
    if not icon_name:
        img.set_from_icon_name("application-x-executable", Gtk.IconSize.INVALID)
        return img
    if os.path.isabs(icon_name) and os.path.isfile(icon_name):
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                icon_name, ICON_SIZE, ICON_SIZE, True
            )
            img.set_from_pixbuf(pb)
            return img
        except Exception:
            pass
    theme = Gtk.IconTheme.get_default()
    if theme.has_icon(icon_name):
        img.set_from_icon_name(icon_name, Gtk.IconSize.INVALID)
    else:
        img.set_from_icon_name("application-x-executable", Gtk.IconSize.INVALID)
    return img


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


def do_launch(exec_str):
    cmd = re.sub(r"%[fFuUdDnNickvm]", "", exec_str).strip()
    subprocess.Popen(cmd, shell=True)
    Gtk.main_quit()


def setup_css():
    p = Gtk.CssProvider()
    p.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


class DimWindow(Gtk.Window):
    def __init__(self, monitor):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.set_app_paintable(True)
        vis = self.get_screen().get_rgba_visual()
        if vis:
            self.set_visual(vis)

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        GtkLayerShell.set_monitor(self, monitor)
        for edge in [GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                     GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT]:
            GtkLayerShell.set_anchor(self, edge, True)

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("button-press-event", lambda w, e: Gtk.main_quit())
        self.connect("draw", self._on_draw)
        self.show_all()

    def _on_draw(self, _w, cr):
        cr.set_source_rgba(0, 0, 0, 0.45)
        cr.paint()
        return False


class Launcher(Gtk.Window):
    def __init__(self, monitor=None, monitor_name=""):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.set_app_paintable(True)

        vis = self.get_screen().get_rgba_visual()
        if vis:
            self.set_visual(vis)

        # Full-screen layer surface on the given monitor
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        if monitor:
            GtkLayerShell.set_monitor(self, monitor)
        for edge in [GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                     GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT]:
            GtkLayerShell.set_anchor(self, edge, True)

        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self._on_key)

        GLib.timeout_add(400, self._start_ipc_watcher)
        if monitor:
            geo = monitor.get_geometry()
            threading.Thread(
                target=watch_mouse_clicks,
                args=(Gtk.main_quit, geo.x, geo.y, geo.width, geo.height),
                daemon=True,
            ).start()

        self._setup_css()
        self._groups = categorize(load_apps())
        self._sections = {}

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("button-press-event", self._on_bg_click)

        dim = Gtk.Box()
        dim.get_style_context().add_class("dim")
        self.add(dim)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.get_style_context().add_class("launcher-box")
        box.set_size_request(800, 580)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        dim.pack_start(box, True, False, 0)
        self._content = box

        inner = Gtk.EventBox()
        inner.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        inner.connect("button-press-event", lambda w, e: True)
        box.pack_start(inner, True, True, 0)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.set_margin_start(16)
        root.set_margin_end(16)
        root.set_margin_top(16)
        root.set_margin_bottom(16)
        inner.add(root)

        wrap = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        wrap.get_style_context().add_class("search-wrap")
        wrap.pack_start(Gtk.Label(label=" "), False, False, 0)
        self._entry = Gtk.Entry()
        self._entry.set_placeholder_text("Поиск приложений...")
        self._entry.get_style_context().add_class("search-entry")
        self._entry.connect("changed", self._on_search)
        wrap.pack_start(self._entry, True, True, 0)
        root.pack_start(wrap, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_margin_top(14)
        root.pack_start(scrolled, True, True, 0)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scrolled.add(content)

        for cat in CATEGORY_ORDER:
            apps = self._groups.get(cat)
            if not apps:
                continue

            header = Gtk.Button(label=f"▾  {cat.upper()}")
            header.get_style_context().add_class("cat-btn")
            header.set_halign(Gtk.Align.START)
            header.connect("clicked", self._toggle, cat, header)
            content.pack_start(header, False, False, 0)

            revealer = Gtk.Revealer()
            revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
            revealer.set_transition_duration(150)
            revealer.set_reveal_child(True)

            flow = Gtk.FlowBox()
            flow.set_max_children_per_line(30)
            flow.set_selection_mode(Gtk.SelectionMode.NONE)
            flow.set_column_spacing(4)
            flow.set_row_spacing(4)
            flow.set_margin_bottom(10)
            revealer.add(flow)
            content.pack_start(revealer, False, False, 0)

            self._sections[cat] = (revealer, flow, list(apps))
            for app in apps:
                self._add_tile(flow, app)

        self.show_all()
        GLib.idle_add(self._entry.grab_focus)

    def _start_ipc_watcher(self):
        t = threading.Thread(
            target=watch_hyprland, args=(Gtk.main_quit,), daemon=True
        )
        t.start()
        return False

    def _add_tile(self, flow, app):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box.set_size_request(90, -1)

        icon = make_icon(app["icon"])
        icon.set_halign(Gtk.Align.CENTER)

        lbl = Gtk.Label(label=app["name"])
        lbl.set_ellipsize(Pango.EllipsizeMode.END)
        lbl.set_max_width_chars(11)
        lbl.set_halign(Gtk.Align.CENTER)
        lbl.get_style_context().add_class("app-label")

        box.pack_start(icon, False, False, 0)
        box.pack_start(lbl, False, False, 0)

        btn = Gtk.Button()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.get_style_context().add_class("app-btn")
        btn.add(box)
        btn.connect("clicked", lambda _b, a=app: do_launch(a["exec"]))
        flow.add(btn)

    def _toggle(self, _btn, cat, header):
        revealer, _, _ = self._sections[cat]
        visible = revealer.get_reveal_child()
        revealer.set_reveal_child(not visible)
        header.set_label(f"{'▸' if visible else '▾'}  {cat.upper()}")

    def _on_search(self, entry):
        query = entry.get_text().lower().strip()
        for cat, (revealer, flow, apps) in self._sections.items():
            for ch in flow.get_children():
                flow.remove(ch)
            if query:
                filtered = [a for a in apps if query in a["name"].lower()]
                revealer.set_reveal_child(bool(filtered))
            else:
                filtered = apps
                revealer.set_reveal_child(True)
            for app in filtered:
                self._add_tile(flow, app)
            flow.show_all()

    def _on_bg_click(self, _win, event):
        alloc = self._content.get_allocation()
        cx, cy = self._content.translate_coordinates(self, 0, 0)
        if not (cx <= event.x <= cx + alloc.width and cy <= event.y <= cy + alloc.height):
            Gtk.main_quit()

    def _on_key(self, _win, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()

    def _setup_css(self):
        setup_css()


if __name__ == "__main__":
    _lock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        _lock.bind("\0app-launcher")
    except OSError:
        sys.exit(0)

    setup_css()

    display = Gdk.Display.get_default()
    cx, cy = _hypr_cursorpos()
    if cx is None:
        cx, cy = 0, 0
    else:
        cx, cy = int(cx), int(cy)

    active_monitor = display.get_monitor(0)
    active_mon_name = ""
    for i in range(display.get_n_monitors()):
        mon = display.get_monitor(i)
        geo = mon.get_geometry()
        if geo.x <= cx < geo.x + geo.width and geo.y <= cy < geo.y + geo.height:
            active_monitor = mon
            break

    try:
        monitors = json.loads(subprocess.check_output(["hyprctl", "monitors", "-j"], text=True))
        for m in monitors:
            if m.get("focused"):
                active_mon_name = m["name"]
                break
    except Exception:
        pass

    n = display.get_n_monitors()
    for i in range(n):
        mon = display.get_monitor(i)
        if mon == active_monitor:
            Launcher(mon, active_mon_name)
        else:
            DimWindow(mon)

    Gtk.main()
