"""Authenticated HTTP requests to Atlassian REST APIs."""
import json
import os
import sqlite3
import sys

_DB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "store.db"
)


def _get_token(domain):
    """Look up the PAT for *domain*, or exit with an error."""
    if not os.path.exists(_DB):
        _die(f"No token for {domain}")
    conn = sqlite3.connect(_DB)
    row = conn.execute(
        "SELECT pat FROM tokens WHERE domain = ?", (domain,)
    ).fetchone()
    conn.close()
    if not row:
        _die(f"No token for {domain}")
    return row[0]


def _die(msg):
    """Print error and exit."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


_last_req = 0.0

def _send(url, headers, method="GET", body=None, raw=False):
    """Send an HTTP request and return JSON or raw string."""
    import time
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen

    global _last_req
    gap = time.monotonic() - _last_req
    if gap < 0.3:
        time.sleep(0.3 - gap)

    for attempt in range(4):
        _last_req = time.monotonic()
        req = Request(url, data=body, method=method, headers=headers)
        try:
            with urlopen(req) as resp:
                content = resp.read()
                if raw:
                    return content.decode()
                return json.loads(content) if content else {}
        except HTTPError as e:
            if e.code == 429:
                time.sleep(float(e.headers.get("Retry-After", 2 ** attempt)))
                continue
            if e.code == 401:
                _die(f"401 Unauthorized — token may be expired ({url})")
            elif e.code == 403:
                _die(f"403 Forbidden — no permission ({url})")
            _die(f"HTTP {e.code} from {url}")
    _die(f"HTTP 429 — rate limited after retries ({url})")


def request(url, domain, method="GET", data=None, raw=False):
    """Send PAT-authenticated request. Return JSON dict or raw string."""
    headers = {"Authorization": f"Bearer {_get_token(domain)}"}
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode() if isinstance(data, dict) else data
    return _send(url, headers, method, body, raw)
