"""Token CRUD on tokens.json."""
import json
import os
import stat

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
_FILE = os.path.join(_DIR, "tokens.json")


def _read():
    """Read tokens dict from disk."""
    if not os.path.exists(_FILE):
        return {}
    with open(_FILE) as f:
        return json.load(f)


def _write(data):
    """Write tokens dict to disk with 600 permissions."""
    os.makedirs(_DIR, exist_ok=True)
    with open(_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.chmod(_FILE, stat.S_IRUSR | stat.S_IWUSR)


def get(domain):
    """Return token for domain, or None."""
    return _read().get(domain)


def set_(domain, pat):
    """Store token for domain."""
    data = _read()
    data[domain] = pat
    _write(data)


def remove(domain):
    """Remove token for domain."""
    data = _read()
    data.pop(domain, None)
    _write(data)


def list_domains():
    """Return list of configured domains."""
    return list(_read().keys())
