#!/usr/bin/env python3.12
"""Convert Confluence Storage HTML to plain text."""
import html
import re


def _extract_images(h, base_url=""):
    """Replace ac:image tags with [image: ...] placeholders."""
    def _attachment(m):
        filename = m.group(1)
        if base_url:
            return f"[image: {base_url}/{filename}]"
        return f"[image: {filename}]"

    h = re.sub(
        r'<ac:image[^>]*>.*?<ri:attachment ri:filename="([^"]+)"[^/]*/>'
        r'.*?</ac:image>',
        _attachment, h, flags=re.DOTALL)
    h = re.sub(
        r'<ac:image[^>]*>.*?<ri:url ri:value="([^"]+)"[^/]*/>'
        r'.*?</ac:image>',
        r'[image: \1]', h, flags=re.DOTALL)
    return h


def html2text(h, domain="", page_id=""):
    """Strip HTML tags, preserve image references, normalize whitespace."""
    base_url = ""
    if domain and page_id:
        base_url = f"https://{domain}/download/attachments/{page_id}"
    t = _extract_images(h, base_url)
    t = re.sub(r'<br\s*/?>', '\n', t)
    t = re.sub(r'</?(p|div|li|tr|td|th|h[1-6])[^>]*>', '\n', t)
    t = re.sub(r'<[^>]+>', '', t)
    t = html.unescape(t)
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()
