"""Tests for convert.py — Storage HTML to plain text."""
from __future__ import annotations

import convert


def test_empty_input():
    assert convert.html_to_text("") == ""


def test_strips_paragraph_tags():
    out = convert.html_to_text("<p>hello</p><p>world</p>")
    assert "hello" in out
    assert "world" in out
    assert "<p>" not in out


def test_br_becomes_newline():
    out = convert.html_to_text("line1<br/>line2")
    assert out == "line1\nline2"


def test_html_entities_unescaped():
    out = convert.html_to_text("<p>a &amp; b &lt;x&gt;</p>")
    assert "a & b <x>" in out


def test_collapses_triple_blank_lines():
    out = convert.html_to_text("<p>a</p>\n\n\n\n\n<p>b</p>")
    assert "\n\n\n" not in out


def test_attachment_image_without_base_url():
    html = (
        '<ac:image ac:width="100">'
        '<ri:attachment ri:filename="diagram.png" />'
        '</ac:image>'
    )
    out = convert.html_to_text(html)
    assert "[image: diagram.png]" in out


def test_attachment_image_with_base_url():
    html = (
        '<ac:image><ri:attachment ri:filename="diagram.png" /></ac:image>'
    )
    out = convert.html_to_text(html, domain="example.com", page_id="42")
    assert (
        "[image: https://example.com/download/attachments/42/diagram.png]"
    ) in out


def test_url_image():
    html = (
        '<ac:image><ri:url ri:value="https://cdn/img.png" /></ac:image>'
    )
    out = convert.html_to_text(html)
    assert "[image: https://cdn/img.png]" in out


def test_preserves_text_inside_headings():
    html = "<h1>Title</h1><p>body</p>"
    out = convert.html_to_text(html)
    assert "Title" in out
    assert "body" in out
