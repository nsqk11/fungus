"""Authenticated HTTP requests to Atlassian REST APIs."""
import json
import sys
from urllib.error import HTTPError
from urllib.request import Request
from urllib.request import urlopen

from tokens import get as get_token


def _die(msg):
    """Print error and exit."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def request(url, domain, method="GET", data=None, raw=False):
    """Send authenticated request. Return JSON dict or raw string."""
    tok = get_token(domain)
    if not tok:
        _die(f"No token for {domain}")
    headers = {"Authorization": f"Bearer {tok}"}
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode() if isinstance(data, dict) else data
    req = Request(url, data=body, method=method, headers=headers)
    try:
        with urlopen(req) as resp:
            content = resp.read()
            if raw:
                return content.decode()
            return json.loads(content) if content else {}
    except HTTPError as e:
        if e.code == 401:
            _die(f"401 Unauthorized — token for {domain} may be expired.")
        elif e.code == 403:
            _die(f"403 Forbidden — no permission or token lacks scope.")
        else:
            _die(f"HTTP {e.code} from {url}")
