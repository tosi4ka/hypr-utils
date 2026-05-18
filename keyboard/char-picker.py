#!/usr/bin/env python3
import fcntl
import os
import selectors
import struct
import subprocess
import sys
import threading
import time

import evdev
import gi
from evdev import InputDevice
from evdev import ecodes as e
from Xlib import X
from Xlib import display as xdisplay
from Xlib.ext import xtest

gi.require_version("Atspi", "2.0")
from gi.repository import Atspi as _Atspi

VARIANTS = {
    e.KEY_A: ["à", "á", "â", "ã", "ä", "å", "æ", "ā", "ă", "ą"],
    e.KEY_E: ["è", "é", "ê", "ë", "ě", "ę", "ē", "ė", "ə"],
    e.KEY_I: ["ì", "í", "î", "ï", "ī", "į", "ı", "ĭ"],
    e.KEY_O: ["ò", "ó", "ô", "õ", "ö", "ø", "œ", "ō", "ŏ"],
    e.KEY_U: ["ù", "ú", "û", "ü", "ū", "ů", "ű", "ŭ", "ų"],
    e.KEY_Y: ["ý", "ÿ", "ŷ"],
    e.KEY_N: ["ñ", "ń", "ņ", "ň", "ŋ"],
    e.KEY_C: ["ç", "ć", "č", "ĉ", "ċ"],
    e.KEY_S: ["ś", "š", "ŝ", "ş", "ß"],
    e.KEY_Z: ["ź", "ż", "ž"],
    e.KEY_L: ["ł", "ļ", "ľ", "ĺ"],
    e.KEY_R: ["ř", "ŗ"],
    e.KEY_D: ["ð", "đ"],
    e.KEY_T: ["þ", "ţ", "ť"],
    e.KEY_G: ["ğ", "ĝ", "ġ"],
    e.KEY_H: ["ħ", "ĥ"],
    e.KEY_MINUS: ["–", "—", "·", "•"],
    e.KEY_EQUAL: ["≠", "≈", "±", "×", "÷"],
    e.KEY_SLASH: ["÷", "⁄"],
    e.KEY_DOT: ["…", "·", "•"],
}

HOLD_TIME = 0.45
DISPLAY = os.environ.get("DISPLAY", ":0")
XAUTHORITY = os.environ.get("XAUTHORITY", os.path.expanduser("~/.Xauthority"))
ROFI = "/usr/bin/rofi"
XDOTOOL = "/usr/bin/xdotool"
XSET = "/usr/bin/xset"
EVIOCSREP = 0x40084503


def xenv():
    return {**os.environ, "DISPLAY": DISPLAY, "XAUTHORITY": XAUTHORITY}


def x11_repeat(on: bool):
    if _xdpy and _libx:
        try:
            if on:
                _libx.XAutoRepeatOn(_xdpy)
            else:
                _libx.XAutoRepeatOff(_xdpy)
            _libx.XFlush(_xdpy)
            return
        except Exception as ex:
            print(f"[picker] x11_repeat error: {ex}", flush=True)
    subprocess.run(
        [XSET, "r", "on" if on else "off"],
        env=xenv(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def kernel_repeat(kbd, delay, period):
    try:
        fcntl.ioctl(kbd.fd, EVIOCSREP, struct.pack("II", delay, period))
    except Exception as ex:
        print(f"[picker] kernel_repeat error: {ex}", flush=True)


def fake_keyup(kc):
    try:
        dpy = xdisplay.Display(DISPLAY)
        xtest.fake_input(dpy, X.KeyRelease, kc + 8)
        dpy.flush()
        dpy.close()
    except Exception as ex:
        print(f"[picker] fake_keyup: {ex}", flush=True)


def show_rofi(variants):
    cx, cy = get_caret_pos()
    try:
        win_id = (
            subprocess.check_output([XDOTOOL, "getactivewindow"], env=xenv())
            .decode()
            .strip()
        )
    except Exception:
        win_id = None
    try:
        r = subprocess.run(
            [
                "/home/tosi4ka/.local/bin/char-picker-popup.py",
                " ".join(variants),
                str(cx),
                str(cy),
            ],
            capture_output=True,
            timeout=30,
            env=xenv(),
        )
        if r.returncode == 0:
            s = r.stdout.decode("utf-8").strip()
            return s if s in variants else None, win_id
    except Exception as ex:
        print(f"[picker] popup error: {ex}", flush=True)
    return None, win_id


def _find_focused_atspi(obj, depth=0):
    if depth > 6:
        return None
    try:
        if obj.get_state_set().contains(_Atspi.StateType.FOCUSED):
            return obj
        for i in range(min(obj.get_child_count(), 30)):
            child = obj.get_child_at_index(i)
            if child:
                result = _find_focused_atspi(child, depth + 1)
                if result:
                    return result
    except Exception:
        pass
    return None


def get_caret_pos():
    result = []

    def _worker():
        try:
            _Atspi.init()
            desktop = _Atspi.get_desktop(0)
            for i in range(desktop.get_child_count()):
                app = desktop.get_child_at_index(i)
                if not app:
                    continue
                focused = _find_focused_atspi(app)
                if focused:
                    try:
                        text = focused.get_text_iface()
                        offset = text.get_caret_offset()
                        rect = text.get_character_extents(
                            offset, _Atspi.CoordType.SCREEN
                        )
                        if rect.height > 0:
                            result.append((rect.x, rect.y + rect.height))
                    except Exception:
                        pass
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=0.4)
    return result[0] if result else (-1, -1)


import ctypes as _ct


class _XkbState(_ct.Structure):
    _fields_ = [
        ("group", _ct.c_ubyte),
        ("locked_group", _ct.c_ubyte),
        ("base_group", _ct.c_ushort),
        ("latched_group", _ct.c_ushort),
        ("mods", _ct.c_ubyte),
        ("base_mods", _ct.c_ubyte),
        ("latched_mods", _ct.c_ubyte),
        ("locked_mods", _ct.c_ubyte),
        ("compat_state", _ct.c_ubyte),
        ("grab_mods", _ct.c_ubyte),
        ("compat_grab_mods", _ct.c_ubyte),
        ("lookup_mods", _ct.c_ubyte),
        ("compat_lookup_mods", _ct.c_ubyte),
        ("ptr_buttons", _ct.c_ushort),
    ]


try:
    _libx = _ct.cdll.LoadLibrary("libX11.so.6")
    _libx.XOpenDisplay.restype = _ct.c_void_p
    _libx.XOpenDisplay.argtypes = [_ct.c_char_p]
    _libx.XkbGetState.argtypes = [_ct.c_void_p, _ct.c_uint, _ct.POINTER(_XkbState)]
    _libx.XkbGetState.restype = _ct.c_int
    _libx.XCloseDisplay.argtypes = [_ct.c_void_p]
    _libx.XAutoRepeatOn.argtypes = [_ct.c_void_p]
    _libx.XAutoRepeatOn.restype = _ct.c_int
    _libx.XAutoRepeatOff.argtypes = [_ct.c_void_p]
    _libx.XAutoRepeatOff.restype = _ct.c_int
    _libx.XFlush.argtypes = [_ct.c_void_p]
    _libx.XFlush.restype = _ct.c_int
    _xdpy = _libx.XOpenDisplay(DISPLAY.encode())
except Exception:
    _libx = None
    _xdpy = None


def is_latin_layout():
    try:
        s = _XkbState()
        _libx.XkbGetState(_xdpy, 0x0100, _ct.byref(s))
        return s.group == 0
    except Exception:
        return True


def find_keyboards():
    need = {e.KEY_A, e.KEY_Z, e.KEY_SPACE, e.KEY_ENTER, e.KEY_LEFTCTRL}
    found = []
    for path in evdev.list_devices():
        try:
            dev = InputDevice(path)
            caps = dev.capabilities()
            if e.EV_KEY not in caps:
                continue
            if not need.issubset(set(caps[e.EV_KEY])):
                continue
            if any(x in dev.name.lower() for x in ("virtual", "uinput", "picker")):
                continue
            found.append(dev)
        except Exception:
            continue
    return found


def run(keyboards):
    sel = selectors.DefaultSelector()
    for kbd in keyboards:
        sel.register(kbd, selectors.EVENT_READ)
        print(f"[picker] monitoring: {kbd.name}", flush=True)

    held = {}  # fd -> (key_code, press_time)
    repeat_held = 0

    try:
        while True:
            ready = sel.select(timeout=0.01)
            now = time.time()

            for fd, (kc, pt) in list(held.items()):
                if (now - pt) >= HOLD_TIME:
                    del held[fd]
                    repeat_held -= 1

                    kbd = next(k for k in keyboards if k.fd == fd)

                    try:
                        kbd.grab()
                    except Exception:
                        pass

                    fake_keyup(kc)

                    deadline = time.time() + 5.0
                    while time.time() < deadline:
                        for key_inner, _ in sel.select(timeout=0.02):
                            dev = key_inner.fileobj
                            try:
                                for ev in dev.read():
                                    if (
                                        dev.fd == fd
                                        and ev.type == e.EV_KEY
                                        and ev.code == kc
                                        and ev.value == 0
                                    ):
                                        deadline = 0
                            except Exception:
                                pass

                    try:
                        kbd.ungrab()
                    except Exception:
                        pass

                    fake_keyup(kc)

                    kernel_repeat(kbd, 500, 20)
                    if repeat_held <= 0:
                        repeat_held = 0
                        x11_repeat(True)
                    time.sleep(0.08)

                    chosen, win_id = show_rofi(VARIANTS.get(kc, []))
                    print(f"[picker] chosen: {chosen}", flush=True)
                    if chosen:
                        time.sleep(0.2)
                        subprocess.run(
                            [XDOTOOL, "key", "BackSpace"],
                            env=xenv(),
                            stderr=subprocess.DEVNULL,
                        )
                        time.sleep(0.05)
                        subprocess.run(
                            [XDOTOOL, "key", "--clearmodifiers", f"U{ord(chosen):04X}"],
                            env=xenv(),
                            stderr=subprocess.DEVNULL,
                        )

            if not ready:
                continue

            for key, _ in ready:
                kbd = key.fileobj
                try:
                    events = list(kbd.read())
                except Exception:
                    continue

                for ev in events:
                    if ev.type != e.EV_KEY:
                        continue
                    fd = kbd.fd
                    if (
                        ev.value == 1
                        and ev.code in VARIANTS
                        and fd not in held
                        and is_latin_layout()
                    ):
                        held[fd] = (ev.code, time.time())
                        repeat_held += 1
                        if repeat_held == 1:
                            x11_repeat(False)
                        kernel_repeat(kbd, 10000, 10000)
                        fake_keyup(ev.code)
                    elif ev.value == 0 and fd in held and held[fd][0] == ev.code:
                        del held[fd]
                        repeat_held -= 1
                        try:
                            kbd.ungrab()
                        except Exception:
                            pass
                        kernel_repeat(kbd, 500, 20)
                        if repeat_held <= 0:
                            repeat_held = 0
                            x11_repeat(True)
    except Exception as ex:
        print(f"[picker] loop error: {ex}", flush=True)
        x11_repeat(True)
        for kbd in keyboards:
            kernel_repeat(kbd, 500, 20)
            try:
                kbd.ungrab()
            except Exception:
                pass


def main():
    keyboards = find_keyboards()
    if not keyboards:
        print("[picker] Клавиатуры не найдены.")
        sys.exit(1)
    try:
        run(keyboards)
    except PermissionError:
        print("[picker] Нет прав. sudo usermod -aG input $USER → ребут")
        sys.exit(1)
    except KeyboardInterrupt:
        x11_repeat(True)
        for kbd in keyboards:
            kernel_repeat(kbd, 500, 20)
            try:
                kbd.ungrab()
            except Exception:
                pass
        print("[picker] Остановлен.")


if __name__ == "__main__":
    main()
