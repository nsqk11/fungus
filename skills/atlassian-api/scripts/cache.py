"""Page index and content cache, organized by domain."""
import json
import os

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
_INDEX = os.path.join(_DIR, "page-index.json")
_PAGES = os.path.join(_DIR, "pages")


def _read_index():
    """Read full index from disk."""
    if not os.path.exists(_INDEX):
        return {}
    with open(_INDEX) as f:
        return json.load(f)


def _write_index(idx):
    """Write full index to disk."""
    os.makedirs(_DIR, exist_ok=True)
    with open(_INDEX, "w") as f:
        json.dump(idx, f, indent=2, ensure_ascii=False)


def get_meta(domain, page_id):
    """Return cached metadata dict for a page, or None."""
    return _read_index().get(domain, {}).get(str(page_id))


def set_meta(domain, page_id, title, version, author, updated):
    """Update cached metadata for a page."""
    idx = _read_index()
    idx.setdefault(domain, {})[str(page_id)] = {
        "title": title,
        "version": version,
        "author": author,
        "updated": updated,
    }
    _write_index(idx)


def update_titles(domain, pages):
    """Bulk update titles from search results. pages: [(id, title), ...]."""
    idx = _read_index()
    dom = idx.setdefault(domain, {})
    for pid, title in pages:
        dom.setdefault(str(pid), {"title": title})["title"] = title
    _write_index(idx)


def search_index(keyword, domain=None):
    """Search local index by keyword. Return [(pageId, title), ...]."""
    idx = _read_index()
    kw = keyword.lower().split()
    results = []
    domains = [domain] if domain else list(idx.keys())
    for d in domains:
        for pid, meta in idx.get(d, {}).items():
            title = meta.get("title", "") if isinstance(meta, dict) else str(meta)
            if all(w in title.lower() for w in kw):
                results.append((pid, title))
    return results


def read_page(domain, page_id):
    """Read cached page text, or None."""
    p = os.path.join(_PAGES, domain, f"{page_id}.txt")
    if os.path.exists(p):
        with open(p) as f:
            return f.read()
    return None


def write_page(domain, page_id, text):
    """Write page text to cache."""
    d = os.path.join(_PAGES, domain)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"{page_id}.txt"), "w") as f:
        f.write(text)
