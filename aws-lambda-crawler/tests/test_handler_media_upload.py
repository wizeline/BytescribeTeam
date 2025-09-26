import json
import os
import sys
from unittest import mock

import pytest

# Ensure the parent package dir is on sys.path so we can import handler
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import handler as handler_module


@mock.patch("aws_lambda_crawler.handler.boto3.client")
@mock.patch("aws_lambda_crawler.handler.fetch_all_content")
@mock.patch("aws_lambda_crawler.handler.parse_html")
@mock.patch("aws_lambda_crawler.handler.summarize_page")
def test_lambda_handler_uploads_and_passes_media(mock_summarize, mock_parse, mock_fetch_all, mock_boto_client):
    # Setup fake fetched resources
    fake_resources = {
        "https://example.com/image.png": b"PNGDATA",
        "https://example.com/script.js": b"JSDATA",
    }
    mock_fetch_all.return_value = {"html": "<html></html>", "resources": fake_resources, "failed": []}

    # Parsed images/videos
    mock_parse.return_value = {
        "title": "Test",
        "text_snippet": "Some text",
        "images": [{"src": "https://example.com/image.png", "alt": "an image"}],
        "videos": []
    }

    # Mock boto3 client put_object and generate_presigned_url
    mock_s3 = mock.Mock()
    mock_boto_client.return_value = mock_s3
    mock_s3.put_object.return_value = {}
    mock_s3.generate_presigned_url.return_value = "https://presigned.example.com/get/object"

    # Mock summarize_page
    mock_summarize.return_value = {"result": {}}

    # Set env var for bucket
    os.environ["S3_UPLOAD_BUCKET"] = "my-bucket"
    os.environ["S3_PRESIGNED_EXPIRES"] = "60"

    event = {"url": "https://example.com/page", "full": True}
    resp = handler_module.lambda_handler(event)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "uploaded_media" in body
    uploaded = body["uploaded_media"]
    # Should contain at least the uploaded image
    assert any(m.get("source_url") == "https://example.com/image.png" for m in uploaded)
    # Verify summarize_page was called with media_refs
    assert mock_summarize.call_count == 1
    called_kwargs = mock_summarize.call_args[1]
    assert "media_refs" in called_kwargs


if __name__ == "__main__":
    pytest.main([__file__])
