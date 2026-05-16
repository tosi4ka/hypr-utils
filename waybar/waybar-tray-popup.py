#!/usr/bin/env python3
"""Tray popup — appears as a pill inline with the waybar bar."""

import dbus
import dbus.mainloop.glib
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, GtkLayerShell

WATCHER_BUS = "org.kde.StatusNotifierWatcher"
WATCHER_OBJ = "/StatusNotifierWatcher"
ITEM_IFACE = "org.kde.StatusNotifierItem"
ICON_SIZE = 22

# Below the bar, mirrored gap from right edge matching the Arch button's gap from left
# Arch button: modules-left padding (4px) + margin-left (4px) = 8px from left edge
MARGIN_TOP = 4    # small gap below the bar
MARGIN_RIGHT = 8  # mirror of arch button's 8px gap from screen edge

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)


def load_icon(session, bus_name, obj_path):
    try:
        obj = session.get_object(bus_name, obj_path)
        props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
        try:
            path = str(props.Get(ITEM_IFACE, "IconThemePath"))
            if path:
                Gtk.IconTheme.get_default().append_search_path(path)
        except Exception:
            pass
        for prop in ("IconName", "AttentionIconName"):
            try:
                name = str(props.Get(ITEM_IFACE, prop))
                if name and Gtk.IconTheme.get_default().has_icon(name):
                    return Gtk.IconTheme.get_default().load_icon(name, ICON_SIZE, 0)
            except Exception:
                pass
        try:
            pixmaps = props.Get(ITEM_IFACE, "IconPixmap")
            if pixmaps:
                best = min(pixmaps, key=lambda p: abs(int(p[0]) - ICON_SIZE))
                w, h = int(best[0]), int(best[1])
                raw = bytes(best[2])
                rgba = bytearray(len(raw))
                for i in range(0, len(raw), 4):
                    rgba[i], rgba[i + 1], rgba[i + 2], rgba[i + 3] = (
                        raw[i + 1], raw[i + 2], raw[i + 3], raw[i],
                    )
                gb = GLib.Bytes.new(bytes(rgba))
                pb = GdkPixbuf.Pixbuf.new_from_bytes(
                    gb, GdkPixbuf.Colorspace.RGB, True, 8, w, h, w * 4
                )
                if w != ICON_SIZE:
                    pb = pb.scale_simple(ICON_SIZE, ICON_SIZE, GdkPixbuf.InterpType.BILINEAR)
                return pb
        except Exception:
            pass
    except Exception as e:
        print(f"[tray] icon error {bus_name}: {e}")
    return None


def get_tooltip(session, bus_name, obj_path):
    try:
        obj = session.get_object(bus_name, obj_path)
        props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
        tt = props.Get(ITEM_IFACE, "ToolTip")
        title = str(tt[2]) if len(tt) > 2 else ""
        desc = str(tt[3]) if len(tt) > 3 else ""
        return (title + "\n" + desc).strip()
    except Exception:
        pass
    try:
        obj = session.get_object(bus_name, obj_path)
        props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
        return str(props.Get(ITEM_IFACE, "Id"))
    except Exception:
        return ""


class TrayPopup(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.set_app_paintable(True)

        vis = self.get_screen().get_rgba_visual()
        if vis:
            self.set_visual(vis)

        GtkLayerShell.init_for_window(self)
        # OVERLAY so it renders above waybar (which is TOP layer)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)

        # Anchor top + right only — window auto-sizes to content
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, MARGIN_TOP)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, MARGIN_RIGHT)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        box.get_style_context().add_class("tray-popup")
        self.add(box)

        session = dbus.SessionBus()
        items = self._get_items(session)

        if not items:
            lbl = Gtk.Label(label="—")
            lbl.get_style_context().add_class("no-items")
            box.pack_start(lbl, False, False, 10)
        else:
            for bus_name, obj_path in items:
                pb = load_icon(session, bus_name, obj_path)
                if pb is None:
                    continue
                tip = get_tooltip(session, bus_name, obj_path)
                btn = Gtk.Button()
                btn.get_style_context().add_class("tray-btn")
                btn.set_relief(Gtk.ReliefStyle.NONE)
                if tip:
                    btn.set_tooltip_text(tip)
                btn.add(Gtk.Image.new_from_pixbuf(pb))
                btn.connect("clicked", self._activate, session, bus_name, obj_path)
                btn.connect("button-press-event", self._btn_press, session, bus_name, obj_path)
                box.pack_start(btn, False, False, 0)

        self._apply_css()
        self.show_all()

    def _get_items(self, session):
        try:
            w = session.get_object(WATCHER_BUS, WATCHER_OBJ)
            items = w.Get(
                WATCHER_BUS,
                "RegisteredStatusNotifierItems",
                dbus_interface="org.freedesktop.DBus.Properties",
            )
            result = []
            for s in items:
                s = str(s)
                if "/" in s:
                    i = s.index("/")
                    result.append((s[:i], s[i:]))
                else:
                    result.append((s, "/StatusNotifierItem"))
            return result
        except Exception as e:
            print(f"[tray] watcher error: {e}")
            return []

    def _activate(self, _btn, session, bus_name, obj_path):
        try:
            dbus.Interface(session.get_object(bus_name, obj_path), ITEM_IFACE).Activate(0, 0)
        except Exception as e:
            print(f"[tray] activate error: {e}")
        self._quit()

    def _btn_press(self, _btn, event, session, bus_name, obj_path):
        if event.button == 3:
            try:
                dbus.Interface(
                    session.get_object(bus_name, obj_path), ITEM_IFACE
                ).ContextMenu(int(event.x_root), int(event.y_root))
            except Exception as e:
                print(f"[tray] context menu error: {e}")
            self._quit()
            return True
        return False

    def _apply_css(self):
        css = b"""
        window { background: transparent; }
        .tray-popup {
            background: rgba(20, 20, 28, 0.92);
            border-radius: 20px;
            padding: 4px 8px;
        }
        .tray-btn {
            background: transparent;
            border: none;
            border-radius: 12px;
            padding: 4px 6px;
            min-height: 0;
            min-width: 0;
        }
        .tray-btn:hover { background: rgba(127, 119, 221, 0.15); }
        .no-items { color: #555; font-size: 13px; }
        """
        p = Gtk.CssProvider()
        p.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _quit(self):
        Gtk.main_quit()


if __name__ == "__main__":
    TrayPopup()
    Gtk.main()
