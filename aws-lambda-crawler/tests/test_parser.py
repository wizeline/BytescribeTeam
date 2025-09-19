from crawler.parser import parse_html


def test_parse_html_basic():
    html = """<html><head><title>Hi</title></head><body><p>Hello world</p></body></html>"""
    out = parse_html(html)
    assert out["title"] == "Hi"
    assert "Hello world" in out["text_snippet"]
