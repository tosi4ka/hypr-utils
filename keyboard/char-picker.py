#!/usr/bin/env python3
import json
import os
import re
import selectors
import signal
import socket
import subprocess
import sys
import threading
import time

import evdev
from evdev import InputDevice
from evdev import ecodes as e

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
POPUP = os.path.expanduser("~/.local/bin/char-picker-popup.py")

_original_repeat_delay = None
_is_latin = True  # updated by _watch_layout() thread


def _hypr_socket():
    sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
    runtime = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    for base in (runtime, "/tmp"):
        path = f"{base}/hypr/{sig}/.socket.sock"
        if os.path.exists(path):
            return path
    return None


def _hypr_cmd(cmd):
    path = _hypr_socket()
    if not path:
        return
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(path)
            s.sendall(cmd.encode())
            s.recv(256)
    except Exception:
        pass


def _get_original_repeat_delay():
    global _original_repeat_delay
    if _original_repeat_delay is None:
        # Read from config file — immune to our own runtime changes
        try:
            cfg = os.path.expanduser("~/.config/hypr/hyprland.conf")
            with open(cfg) as f:
                for line in f:
                    m = re.search(r'\brepeat_delay\s*=\s*(\d+)', line)
                    if m:
                        _original_repeat_delay = int(m.group(1))
                        return _original_repeat_delay
        except Exception:
            pass
        # Fallback: hyprctl with sanity check (>= 5000 means our script left it broken)
        try:
            r = subprocess.run(
                ["hyprctl", "getoption", "input:repeat_delay", "-j"],
                capture_output=True, text=True, timeout=1,
            )
            val = json.loads(r.stdout).get("int", 600)
            _original_repeat_delay = val if val < 5000 else 600
        except Exception:
            _original_repeat_delay = 600
    return _original_repeat_delay


def disable_repeat():
    _hypr_cmd("keyword input:repeat_delay 100000")


def restore_repeat():
    delay = _get_original_repeat_delay()
    _hypr_cmd(f"keyword input:repeat_delay {delay}")


def is_latin_layout():
    try:
        r = subprocess.run(
            ["hyprctl", "devices", "-j"],
            capture_output=True, text=True, timeout=0.5,
        )
        devices = json.loads(r.stdout)
        kbs = [k for k in devices.get("keyboards", [])
               if "virtual" not in k["name"]]
        if kbs:
            return "Russian" not in kbs[-1].get("active_keymap", "")
        return True
    except Exception:
        return True


def _watch_layout():
    """Background thread: update _is_latin from Hyprland activelayout events."""
    global _is_latin
    sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
    runtime = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    path = None
    for base in (runtime, "/tmp"):
        p = f"{base}/hypr/{sig}/.socket2.sock"
        if os.path.exists(p):
            path = p
            break
    if not path:
        return
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
                if line.startswith("activelayout>>"):
                    keymap = line.split(">>", 1)[1].split(",", 1)[-1]
                    _is_latin = "Russian" not in keymap
    except Exception:
        pass


def hypr_cursorpos():
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
                return int(pos["x"]), int(pos["y"])
            except Exception:
                pass
    return -1, -1


_popup_proc = None


def _get_popup_proc():
    global _popup_proc
    if _popup_proc is None or _popup_proc.poll() is not None:
        _popup_proc = subprocess.Popen(
            [sys.executable, POPUP, "--daemon"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        print("[picker] popup daemon started", flush=True)
    return _popup_proc


def show_popup(variants):
    cx, cy = hypr_cursorpos()
    try:
        proc = _get_popup_proc()
        cmd = " ".join(variants) + f" {cx} {cy}\n"
        proc.stdin.write(cmd.encode())
        proc.stdin.flush()
        line = proc.stdout.readline().decode().strip()
        return line if line in variants else None
    except Exception as ex:
        print(f"[picker] popup error: {ex}", flush=True)
        global _popup_proc
        _popup_proc = None
    return None


def type_char(chosen, n_backspace=1):
    time.sleep(0.15)
    for _ in range(n_backspace):
        subprocess.run(["wtype", "-k", "BackSpace"], stderr=subprocess.DEVNULL)
        time.sleep(0.02)
    subprocess.run(["wtype", chosen], stderr=subprocess.DEVNULL)


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
    global _is_latin
    _get_original_repeat_delay()  # cache before any disable_repeat() calls
    restore_repeat()              # fix any leftover state from a previous crashed run

    _is_latin = is_latin_layout()  # initial layout check (once at startup)
    threading.Thread(target=_watch_layout, daemon=True).start()
    _get_popup_proc()  # pre-warm popup daemon (amortize GTK import cost)

    # hold_time must be shorter than repeat_delay so the popup appears before
    # Hyprland fires the first key repeat (setting repeat_delay to 100000 does
    # not cancel an already-queued repeat timer in Hyprland)
    repeat_delay_s = _get_original_repeat_delay() / 1000.0
    hold_time = max(0.25, min(HOLD_TIME, repeat_delay_s * 0.80))
    print(f"[picker] hold_time={hold_time:.3f}s repeat_delay={repeat_delay_s:.3f}s", flush=True)

    sel = selectors.DefaultSelector()
    for kbd in keyboards:
        sel.register(kbd, selectors.EVENT_READ)
        print(f"[picker] monitoring: {kbd.name}", flush=True)

    # fd -> (key_code, press_time)
    held = {}

    try:
        while True:
            ready = sel.select(timeout=0.01 if held else None)
            now = time.time()

            for fd, entry in list(held.items()):
                kc, pt, extra = entry
                if (now - pt) < hold_time:
                    continue

                del held[fd]

                chosen = show_popup(VARIANTS.get(kc, []))
                print(f"[picker] chosen: {chosen} (backspaces: {1 + extra})", flush=True)

                restore_repeat()

                if chosen:
                    type_char(chosen, 1 + extra)

            if not ready:
                continue

            for key, _ in ready:
                kbd = key.fileobj
                try:
                    events = list(kbd.read())
                except Exception:
                    sel.unregister(kbd)
                    try:
                        kbd.close()
                    except Exception:
                        pass
                    print(f"[picker] device removed: {getattr(kbd, 'name', kbd)}", flush=True)
                    continue

                for ev in events:
                    if ev.type != e.EV_KEY:
                        continue
                    fd = kbd.fd
                    if (ev.value == 1 and ev.code in VARIANTS
                            and fd not in held and _is_latin):
                        held[fd] = [ev.code, time.time(), 0]
                        disable_repeat()  # stop Hyprland repeat before it fires
                    elif (ev.value == 1 and fd in held
                            and held[fd][0] == ev.code):
                        # BT firmware repeat: extra value=1 for already-held key
                        held[fd][2] += 1
                    elif ev.value == 0 and fd in held and held[fd][0] == ev.code:
                        # released before hold_time — normal keypress, restore repeat
                        del held[fd]
                        restore_repeat()
                    elif ev.value == 1 and ev.code not in VARIANTS and fd in held:
                        # non-variant key pressed while waiting — cancel hold
                        del held[fd]
                        restore_repeat()

    except Exception as ex:
        print(f"[picker] loop error: {ex}", flush=True)
        restore_repeat()


def main():
    signal.signal(signal.SIGTERM, lambda *_: (restore_repeat(), sys.exit(0)))
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
        restore_repeat()
        print("[picker] Остановлен.")


if __name__ == "__main__":
    main()
