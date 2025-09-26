import os
import sys
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import handler as handler_module


def test_no_resources_passes_through():
    with mock.patch("handler.fetch_all_content") as mfetch, \
         mock.patch("handler.parse_html") as mparse, \
         mock.patch("handler.summarize_page") as msumm:
        mfetch.return_value = {"html": "<html></html>", "resources": {}, "failed": []}
        mparse.return_value = {"title": "T", "text_snippet": "text", "images": [], "videos": []}
        msumm.return_value = {"result": {}}

        event = {"url": "https://example.com/page", "full": True}
        resp = handler_module.lambda_handler(event)
        assert resp["statusCode"] == 200
        body = resp["body"]
        assert body is not None
