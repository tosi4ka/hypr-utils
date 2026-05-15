#!/usr/bin/env python3
"""Standalone OAuth helper for waybar-calendar.
Runs as a detached process — survives popup closure.
Writes the auth URL to URL_FILE, waits for browser redirect,
saves token, then removes URL_FILE to signal completion.
"""
import os
import subprocess
import wsgiref.simple_server
import wsgiref.util

CREDS_DIR = os.path.expanduser("~/.config/waybar-calendar")
CREDS_FILE = os.path.join(CREDS_DIR, "credentials.json")
TOKEN_FILE = os.path.join(CREDS_DIR, "token.json")
URL_FILE = "/tmp/waybar-calendar-oauth-url"
SCOPES = ["https://www.googleapis.com/auth/calendar"]

SUCCESS_HTML = b"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{background:#14141c;display:flex;align-items:center;justify-content:center;
height:100vh;margin:0;font-family:monospace;}
.m{color:#7f77dd;font-size:18px;text-align:center;}
.s{color:#555;font-size:13px;margin-top:8px;}</style></head>
<body><div><p class="m">&#10003; &#1040;&#1074;&#1090;&#1086;&#1088;&#1080;&#1079;&#1072;&#1094;&#1080;&#1103; &#1079;&#1072;&#1074;&#1077;&#1088;&#1096;&#1077;&#1085;&#1072;</p>
<p class="s">&#1052;&#1086;&#1078;&#1085;&#1086; &#1079;&#1072;&#1082;&#1088;&#1099;&#1090;&#1100; &#1101;&#1090;&#1091; &#1074;&#1082;&#1083;&#1072;&#1076;&#1082;&#1091;</p></div></body></html>"""


def main():
    from google_auth_oauthlib.flow import InstalledAppFlow

    last_uri = []

    class _App:
        def __call__(self, environ, start_response):
            last_uri.append(wsgiref.util.request_uri(environ))
            start_response("200 OK", [("Content-type", "text/html; charset=utf-8")])
            return [SUCCESS_HTML]

    class _NullLog(wsgiref.simple_server.WSGIRequestHandler):
        def log_message(self, *_):
            pass

    server = wsgiref.simple_server.make_server(
        "localhost", 0, _App(), handler_class=_NullLog
    )
    port = server.server_port

    flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
    flow.redirect_uri = f"http://localhost:{port}/"
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

    # Signal the popup: here is the URL to copy
    os.makedirs(CREDS_DIR, exist_ok=True)
    with open(URL_FILE, "w") as f:
        f.write(auth_url)

    print(f"[oauth] listening on port {port}")
    server.handle_request()

    if not last_uri:
        print("[oauth] no redirect received")
        try:
            os.remove(URL_FILE)
        except OSError:
            pass
        return

    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    flow.fetch_token(authorization_response=last_uri[0])

    with open(TOKEN_FILE, "w") as f:
        f.write(flow.credentials.to_json())
    print("[oauth] token saved")

    # Remove URL file — signals completion
    try:
        os.remove(URL_FILE)
    except OSError:
        pass

    subprocess.Popen([
        "notify-send", "󰊫 Google Calendar",
        "Авторизация успешна — теперь открой календарь",
        "--expire-time=6000",
    ])


if __name__ == "__main__":
    main()
