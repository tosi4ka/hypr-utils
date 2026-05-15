#!/usr/bin/env python3
"""Google Calendar notification daemon. Launch via Hyprland exec-once."""
import datetime
import json
import os
import subprocess
import time

TOKEN_FILE = os.path.expanduser("~/.config/waybar-calendar/token.json")
CREDS_FILE = os.path.expanduser("~/.config/waybar-calendar/credentials.json")
SCOPES = ["https://www.googleapis.com/auth/calendar"]
FIRED_FILE = "/tmp/waybar-calendar-fired.json"


def get_creds():
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


def fetch_upcoming():
    try:
        from googleapiclient.discovery import build

        creds = get_creds()
        if not creds:
            return []
        service = build("calendar", "v3", credentials=creds)

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        start = now_utc.isoformat()
        end = (now_utc + datetime.timedelta(hours=24)).isoformat()

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
                maxResults=50,
            )
            .execute()
        )

        events = []
        for e in result.get("items", []):
            dt_str = e.get("start", {}).get("dateTime", "")
            if not dt_str:
                continue
            event_dt = datetime.datetime.fromisoformat(dt_str)
            if event_dt.tzinfo is None:
                event_dt = event_dt.replace(tzinfo=datetime.timezone.utc)

            ev_rem = e.get("reminders", {})
            if ev_rem.get("useDefault"):
                mins_list = [r.get("minutes", 10) for r in default_reminders]
            elif ev_rem.get("overrides"):
                mins_list = [r.get("minutes", 10) for r in ev_rem["overrides"]]
            else:
                mins_list = []

            events.append({
                "id": e.get("id", ""),
                "title": e.get("summary", "Событие"),
                "dt": event_dt,
                "reminder_mins": mins_list,
            })
        return events
    except Exception as ex:
        print(f"[notify] fetch error: {ex}")
        return []


def load_fired():
    try:
        if os.path.exists(FIRED_FILE):
            with open(FIRED_FILE) as f:
                return set(json.load(f))
    except Exception:
        pass
    return set()


def save_fired(fired):
    try:
        with open(FIRED_FILE, "w") as f:
            json.dump(list(fired), f)
    except Exception:
        pass


def check_and_notify():
    now = datetime.datetime.now(datetime.timezone.utc)
    events = fetch_upcoming()
    fired = load_fired()

    for ev in events:
        for mins in ev["reminder_mins"]:
            key = f"{ev['id']}-{mins}"
            if key in fired:
                continue
            notify_at = ev["dt"] - datetime.timedelta(minutes=mins)
            if abs((now - notify_at).total_seconds()) <= 60:
                time_str = ev["dt"].astimezone().strftime("%H:%M")
                body = f"Через {mins} мин — {time_str}" if mins > 0 else time_str
                subprocess.Popen([
                    "notify-send",
                    f"󰃰  {ev['title']}",
                    body,
                    "--expire-time=8000",
                    "--urgency=normal",
                ])
                fired.add(key)

    # Keep only keys from today to avoid unbounded growth
    today = datetime.date.today().isoformat()
    fired = {k for k in fired if today in k or len(k) < 100}
    save_fired(fired)


if __name__ == "__main__":
    print("[calendar-notify] started")
    while True:
        try:
            check_and_notify()
        except Exception as e:
            print(f"[calendar-notify] error: {e}")
        time.sleep(60)
