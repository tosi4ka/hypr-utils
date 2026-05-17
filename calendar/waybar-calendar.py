#!/usr/bin/env python3
import calendar
import datetime
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

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, GLib, Gtk, GtkLayerShell

CREDS_DIR = os.path.expanduser("~/.config/waybar-calendar")
CREDS_FILE = os.path.join(CREDS_DIR, "credentials.json")
TOKEN_FILE = os.path.join(CREDS_DIR, "token.json")
SCOPES = ["https://www.googleapis.com/auth/calendar"]
USER_FILE = os.path.join(CREDS_DIR, "user.txt")
URL_FILE = "/tmp/waybar-calendar-oauth-url"

BG = "rgba(20, 20, 28, 0.97)"
ACCENT = "#7f77dd"
TEXT = "#cccccc"
SUBTEXT = "#666666"
TODAY_BG = "rgba(127, 119, 221, 0.3)"
EVENT_DOT = "#7f77dd"

CSS = f"""
* {{
    font-family: "JetBrainsMono Nerd Font", monospace;
}}
window {{
    background: transparent;
}}
eventbox {{
    background: transparent;
}}
.popup {{
    background: {BG};
    border-radius: 16px;
    border: 1px solid rgba(127, 119, 221, 0.25);
    padding: 16px;
    min-width: 320px;
}}
.header {{
    color: {TEXT};
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 10px;
}}
.nav-btn {{
    background: transparent;
    border: none;
    color: {TEXT};
    font-size: 16px;
    padding: 2px 10px;
    border-radius: 8px;
}}
.nav-btn:hover {{
    background: rgba(127, 119, 221, 0.15);
}}
.weekday {{
    color: {SUBTEXT};
    font-size: 11px;
    font-weight: 600;
    min-width: 38px;
    margin: 1px;
}}
.day-btn {{
    background: transparent;
    border: none;
    color: {TEXT};
    font-size: 13px;
    min-width: 38px;
    min-height: 32px;
    border-radius: 8px;
    margin: 1px;
}}
.day-btn:hover {{
    background: rgba(255,255,255,0.06);
}}
.day-today {{
    background: {TODAY_BG};
    color: #ffffff;
    font-weight: 700;
    border: 1px solid rgba(127, 119, 221, 0.5);
}}
.day-other {{
    color: {SUBTEXT};
}}
.day-has-event {{
    font-weight: 600;
}}
.separator {{
    background: rgba(255,255,255,0.08);
    min-height: 1px;
    margin: 10px 0;
}}
.event-time {{
    color: {ACCENT};
    font-size: 11px;
    min-width: 48px;
}}
.event-title {{
    color: {TEXT};
    font-size: 12px;
}}
.event-row:hover {{
    background: rgba(127, 119, 221, 0.08);
    border-radius: 6px;
}}
.no-events {{
    color: {SUBTEXT};
    font-size: 12px;
    margin: 6px 0;
}}
.section-label {{
    color: {SUBTEXT};
    font-size: 10px;
    font-weight: 600;
    margin-bottom: 4px;
}}
.add-btn {{
    background: rgba(127, 119, 221, 0.15);
    border: 1px solid rgba(127, 119, 221, 0.3);
    border-radius: 8px;
    color: {ACCENT};
    font-size: 12px;
    padding: 4px 12px;
    margin-top: 8px;
}}
.add-btn:hover {{
    background: rgba(127, 119, 221, 0.25);
}}
.event-row-btn {{
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 3px 6px;
    min-height: 0;
}}
.event-row-btn:hover {{
    background: rgba(127, 119, 221, 0.08);
}}
.event-desc {{
    color: #444;
    font-size: 10px;
}}
.event-reminder {{
    color: {ACCENT};
    font-size: 10px;
    margin-left: 4px;
}}
""".encode()

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


WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
MONTHS_RU = [
    "",
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
]


def get_user_email():
    try:
        if os.path.exists(USER_FILE):
            return open(USER_FILE).read().strip()
    except Exception:
        pass
    return ""


def get_credentials_silent():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not os.path.exists(TOKEN_FILE):
        return None
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if creds.valid:
            return creds
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
            return creds
    except Exception:
        pass
    return None




def fetch_events(year, month):
    try:
        from googleapiclient.discovery import build

        creds = get_credentials_silent()
        if not creds:
            return None
        service = build("calendar", "v3", credentials=creds)

        # Cache user email once for authuser URL param
        if not os.path.exists(USER_FILE):
            try:
                cal = service.calendars().get(calendarId="primary").execute()
                email = cal.get("id", "")
                if "@" in email:
                    os.makedirs(CREDS_DIR, exist_ok=True)
                    with open(USER_FILE, "w") as f:
                        f.write(email)
            except Exception:
                pass

        start = datetime.datetime(year, month, 1).isoformat() + "Z"
        last_day = calendar.monthrange(year, month)[1]
        end = datetime.datetime(year, month, last_day, 23, 59, 59).isoformat() + "Z"

        try:
            cal_meta = service.calendarList().get(calendarId="primary").execute()
            default_reminders = cal_meta.get("defaultReminders", [])
        except Exception:
            default_reminders = []

        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start,
                timeMax=end,
                singleEvents=True,
                orderBy="startTime",
                maxResults=100,
            )
            .execute()
        )

        events_by_day = {}
        for e in result.get("items", []):
            start_info = e.get("start", {})
            date_str = start_info.get("dateTime", start_info.get("date", ""))
            day = int(date_str[8:10]) if len(date_str) >= 10 else None
            if not day:
                continue

            ev_reminders = e.get("reminders", {})
            if ev_reminders.get("useDefault") and default_reminders:
                reminder_min = default_reminders[0].get("minutes")
            elif ev_reminders.get("overrides"):
                reminder_min = ev_reminders["overrides"][0].get("minutes")
            else:
                reminder_min = None

            raw_desc = (e.get("description") or "").strip()
            # strip HTML tags for plain text
            import re as _re
            desc = _re.sub(r"<[^>]+>", "", raw_desc)[:80]

            events_by_day.setdefault(day, []).append({
                "title": e.get("summary", ""),
                "time": date_str[11:16] if "T" in date_str else "Весь день",
                "id": e.get("id", ""),
                "htmlLink": e.get("htmlLink", ""),
                "description": desc,
                "reminder": reminder_min,
            })
        return events_by_day
    except Exception as ex:
        print(f"[calendar] fetch error: {ex}")
        return {}


class CalendarPopup(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.today = datetime.date.today()
        self.year = self.today.year
        self.month = self.today.month
        self.selected_day = self.today.day
        self.events = {}

        self.set_decorated(False)
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
        # Fullscreen overlay so backdrop clicks are caught for dismissal
        for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                     GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(self, edge, True)

        screen = self.get_screen()
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Window-level click: anything outside the popup closes it
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("button-press-event", self._on_window_click)

        # Align popup to top-right with margins
        align = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        align.set_halign(Gtk.Align.END)
        align.set_valign(Gtk.Align.START)
        align.set_margin_top(8)
        align.set_margin_end(8)
        self.add(align)

        # EventBox with real GDK window — swallows clicks inside popup
        popup_eb = Gtk.EventBox()
        popup_eb.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        popup_eb.connect("button-press-event", lambda *_: True)
        self._popup_eb = popup_eb
        align.pack_start(popup_eb, False, False, 0)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.get_style_context().add_class("popup")
        popup_eb.add(outer)

        # Header row
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hdr.set_halign(Gtk.Align.FILL)
        outer.pack_start(hdr, False, False, 0)

        btn_prev = Gtk.Button(label="‹")
        btn_prev.get_style_context().add_class("nav-btn")
        btn_prev.connect("clicked", lambda _: self.change_month(-1))
        hdr.pack_start(btn_prev, False, False, 0)

        self.month_label = Gtk.Label()
        self.month_label.get_style_context().add_class("header")
        self.month_label.set_halign(Gtk.Align.CENTER)
        hdr.pack_start(self.month_label, True, True, 0)

        btn_next = Gtk.Button(label="›")
        btn_next.get_style_context().add_class("nav-btn")
        btn_next.connect("clicked", lambda _: self.change_month(1))
        hdr.pack_start(btn_next, False, False, 0)

        # Calendar grid
        self.grid = Gtk.Grid()
        self.grid.set_halign(Gtk.Align.CENTER)
        self.grid.set_column_homogeneous(True)
        outer.pack_start(self.grid, False, False, 0)

        # Separator
        sep = Gtk.Separator()
        sep.get_style_context().add_class("separator")
        outer.pack_start(sep, False, False, 0)

        # Events section
        self.section_lbl = Gtk.Label()
        self.section_lbl.get_style_context().add_class("section-label")
        self.section_lbl.set_halign(Gtk.Align.START)
        outer.pack_start(self.section_lbl, False, False, 0)

        self.events_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.pack_start(self.events_box, False, False, 0)

        # Add event / logout row — hidden until authenticated
        self.btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        outer.pack_start(self.btn_row, False, False, 0)

        add_btn = Gtk.Button(label="+ Добавить событие")
        add_btn.get_style_context().add_class("add-btn")
        add_btn.connect("clicked", self.on_add_event)
        self.btn_row.pack_start(add_btn, True, True, 0)

        logout_btn = Gtk.Button(label="󰍃")
        logout_btn.get_style_context().add_class("add-btn")
        logout_btn.connect("clicked", self.on_logout)
        self.btn_row.pack_start(logout_btn, False, False, 0)

        self.authenticated = False
        self.connecting = False

        self.connect("key-press-event", self.on_key)

        self.build_calendar()
        self.show_all()
        self.btn_row.set_visible(False)

        threading.Thread(target=self.load_events_async, daemon=True).start()

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
            args=(self.quit, geo.x, geo.y, geo.width, geo.height),
            daemon=True,
        ).start()
        GLib.timeout_add(400, self._start_ipc_watcher)

    def _start_ipc_watcher(self):
        threading.Thread(target=watch_hyprland, args=(self.quit,), daemon=True).start()
        return False

    def _on_window_click(self, *_):
        # popup_eb swallows its own clicks (returns True), so this handler
        # only fires for clicks on the transparent area outside the popup
        if not self.connecting:
            self.quit()
        return True

    def on_connect_clicked(self, _):
        self._show_events_content([self._make_label("Подготовка...")])

        try:
            os.remove(URL_FILE)
        except OSError:
            pass

        # Detached process — survives popup closure, sends notify-send on success
        oauth_script = os.path.expanduser("~/.local/bin/waybar-calendar-oauth.py")
        subprocess.Popen([sys.executable, oauth_script], start_new_session=True)

        GLib.timeout_add(500, self._poll_oauth_url)

    def _poll_oauth_url(self):
        try:
            if os.path.exists(URL_FILE):
                url = open(URL_FILE).read().strip()
                if url:
                    # Copy URL silently and close — OAuth finishes in background
                    subprocess.Popen(["wl-copy", url])
                    subprocess.Popen([
                        "notify-send", "󰊫 Google Calendar",
                        "Ссылка скопирована — вставь в браузер и авторизуйся",
                        "--expire-time=7000",
                    ])
                    self.quit()
                    return False
        except Exception:
            pass
        return True

    def _make_label(self, text):
        lbl = Gtk.Label(label=text)
        lbl.get_style_context().add_class("no-events")
        lbl.set_halign(Gtk.Align.START)
        return lbl

    def _show_events_content(self, widgets):
        for child in self.events_box.get_children():
            self.events_box.remove(child)
        for w in widgets:
            self.events_box.pack_start(w, False, False, 4)
        self.events_box.show_all()

    def load_events_async(self):
        events = fetch_events(self.year, self.month)
        GLib.idle_add(self.on_events_loaded, events)

    def on_events_loaded(self, events):
        if events is None:
            self.authenticated = False
        else:
            self.authenticated = True
            self.events = events
        self.build_calendar()
        self.update_events_panel()

    def change_month(self, delta):
        self.month += delta
        if self.month > 12:
            self.month = 1
            self.year += 1
        elif self.month < 1:
            self.month = 12
            self.year -= 1
        self.selected_day = 1
        self.events = {}
        self.build_calendar()
        self.update_events_panel()
        threading.Thread(target=self.load_events_async, daemon=True).start()

    def build_calendar(self):
        for child in self.grid.get_children():
            self.grid.remove(child)

        self.month_label.set_text(f"{MONTHS_RU[self.month]} {self.year}")

        for col_idx, wd in enumerate(WEEKDAYS):
            lbl = Gtk.Label(label=wd)
            lbl.get_style_context().add_class("weekday")
            lbl.set_halign(Gtk.Align.CENTER)
            self.grid.attach(lbl, col_idx, 0, 1, 1)

        cal = calendar.monthcalendar(self.year, self.month)
        for row_idx, week in enumerate(cal):
            for col_idx, day in enumerate(week):
                if day == 0:
                    lbl = Gtk.Label(label="")
                    lbl.set_size_request(38, 32)
                    self.grid.attach(lbl, col_idx, row_idx + 1, 1, 1)
                    continue

                btn = Gtk.Button(label=str(day))
                btn.get_style_context().add_class("day-btn")

                is_today = (
                    day == self.today.day
                    and self.month == self.today.month
                    and self.year == self.today.year
                )

                if is_today:
                    btn.get_style_context().add_class("day-today")
                if day in self.events:
                    btn.get_style_context().add_class("day-has-event")

                btn.connect("clicked", lambda b, d=day: self.select_day(d))
                self.grid.attach(btn, col_idx, row_idx + 1, 1, 1)

        self.grid.show_all()

    def select_day(self, day):
        self.selected_day = day
        self.build_calendar()
        self.update_events_panel()

    def update_events_panel(self):
        for child in self.events_box.get_children():
            self.events_box.remove(child)

        is_today = (
            self.selected_day == self.today.day
            and self.month == self.today.month
            and self.year == self.today.year
        )
        label = (
            "Сегодня" if is_today else f"{self.selected_day} {MONTHS_RU[self.month]}"
        )
        self.section_lbl.set_text(label.upper())
        self.btn_row.set_visible(self.authenticated)

        if not self.authenticated:
            btn = Gtk.Button(label="󰊫  Подключить Google Calendar")
            btn.get_style_context().add_class("add-btn")
            btn.connect("clicked", self.on_connect_clicked)
            self.events_box.pack_start(btn, False, False, 0)
            self.events_box.show_all()
            return

        day_events = self.events.get(self.selected_day, [])
        if not day_events:
            lbl = Gtk.Label(label="Нет событий")
            lbl.get_style_context().add_class("no-events")
            lbl.set_halign(Gtk.Align.START)
            self.events_box.pack_start(lbl, False, False, 0)
        else:
            for ev in day_events:
                btn = Gtk.Button()
                btn.get_style_context().add_class("event-row-btn")
                btn.set_relief(Gtk.ReliefStyle.NONE)
                btn.connect("clicked", lambda *_: self._open_event())

                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                btn.add(row)

                time_lbl = Gtk.Label(label=ev["time"])
                time_lbl.get_style_context().add_class("event-time")
                time_lbl.set_halign(Gtk.Align.START)
                time_lbl.set_valign(Gtk.Align.START)
                row.pack_start(time_lbl, False, False, 0)

                content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
                row.pack_start(content, True, True, 0)

                title_lbl = Gtk.Label(label=ev["title"])
                title_lbl.get_style_context().add_class("event-title")
                title_lbl.set_halign(Gtk.Align.START)
                title_lbl.set_ellipsize(3)
                title_lbl.set_max_width_chars(24)
                content.pack_start(title_lbl, False, False, 0)

                if ev.get("description"):
                    desc_lbl = Gtk.Label(label=ev["description"])
                    desc_lbl.get_style_context().add_class("event-desc")
                    desc_lbl.set_halign(Gtk.Align.START)
                    desc_lbl.set_ellipsize(3)
                    desc_lbl.set_max_width_chars(24)
                    content.pack_start(desc_lbl, False, False, 0)

                if ev.get("reminder") is not None:
                    rem_lbl = Gtk.Label(label=f"󰂞 {ev['reminder']}мин")
                    rem_lbl.get_style_context().add_class("event-reminder")
                    rem_lbl.set_halign(Gtk.Align.END)
                    rem_lbl.set_valign(Gtk.Align.START)
                    row.pack_start(rem_lbl, False, False, 0)

                self.events_box.pack_start(btn, False, False, 0)

        self.events_box.show_all()

    def _open_event(self, *_):
        email = get_user_email()
        authuser = f"?authuser={email}" if email else ""
        url = (
            f"https://calendar.google.com/calendar/r/day"
            f"/{self.year}/{self.month}/{self.selected_day}{authuser}"
        )
        subprocess.Popen(["xdg-open", url])
        self.quit()

    def on_add_event(self, _):
        date_str = f"{self.year}-{self.month:02d}-{self.selected_day:02d}"
        url = f"https://calendar.google.com/calendar/r/eventedit?dates={date_str}/{date_str}"
        subprocess.Popen(["xdg-open", url])
        self.quit()

    def on_logout(self, _):
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        self.authenticated = False
        self.events = {}
        self.build_calendar()
        self.update_events_panel()

    def on_key(self, widget, event):
        if Gdk.keyval_name(event.keyval) == "Escape":
            self.quit()
        return False

    def quit(self):
        Gtk.main_quit()


if __name__ == "__main__":
    CalendarPopup()
    Gtk.main()
