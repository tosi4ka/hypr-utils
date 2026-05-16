#!/usr/bin/env python3
"""Standalone StatusNotifierWatcher daemon."""

import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

BUS_NAME = "org.kde.StatusNotifierWatcher"
IFACE = "org.kde.StatusNotifierWatcher"
HOST_IFACE = "org.kde.StatusNotifierHost"


class Watcher(dbus.service.Object):
    def __init__(self, bus):
        self._items = []
        self._hosts = []
        bus_name = dbus.service.BusName(BUS_NAME, bus=bus)
        super().__init__(bus_name, "/StatusNotifierWatcher")
        self._bus = bus

    @dbus.service.method(IFACE, in_signature="s", sender_keyword="sender")
    def RegisterStatusNotifierItem(self, service_or_path, sender=None):
        if service_or_path.startswith("/"):
            item = f"{sender}{service_or_path}"
        else:
            # bus name or service name without path → use default SNI object path
            item = f"{sender}/StatusNotifierItem"
        if item not in self._items:
            self._items.append(item)
            self.StatusNotifierItemRegistered(item)

    @dbus.service.method(IFACE, in_signature="s", sender_keyword="sender")
    def RegisterStatusNotifierHost(self, service, sender=None):
        if service not in self._hosts:
            self._hosts.append(service)
            self.StatusNotifierHostRegistered()

    @dbus.service.signal(IFACE, signature="s")
    def StatusNotifierItemRegistered(self, service):
        pass

    @dbus.service.signal(IFACE, signature="s")
    def StatusNotifierItemUnregistered(self, service):
        pass

    @dbus.service.signal(IFACE)
    def StatusNotifierHostRegistered(self):
        pass

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature="ss", out_signature="v")
    def Get(self, iface, prop):
        if prop == "RegisteredStatusNotifierItems":
            return dbus.Array(self._items, signature="s")
        if prop == "IsStatusNotifierHostRegistered":
            return dbus.Boolean(len(self._hosts) > 0)
        if prop == "ProtocolVersion":
            return dbus.Int32(0)
        raise dbus.DBusException(f"Unknown property: {prop}")

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, iface):
        return {
            "RegisteredStatusNotifierItems": dbus.Array(self._items, signature="s"),
            "IsStatusNotifierHostRegistered": dbus.Boolean(len(self._hosts) > 0),
            "ProtocolVersion": dbus.Int32(0),
        }

    def watch_name(self, name):
        """Remove items when their owner disconnects."""
        self._bus.watch_name_owner(name, self._on_name_changed)

    def _on_name_changed(self, new_owner):
        if not new_owner:
            self._items = [i for i in self._items if not i.startswith(new_owner)]


if __name__ == "__main__":
    bus = dbus.SessionBus()
    Watcher(bus)
    print("[sni-watcher] started")
    GLib.MainLoop().run()
