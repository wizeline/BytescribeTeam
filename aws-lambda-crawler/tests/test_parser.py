from crawler.parser import parse_html


def test_parse_html_basic():
    html = """<html><head><title>Hi</title></head><body><p>Hello world</p></body></html>"""
    out = parse_html(html)
    assert out["title"] == "Hi"
    assert "Hello world" in out["text_snippet"]


def test_parse_html_custom_length():
    html = """<html><head><title>Hi</title></head><body><p>""" + ("A" * 1000) + """</p></body></html>"""
    out = parse_html(html, max_snippet_chars=50)
    assert len(out["text_snippet"]) == 50


def test_parse_html_full_text():
    body_text = """""".join(["Hello", " ", "World", "! This is a test."])
    html = f"<html><head><title>Hi</title></head><body><p>{body_text}</p></body></html>"
    out = parse_html(html, full_text=True)
    assert out["text_snippet"] == body_text
