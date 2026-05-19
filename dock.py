#!/usr/bin/env python3
"""Hyprland dock — macOS-style with minimize/restore, settings, drag-to-unpin."""

import json
import os
import socket
import subprocess
import threading

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, GtkLayerShell  # noqa: F401

CONFIG_PATH = os.path.expanduser("~/.config/dock/config.json")
SPECIAL = "special:minimized"

DEFAULT_PINNED = [
    {"cls": "firefox",  "cmd": "firefox",  "icon": "firefox"},
    {"cls": "kitty",    "cmd": "kitty",    "icon": "kitty"},
    {"cls": "vscodium", "cmd": "codium",   "icon": "vscodium"},
    None,
    {"cls": "thunar",   "cmd": "thunar",   "icon": "thunar"},
]

CSS = b"""
window { background: transparent; }

.dock-bg {
    background: rgba(255, 275, 275, 0.18);
    border-radius: 15px;
    padding: 6px 12px 4px;
    border: 1px solid rgba(255, 255, 255, 0.10);
}
.dock-btn {
    background: transparent;
    border: none;
    border-radius: 10px;
    padding: 0;
}
.indicator {
    background: rgba(60, 60, 60, 0.75);
    border-radius: 50%;
    min-width: 5px;
    min-height: 5px;
    margin-top: 3px;
}
.indicator-min {
    background: rgba(140, 140, 140, 0.50);
    border-radius: 50%;
    min-width: 5px;
    min-height: 5px;
    margin-top: 3px;
}
.separator {
    background: rgba(0, 0, 0, 0.15);
    min-width: 1px;
    margin: 10px 4px;
}
.drag-remove { opacity: 0.30; }

.gear-btn {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 2px 6px;
    color: rgba(255, 255, 255, 0.40);
    font-size: 39px;
}
.gear-btn:hover { color: rgba(255, 255, 255, 0.85); }

.settings-bg {
    background: rgba(20, 20, 28, 0.96);
    border-radius: 14px;
    border: 1px solid rgba(127, 119, 221, 0.25);
    padding: 14px 16px 16px;
}
.settings-title { color: #cccccc; font-size: 13px; font-weight: bold; }
.settings-lbl   { color: #999999; font-size: 11px; }
"""


# ── config ─────────────────────────────────────────────────────────────────────

def load_config():
    cfg = {}
    try:
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
    except Exception:
        pass
    cfg.setdefault("icon_size", 40)
    cfg.setdefault("btn_size",  50)
    cfg.setdefault("lock_drag", False)
    cfg.setdefault("pinned", DEFAULT_PINNED)
    return cfg


def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as ex:
        print(f"[dock] save: {ex}")


# ── Hyprland IPC ───────────────────────────────────────────────────────────────

def _hypr_sock1():
    sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
    rt  = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    for base in (rt, "/tmp"):
        p = f"{base}/hypr/{sig}/.socket.sock"
        if os.path.exists(p):
            return p
    return None


def hypr_cmd(cmd):
    path = _hypr_sock1()
    if not path:
        return
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(path)
            s.sendall(cmd.encode())
            s.recv(256)
    except Exception:
        pass


# ── State ──────────────────────────────────────────────────────────────────────

class State:
    def __init__(self):
        self.windows     = {}
        self.active_addr = ""
        self._prev_ws    = {}
        self._lock       = threading.Lock()

    def refresh(self):
        try:
            r = subprocess.run(["hyprctl", "clients", "-j"],
                               capture_output=True, text=True, timeout=1)
            clients = json.loads(r.stdout or "[]")
            with self._lock:
                for c in clients:
                    if not c["workspace"]["name"].startswith("special"):
                        self._prev_ws[c["address"]] = c["workspace"]["id"]
                self.windows = {c["address"]: c for c in clients}
        except Exception:
            pass

    def prev_ws(self, addr):
        with self._lock:
            return self._prev_ws.get(addr, "e+0")

    def refresh_active(self):
        try:
            r = subprocess.run(["hyprctl", "activewindow", "-j"],
                               capture_output=True, text=True, timeout=0.5)
            w = json.loads(r.stdout or "{}")
            with self._lock:
                self.active_addr = w.get("address", "")
        except Exception:
            pass

    def windows_for(self, cls):
        with self._lock:
            all_w = list(self.windows.values())
        normal    = [w for w in all_w if w["class"].lower() == cls
                     and not w["workspace"]["name"].startswith("special")]
        minimized = [w for w in all_w if w["class"].lower() == cls
                     and w["workspace"]["name"].startswith("special")]
        return normal, minimized

    @property
    def active(self):
        with self._lock:
            return self.active_addr


# ── DockButton ─────────────────────────────────────────────────────────────────

class DockButton(Gtk.Box):
    def __init__(self, cls, cmd, icon_name, state, cfg,
                 pinned=True, on_unpin=None, on_pin=None, on_settings=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.cls         = cls
        self.cmd         = cmd
        self._icon_name  = icon_name
        self.state       = state
        self.cfg         = cfg
        self.pinned      = pinned
        self.on_unpin    = on_unpin
        self.on_pin      = on_pin
        self.on_settings = on_settings
        self._pixbuf   = None
        self._drag_y   = None
        self._drag_out = False

        self.ebox = Gtk.EventBox()
        self.ebox.set_visible_window(False)
        self.ebox.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK
        )
        self.ebox.connect("button-press-event",   self._on_press)
        self.ebox.connect("motion-notify-event",  self._on_motion)
        self.ebox.connect("button-release-event", self._on_release)

        if not pinned:
            self.ebox.drag_source_set(
                Gdk.ModifierType.BUTTON1_MASK, [], Gdk.DragAction.COPY)
            self.ebox.drag_source_add_text_targets()
            self.ebox.connect("drag-begin",    self._drag_begin)
            self.ebox.connect("drag-data-get", self._drag_data_get)
            self.ebox.connect("drag-end",      self._drag_end)

        self.cell = Gtk.Box()
        self.cell.get_style_context().add_class("dock-btn")
        btn_size = cfg.get("btn_size", 50)
        self.cell.set_size_request(btn_size, btn_size)

        self.img = Gtk.Image()
        self._reload_icon()
        self.img.set_halign(Gtk.Align.CENTER)
        self.img.set_valign(Gtk.Align.CENTER)
        self.cell.pack_start(self.img, True, True, 0)
        self.ebox.add(self.cell)
        self.pack_start(self.ebox, False, False, 0)

        self.dot_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.dot_row.set_halign(Gtk.Align.CENTER)
        self.pack_start(self.dot_row, False, False, 0)

    def _reload_icon(self):
        icon_size = self.cfg.get("icon_size", 40)
        theme = Gtk.IconTheme.get_default()
        pb = None
        for n in (self._icon_name, self._icon_name.lower(), self._icon_name.capitalize()):
            try:
                pb = theme.load_icon(n, icon_size, Gtk.IconLookupFlags.FORCE_SIZE)
                break
            except Exception:
                pass
        if pb is None:
            try:
                pb = theme.load_icon("application-x-executable", icon_size,
                                     Gtk.IconLookupFlags.FORCE_SIZE)
            except Exception:
                pass
        self._pixbuf = pb
        if pb:
            self.img.set_from_pixbuf(pb)
        else:
            self.img.set_from_icon_name("application-x-executable",
                                        Gtk.IconSize.LARGE_TOOLBAR)

    def resize(self, icon_size, btn_size):
        self.cell.set_size_request(btn_size, btn_size)
        self._reload_icon()

    # ── drag-to-unpin ──────────────────────────────────────────────────────────

    def _on_press(self, _eb, event):
        if event.button == 1:
            self._drag_y   = event.y_root
            self._drag_out = False

    def _on_motion(self, _eb, event):
        if not self.pinned or self.cfg.get("lock_drag", False):
            return
        if self._drag_y is None:
            return
        # dragged upward past one button-height → mark for removal
        becoming = (self._drag_y - event.y_root) > self.cfg.get("btn_size", 50)
        if becoming != self._drag_out:
            self._drag_out = becoming
            ctx = self.cell.get_style_context()
            if becoming:
                ctx.add_class("drag-remove")
            else:
                ctx.remove_class("drag-remove")

    def _drag_begin(self, _widget, ctx):
        if self._pixbuf:
            Gtk.drag_set_icon_pixbuf(ctx, self._pixbuf,
                                     self._pixbuf.get_width() // 2,
                                     self._pixbuf.get_height() // 2)
        self._drag_y   = None
        self._drag_out = False

    def _drag_data_get(self, _widget, _ctx, data, _info, _time):
        data.set_text(self.cls, -1)

    def _drag_end(self, _widget, _ctx):
        self._drag_y   = None
        self._drag_out = False
        self.cell.get_style_context().remove_class("drag-remove")

    def _on_release(self, _eb, event):
        if event.button == 1:
            dragged        = self._drag_out
            self._drag_out = False
            self._drag_y   = None
            self.cell.get_style_context().remove_class("drag-remove")
            if dragged:
                if self.on_unpin:
                    self.on_unpin(self.cls)
                return
            self._click(event)
        elif event.button == 3:
            self._right_click(event)

    # ── click logic ────────────────────────────────────────────────────────────

    def _click(self, event):
        normal, minimized = self.state.windows_for(self.cls)
        active = self.state.active
        all_wins = normal + minimized

        if not all_wins:
            subprocess.Popen(self.cmd.split())
            return

        if minimized:
            w  = minimized[0]
            ws = self.state.prev_ws(w["address"])
            hypr_cmd(f"dispatch movetoworkspacesilent {ws},address:{w['address']}")
            hypr_cmd(f"dispatch focuswindow address:{w['address']}")
            return

        focused = [w for w in normal if w["address"] == active]
        if focused:
            hypr_cmd(f"dispatch movetoworkspacesilent {SPECIAL},"
                     f"address:{focused[0]['address']}")
        else:
            hypr_cmd(f"dispatch focuswindow address:{normal[0]['address']}")

    def _right_click(self, event):
        normal, minimized = self.state.windows_for(self.cls)
        all_wins = normal + minimized
        menu = Gtk.Menu()

        for w in all_wins:
            title  = (w.get("title") or w.get("class", "—"))[:60]
            is_min = w in minimized
            item   = Gtk.MenuItem(label=("↓ " if is_min else "") + title)
            addr   = w["address"]
            def on_activate(_, a=addr, m=is_min):
                if m:
                    ws = self.state.prev_ws(a)
                    hypr_cmd(f"dispatch movetoworkspace {ws},address:{a}")
                hypr_cmd(f"dispatch focuswindow address:{a}")
            item.connect("activate", on_activate)
            menu.append(item)

        if all_wins and self.on_settings:
            menu.append(Gtk.SeparatorMenuItem())
        if self.on_settings:
            cfg_item = Gtk.MenuItem(label="⚙  Dock settings")
            cfg_item.connect("activate", lambda _: self.on_settings())
            menu.append(cfg_item)

        if not menu.get_children():
            return
        menu.show_all()
        menu.popup_at_pointer(event)

    def update(self):
        normal, minimized = self.state.windows_for(self.cls)
        active = self.state.active

        ctx = self.cell.get_style_context()
        if any(w["address"] == active for w in normal):
            ctx.add_class("dock-active")
        else:
            ctx.remove_class("dock-active")

        for ch in self.dot_row.get_children():
            self.dot_row.remove(ch)
        if normal or minimized:
            dot = Gtk.Box()
            dot.get_style_context().add_class(
                "indicator" if normal else "indicator-min")
            self.dot_row.pack_start(dot, False, False, 0)
        self.dot_row.show_all()


# ── SettingsWindow ─────────────────────────────────────────────────────────────

class SettingsWindow(Gtk.Window):
    def __init__(self, dock):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.dock = dock
        self.cfg  = dock.cfg
        self._rebuild_timer = None

        self.set_decorated(False)
        self.set_app_paintable(True)
        vis = self.get_screen().get_rgba_visual()
        if vis:
            self.set_visual(vis)

        # LayerShell: float above the dock at the bottom-centre
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, True)
        bottom_margin = dock._zone() + 16
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.BOTTOM, bottom_margin)

        outer = Gtk.Box()
        bg = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        bg.get_style_context().add_class("settings-bg")
        outer.pack_start(bg, True, True, 0)
        self.add(outer)

        # title + close
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label="Dock")
        lbl.get_style_context().add_class("settings-title")
        lbl.set_halign(Gtk.Align.START)
        row.pack_start(lbl, True, True, 0)
        close = Gtk.Button(label="✕")
        close.get_style_context().add_class("gear-btn")
        close.connect("clicked", lambda _: self.destroy())
        row.pack_end(close, False, False, 0)
        bg.pack_start(row, False, False, 0)

        bg.pack_start(Gtk.Separator(), False, False, 0)

        # lock drag
        lock_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lock_lbl = Gtk.Label(label="Lock drag-to-remove")
        lock_lbl.get_style_context().add_class("settings-lbl")
        lock_lbl.set_halign(Gtk.Align.START)
        lock_row.pack_start(lock_lbl, True, True, 0)
        self.lock_sw = Gtk.Switch()
        self.lock_sw.set_active(self.cfg.get("lock_drag", False))
        self.lock_sw.connect("notify::active", self._on_lock)
        lock_row.pack_end(self.lock_sw, False, False, 0)
        bg.pack_start(lock_row, False, False, 0)

        # icon size
        self._icon_lbl = Gtk.Label()
        self._icon_lbl.get_style_context().add_class("settings-lbl")
        self._icon_lbl.set_halign(Gtk.Align.START)
        bg.pack_start(self._icon_lbl, False, False, 0)
        self.icon_sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 20, 64, 2)
        self.icon_sc.set_value(self.cfg.get("icon_size", 40))
        self.icon_sc.set_draw_value(False)
        self.icon_sc.set_hexpand(True)
        self.icon_sc.connect("value-changed", self._on_icon)
        bg.pack_start(self.icon_sc, False, False, 0)
        self._update_icon_lbl()

        # btn / panel size
        self._btn_lbl = Gtk.Label()
        self._btn_lbl.get_style_context().add_class("settings-lbl")
        self._btn_lbl.set_halign(Gtk.Align.START)
        bg.pack_start(self._btn_lbl, False, False, 0)
        self.btn_sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 36, 80, 2)
        self.btn_sc.set_value(self.cfg.get("btn_size", 50))
        self.btn_sc.set_draw_value(False)
        self.btn_sc.set_hexpand(True)
        self.btn_sc.connect("value-changed", self._on_btn)
        bg.pack_start(self.btn_sc, False, False, 0)
        self._update_btn_lbl()

        self.set_size_request(260, -1)
        self.show_all()
        self.connect("focus-out-event", lambda *_: self.destroy())
        self.connect("key-press-event", self._on_key)

    def _update_icon_lbl(self):
        self._icon_lbl.set_text(f"Icon size: {self.cfg.get('icon_size', 40)}px")

    def _update_btn_lbl(self):
        self._btn_lbl.set_text(f"Panel size: {self.cfg.get('btn_size', 50)}px")

    def _on_key(self, _w, ev):
        if Gdk.keyval_name(ev.keyval) == "Escape":
            self.destroy()
        return False

    def _on_lock(self, sw, _p):
        self.cfg["lock_drag"] = sw.get_active()
        save_config(self.cfg)

    def _on_icon(self, sc):
        self.cfg["icon_size"] = int(sc.get_value())
        self._update_icon_lbl()
        save_config(self.cfg)
        self._schedule_resize()

    def _on_btn(self, sc):
        self.cfg["btn_size"] = int(sc.get_value())
        self._update_btn_lbl()
        save_config(self.cfg)
        self._schedule_resize()

    def _schedule_resize(self):
        if self._rebuild_timer:
            GLib.source_remove(self._rebuild_timer)
        self._rebuild_timer = GLib.timeout_add(150, self._do_resize)

    def _do_resize(self):
        self._rebuild_timer = None
        self.dock._resize_all()
        return False


# ── Dock ───────────────────────────────────────────────────────────────────────

class Dock(Gtk.Window):
    def __init__(self, cfg):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.cfg  = cfg
        self.state = State()
        self._btns = []
        self._settings_win = None

        self.set_decorated(False)
        self.set_app_paintable(True)
        vis = self.get_screen().get_rgba_visual()
        if vis:
            self.set_visual(vis)

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_namespace(self, "dock")
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        for edge in (GtkLayerShell.Edge.BOTTOM,
                     GtkLayerShell.Edge.LEFT,
                     GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(self, edge, True)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.BOTTOM, 8)

        self.outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.outer.set_halign(Gtk.Align.CENTER)
        self.outer.set_valign(Gtk.Align.END)
        self.add(self.outer)

        self.inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.inner.get_style_context().add_class("dock-bg")
        self.outer.pack_start(self.inner, False, False, 0)

        self._pinned_classes = set()
        self._dyn_sep  = None
        self._dyn_box  = None
        self._dyn_btns = {}

        self._build_contents()
        self._apply_zone()

        self.state.refresh()
        self.state.refresh_active()
        GLib.timeout_add(2000, self._poll)
        threading.Thread(target=self._watch, daemon=True).start()

    def _zone(self):
        return self.cfg.get("btn_size", 50) + 30

    def _apply_zone(self):
        zone = self._zone()
        GtkLayerShell.set_exclusive_zone(self, zone)
        self.outer.set_size_request(-1, zone)

    def _build_contents(self):
        self._pinned_classes = set()
        for item in self.cfg.get("pinned", []):
            if item is None:
                sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
                sep.get_style_context().add_class("separator")
                self.inner.pack_start(sep, False, False, 0)
            else:
                cls, cmd, icon = item["cls"], item["cmd"], item["icon"]
                self._pinned_classes.add(cls)
                btn = DockButton(cls, cmd, icon, self.state, self.cfg,
                                 pinned=True, on_unpin=self._unpin,
                                 on_settings=self._open_settings)
                self._btns.append(btn)
                self.inner.pack_start(btn, False, False, 0)

        self._dyn_sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self._dyn_sep.get_style_context().add_class("separator")
        self.inner.pack_start(self._dyn_sep, False, False, 0)

        self._dyn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.inner.pack_start(self._dyn_box, False, False, 0)

        # drop target: drag dynamic icon onto dock → pin it
        self.inner.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.inner.drag_dest_add_text_targets()
        self.inner.connect("drag-data-received", self._on_drop)

    def _clear_contents(self):
        self._btns.clear()
        for btn in self._dyn_btns.values():
            btn.destroy()
        self._dyn_btns = {}
        for ch in self.inner.get_children():
            self.inner.remove(ch)
            ch.destroy()

    def _resize_all(self):
        icon_size = self.cfg.get("icon_size", 40)
        btn_size  = self.cfg.get("btn_size",  50)
        for btn in self._btns + list(self._dyn_btns.values()):
            btn.resize(icon_size, btn_size)
        self._apply_zone()
        self.inner.queue_resize()

    def _rebuild(self):
        self._clear_contents()
        self._build_contents()
        self._apply_zone()
        self.inner.show_all()
        self.state.refresh()
        GLib.idle_add(self._redraw)

    def _on_drop(self, _widget, ctx, _x, _y, data, _info, time):
        cls = data.get_text()
        if cls:
            self._pin(cls, cls, cls)
        Gtk.drag_finish(ctx, bool(cls), False, time)

    def _pin(self, cls, cmd, icon):
        pinned = self.cfg.get("pinned", [])
        if any(p and p["cls"] == cls for p in pinned):
            return
        pinned.append({"cls": cls, "cmd": cmd, "icon": icon})
        self.cfg["pinned"] = pinned
        save_config(self.cfg)
        self._rebuild()

    def _unpin(self, cls):
        pinned = [p for p in self.cfg.get("pinned", [])
                  if p is None or p["cls"] != cls]
        while pinned and pinned[-1] is None:
            pinned.pop()
        self.cfg["pinned"] = pinned
        save_config(self.cfg)
        self._rebuild()

    def _open_settings(self, _btn=None):
        if self._settings_win and self._settings_win.get_visible():
            self._settings_win.destroy()
            self._settings_win = None
            return
        self._settings_win = SettingsWindow(self)

    def _redirect_minimized(self):
        with self.state._lock:
            all_w = list(self.state.windows.values())
        for w in all_w:
            ws = w.get("workspace", {})
            if ws.get("id", 0) < 0 and ws.get("name", "") != SPECIAL:
                hypr_cmd(f"dispatch movetoworkspacesilent {SPECIAL},"
                         f"address:{w['address']}")
        return False

    # ── polling / events ───────────────────────────────────────────────────────

    def _poll(self):
        self.state.refresh()
        self.state.refresh_active()
        self._redraw()
        return True

    def _redraw(self):
        for btn in self._btns:
            btn.update()
        self._redraw_dynamic()
        return False

    def _redraw_dynamic(self):
        with self.state._lock:
            all_w = list(self.state.windows.values())

        seen = {w["class"].lower() for w in all_w
                if w["class"] and w["class"].lower() not in self._pinned_classes}

        for cls in list(self._dyn_btns):
            if cls not in seen:
                self._dyn_btns[cls].destroy()
                del self._dyn_btns[cls]

        for cls in seen:
            if cls not in self._dyn_btns:
                btn = DockButton(cls, cls, cls, self.state, self.cfg,
                                 pinned=False, on_pin=self._pin,
                                 on_settings=self._open_settings)
                self._dyn_btns[cls] = btn
                self._dyn_box.pack_start(btn, False, False, 0)
                btn.show_all()

        for btn in self._dyn_btns.values():
            btn.update()

        if self._dyn_btns:
            self._dyn_sep.show()
        else:
            self._dyn_sep.hide()

    def _watch(self):
        sig  = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
        rt   = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
        path = None
        for base in (rt, "/tmp"):
            p = f"{base}/hypr/{sig}/.socket2.sock"
            if os.path.exists(p):
                path = p
                break
        if not path:
            return
        EVENTS = ("openwindow>>", "closewindow>>", "movewindow>>",
                  "activewindow>>", "activewindowv2>>")
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(path)
            buf = ""
            while True:
                data = s.recv(4096).decode("utf-8", errors="ignore")
                if not data:
                    break
                buf += data
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    if any(line.startswith(e) for e in EVENTS):
                        self.state.refresh()
                        self.state.refresh_active()
                        GLib.idle_add(self._redirect_minimized)
                        GLib.idle_add(self._redraw)
        except Exception as ex:
            print(f"[dock] watch: {ex}")


def main():
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
    dock = Dock(load_config())
    dock.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
