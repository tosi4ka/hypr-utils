#!/usr/bin/env python3
import fcntl
import glob
import json
import os
import select
import socket
import struct
import subprocess
import threading
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
LAPTOP = "eDP-1"

CSS = b"""
window {
    background: transparent;
}
.dim {
    background: rgba(0, 0, 0, 0.45);
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


WS_MAP_FILE = "/tmp/hypr-monitor-ws-mapping.json"


def save_workspace_mapping():
    try:
        workspaces = get_workspaces()
        mapping = {}
        for ws in workspaces:
            mapping.setdefault(ws["monitor"], []).append(ws["id"])
        with open(WS_MAP_FILE, "w") as f:
            json.dump(mapping, f)
    except Exception:
        pass


def restore_workspace_mapping():
    try:
        with open(WS_MAP_FILE) as f:
            mapping = json.load(f)
        for monitor, ws_ids in mapping.items():
            for ws_id in ws_ids:
                subprocess.run(
                    ["hyprctl", "dispatch", "moveworkspacetomonitor",
                     f"{ws_id} {monitor}"],
                    capture_output=True,
                )
    except Exception:
        pass


def run_monitor(mode):
    ext = get_external_monitor()
    if not ext and mode != "laptop":
        return

    if get_current_mode() == "extend" and mode != "extend":
        save_workspace_mapping()

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
        time.sleep(0.3)
        restore_workspace_mapping()

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
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.current_mode = get_current_mode()

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

        dim = Gtk.Box()
        dim.get_style_context().add_class("dim")
        self.add(dim)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.get_style_context().add_class("popup-box")
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)
        dim.pack_start(outer, True, False, 0)
        self._popup = outer

        content_eb = Gtk.EventBox()
        content_eb.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        content_eb.connect("button-press-event", lambda w, e: True)
        outer.pack_start(content_eb, True, True, 0)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_eb.add(content)

        title = Gtk.Label(label="󰍹  DISPLAY MODE")
        title.get_style_context().add_class("title")
        title.set_halign(Gtk.Align.CENTER)
        content.pack_start(title, False, False, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        row.set_halign(Gtk.Align.CENTER)
        content.pack_start(row, False, False, 0)

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
        content.pack_start(hint, False, False, 0)

        self.connect("key-press-event", self.on_key)

        self.current_idx = next(
            (i for i, (_, m) in enumerate(MODES) if m == self.current_mode), 2
        )

        self.show_all()

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

    def on_click(self, btn, mode):
        if mode == self.current_mode:
            return
        run_monitor(mode)
        Gtk.main_quit()

    def on_key(self, widget, event):
        name = Gdk.keyval_name(event.keyval)
        if name == "Escape":
            Gtk.main_quit()
        elif name == "Return":
            _, mode = MODES[self.current_idx]
            if mode != self.current_mode:
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
