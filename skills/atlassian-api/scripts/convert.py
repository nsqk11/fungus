"""Convert Confluence Storage-format HTML to plain text.

The conversion preserves image references as ``[image: url]`` placeholders
and normalises whitespace. This is a lossy transform; keep the original
HTML too if full fidelity matters.
"""
from __future__ import annotations

import html
import re

__all__ = ["html_to_text"]


_ATTACHMENT_PATTERN = re.compile(
    r'<ac:image[^>]*>.*?<ri:attachment ri:filename="([^"]+)"[^/]*/>.*?</ac:image>',
    re.DOTALL,
)
_URL_IMAGE_PATTERN = re.compile(
    r'<ac:image[^>]*>.*?<ri:url ri:value="([^"]+)"[^/]*/>.*?</ac:image>',
    re.DOTALL,
)
_BR_PATTERN = re.compile(r"<br\s*/?>", re.IGNORECASE)
_BLOCK_PATTERN = re.compile(
    r"</?(p|div|li|tr|td|th|h[1-6])[^>]*>", re.IGNORECASE
)
_TAG_PATTERN = re.compile(r"<[^>]+>")
_BLANK_LINES_PATTERN = re.compile(r"\n{3,}")


def _extract_images(body: str, base_url: str) -> str:
    """Replace ``<ac:image>`` tags with ``[image: …]`` placeholders."""

    def _attachment(match: re.Match[str]) -> str:
        filename = match.group(1)
        if base_url:
            return f"[image: {base_url}/{filename}]"
        return f"[image: {filename}]"

    body = _ATTACHMENT_PATTERN.sub(_attachment, body)
    body = _URL_IMAGE_PATTERN.sub(lambda m: f"[image: {m.group(1)}]", body)
    return body


def html_to_text(body_html: str, domain: str = "", page_id: str = "") -> str:
    """Strip HTML tags, preserve image references, normalise whitespace.

    When *domain* and *page_id* are both non-empty, attachment images are
    rewritten with their full download URL so agents can fetch them later.
    """
    if not body_html:
        return ""
    base_url = ""
    if domain and page_id:
        base_url = f"https://{domain}/download/attachments/{page_id}"
    text = _extract_images(body_html, base_url)
    text = _BR_PATTERN.sub("\n", text)
    text = _BLOCK_PATTERN.sub("\n", text)
    text = _TAG_PATTERN.sub("", text)
    text = html.unescape(text)
    text = _BLANK_LINES_PATTERN.sub("\n\n", text)
    return text.strip()
