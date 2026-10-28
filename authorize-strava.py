"""Authorize Strava activity access locally; optionally update repository Secrets."""

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "run_page"))
from strava_auth import ENV_FILE, load_local_env, save_tokens  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--github-repo", help="Also save credentials as Actions Secrets"
    )
    options = parser.parse_args()
    load_local_env()
    client_id = os.environ.get("STRAVA_CLIENT_ID")
    client_secret = os.environ.get("STRAVA_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise SystemExit(
            "Fill STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in .env first."
        )
    state = secrets.token_urlsafe(32)
    result = {}

    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # Authorization codes must not appear in request logs.

        def do_GET(self):
            url = urllib.parse.urlsplit(self.path)
            query = urllib.parse.parse_qs(url.query)
            if url.path != "/callback" or query.get("state") != [state]:
                self.send_error(400)
                return
            result.update({key: values[0] for key, values in query.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<h1>Strava 授权已返回</h1><p>可以关闭此页面，回到 Codex 查看同步结果。</p>".encode()
            )

    with HTTPServer(("127.0.0.1", 8765), Callback) as server:
        server.timeout = 1
        params = urllib.parse.urlencode(
            {
                "client_id": client_id,
                "redirect_uri": "http://localhost:8765/callback",
                "response_type": "code",
                "approval_prompt": "force",
                "scope": "read,activity:read_all",
                "state": state,
            }
        )
        url = "https://www.strava.com/oauth/authorize?" + params
        print("Opening Strava authorization; please allow activity access.", flush=True)
        print(url, flush=True)
        webbrowser.open(url)
        deadline = time.monotonic() + 900
        while not result and time.monotonic() < deadline:
            server.handle_request()
    if "code" not in result:
        raise SystemExit(
            "Authorization was declined or timed out; run this script again."
        )
    if "activity:read_all" not in result.get("scope", "").split(","):
        raise SystemExit("Activity permission was not granted; please authorize again.")
    payload = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": result["code"],
            "grant_type": "authorization_code",
        }
    ).encode()
    try:
        with urllib.request.urlopen(
            "https://www.strava.com/oauth/token", data=payload, timeout=30
        ) as response:
            tokens = json.load(response)
        save_tokens(tokens)
        request = urllib.request.Request(
            "https://www.strava.com/api/v3/athlete/activities?per_page=1",
            headers={"Authorization": "Bearer " + tokens["access_token"]},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            json.load(response)
        print("Strava activity access verified; local credentials saved.", flush=True)
    except urllib.error.HTTPError as error:
        raise SystemExit(f"Strava authorization failed (HTTP {error.code}).") from None
    if options.github_repo:
        gh = shutil.which("gh") or str(
            Path(os.environ["LOCALAPPDATA"]) / "Programs/GitHub CLI/bin/gh.exe"
        )
        subprocess.run(
            [
                gh,
                "secret",
                "set",
                "--repo",
                options.github_repo,
                "--env-file",
                str(ENV_FILE),
            ],
            check=True,
        )
        print("GitHub Actions Secrets updated.", flush=True)


if __name__ == "__main__":
    main()
