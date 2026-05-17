#!/usr/bin/env python3
"""Wallpaper manager — menu, thumbnail picker, slideshow control."""

import json
import os
import subprocess

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Pango

IMG_DIR = os.path.expanduser("~/SomeFiles/img")
EXTS = {".jpg", ".jpeg", ".png", ".webp"}
THUMB_W, THUMB_H = 220, 140
PID_FILE = "/tmp/wallpaper-slideshow.pid"
SLIDESHOW_SCRIPT = os.path.expanduser("~/.local/bin/wallpaper-slideshow.sh")

CSS = b"""
window { background: rgba(20, 20, 28, 0.97); }

.section-title {
    color: rgba(127, 119, 221, 0.8);
    font-size: 11px;
    letter-spacing: 2px;
}
.menu-btn {
    background: rgba(30, 30, 42, 0.9);
    border-radius: 12px;
    padding: 12px 20px;
    border: 1px solid rgba(127, 119, 221, 0.12);
    color: #ccc;
    font-size: 13px;
}
.menu-btn:hover {
    background: rgba(127, 119, 221, 0.2);
    border-color: rgba(127, 119, 221, 0.55);
    color: #fff;
}
.stop-btn {
    background: rgba(30, 30, 42, 0.9);
    border-radius: 12px;
    padding: 12px 20px;
    border: 1px solid rgba(240, 149, 149, 0.12);
    color: #999;
    font-size: 13px;
}
.stop-btn:hover {
    background: rgba(240, 149, 149, 0.15);
    border-color: rgba(240, 149, 149, 0.5);
    color: #fff;
}
.interval-btn {
    background: rgba(30, 30, 42, 0.9);
    border-radius: 10px;
    padding: 10px 0;
    border: 1px solid rgba(127, 119, 221, 0.12);
    color: #ccc;
    font-size: 13px;
}
.interval-btn:hover {
    background: rgba(127, 119, 221, 0.2);
    border-color: rgba(127, 119, 221, 0.55);
    color: #fff;
}
.thumb-btn {
    background: rgba(30, 30, 42, 0.9);
    border-radius: 10px;
    padding: 6px;
    border: 1px solid rgba(127, 119, 221, 0.08);
}
.thumb-btn:hover {
    background: rgba(127, 119, 221, 0.2);
    border-color: rgba(127, 119, 221, 0.6);
}
.thumb-label {
    color: #999;
    font-size: 11px;
}
"""


def setup_css():
    p = Gtk.CssProvider()
    p.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def esc_quit(_win, event):
    if event.keyval == Gdk.KEY_Escape:
        Gtk.main_quit()


def get_images():
    try:
        return sorted(
            f for f in os.listdir(IMG_DIR) if os.path.splitext(f)[1].lower() in EXTS
        )
    except OSError:
        return []


def apply_wallpaper(full_path):
    try:
        out = subprocess.check_output(["hyprctl", "monitors", "-j"], text=True)
        monitors = [m["name"] for m in json.loads(out)]
    except Exception:
        monitors = []

    conf = ["splash = false", f"preload = {full_path}"]
    for mon in monitors:
        conf.append(f"wallpaper = {mon},{full_path}")

    with open(os.path.expanduser("~/.config/hypr/hyprpaper.conf"), "w") as f:
        f.write("\n".join(conf) + "\n")

    for mon in monitors:
        subprocess.run(["hyprctl", "hyprpaper", "preload", full_path], capture_output=True)
        subprocess.run(
            ["hyprctl", "hyprpaper", "wallpaper", f"{mon},{full_path}"], capture_output=True
        )

    symlink = os.path.expanduser("~/.config/hypr/wallpaper")
    try:
        if os.path.islink(symlink) or os.path.exists(symlink):
            os.remove(symlink)
        os.symlink(full_path, symlink)
    except OSError:
        pass

    subprocess.run(
        ["notify-send", "🖼 Wallpaper", os.path.basename(full_path), "--expire-time=2000"]
    )


def stop_slideshow():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 9)
        except Exception:
            pass
        try:
            os.remove(PID_FILE)
        except OSError:
            pass


class MenuWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Wallpaper")
        self.set_default_size(300, -1)
        self.set_resizable(False)
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", esc_quit)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(18)
        box.set_margin_end(18)
        box.set_margin_top(18)
        box.set_margin_bottom(18)
        self.add(box)

        title = Gtk.Label(label="ОБОИ")
        title.get_style_context().add_class("section-title")
        title.set_halign(Gtk.Align.START)
        box.pack_start(title, False, False, 4)

        for text, handler, style in [
            ("🖼  Установить обои", self._on_set, "menu-btn"),
            ("🔄  Слайдшоу", self._on_slideshow, "menu-btn"),
            ("⏹  Остановить слайдшоу", self._on_stop, "stop-btn"),
        ]:
            btn = Gtk.Button(label=text)
            btn.get_style_context().add_class(style)
            btn.connect("clicked", handler)
            box.pack_start(btn, False, False, 0)

        self.show_all()

    def _on_set(self, _btn):
        self.hide()
        PickerWindow()

    def _on_slideshow(self, _btn):
        self.hide()
        IntervalWindow()

    def _on_stop(self, _btn):
        stop_slideshow()
        subprocess.run(["notify-send", "⏹ Слайдшоу", "Остановлено", "--expire-time=2000"])
        Gtk.main_quit()


class IntervalWindow(Gtk.Window):
    INTERVALS = [("5 мин", 5), ("10 мин", 10), ("15 мин", 15), ("30 мин", 30), ("60 мин", 60)]

    def __init__(self):
        super().__init__(title="Слайдшоу")
        self.set_default_size(280, -1)
        self.set_resizable(False)
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", esc_quit)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(18)
        box.set_margin_end(18)
        box.set_margin_top(18)
        box.set_margin_bottom(18)
        self.add(box)

        title = Gtk.Label(label="МЕНЯТЬ КАЖДЫЕ")
        title.get_style_context().add_class("section-title")
        title.set_halign(Gtk.Align.START)
        box.pack_start(title, False, False, 4)

        grid = Gtk.Grid()
        grid.set_column_spacing(8)
        grid.set_row_spacing(8)
        grid.set_column_homogeneous(True)
        box.pack_start(grid, False, False, 0)

        for i, (text, mins) in enumerate(self.INTERVALS):
            btn = Gtk.Button(label=text)
            btn.get_style_context().add_class("interval-btn")
            btn.connect("clicked", self._on_select, mins)
            grid.attach(btn, i % 3, i // 3, 1, 1)

        self.show_all()

    def _on_select(self, _btn, mins):
        stop_slideshow()
        proc = subprocess.Popen([SLIDESHOW_SCRIPT, str(mins)])
        with open(PID_FILE, "w") as f:
            f.write(str(proc.pid))
        subprocess.run(
            ["notify-send", "🔄 Слайдшоу", f"Каждые {mins} мин", "--expire-time=2000"]
        )
        Gtk.main_quit()


class PickerWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Выбор обоев")
        self.set_default_size(960, 600)
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", esc_quit)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.add(scrolled)

        self._flow = Gtk.FlowBox()
        self._flow.set_max_children_per_line(30)
        self._flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self._flow.set_column_spacing(10)
        self._flow.set_row_spacing(10)
        self._flow.set_margin_start(14)
        self._flow.set_margin_end(14)
        self._flow.set_margin_top(14)
        self._flow.set_margin_bottom(14)
        scrolled.add(self._flow)

        self._images = get_images()
        self._load_idx = 0
        GLib.idle_add(self._load_next)

        self.show_all()

    def _load_next(self):
        if self._load_idx >= len(self._images):
            return False

        fname = self._images[self._load_idx]
        self._load_idx += 1
        fpath = os.path.join(IMG_DIR, fname)

        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(fpath, THUMB_W, THUMB_H, True)
        except Exception:
            return True

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        img = Gtk.Image.new_from_pixbuf(pb)
        img.set_size_request(THUMB_W, THUMB_H)
        lbl = Gtk.Label(label=fname)
        lbl.set_ellipsize(Pango.EllipsizeMode.END)
        lbl.set_max_width_chars(24)
        lbl.get_style_context().add_class("thumb-label")
        outer.pack_start(img, False, False, 0)
        outer.pack_start(lbl, False, False, 0)

        btn = Gtk.Button()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.get_style_context().add_class("thumb-btn")
        btn.add(outer)
        btn.connect("clicked", self._on_select, fpath)

        self._flow.add(btn)
        btn.show_all()
        return True

    def _on_select(self, _btn, fpath):
        self.hide()
        while Gtk.events_pending():
            Gtk.main_iteration()
        apply_wallpaper(fpath)
        Gtk.main_quit()


if __name__ == "__main__":
    setup_css()
    MenuWindow()
    Gtk.main()
