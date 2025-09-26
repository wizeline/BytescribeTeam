"""Quick smoke-run script for the handler that does not require pytest.

This script mocks boto3 and summarize_page to allow running locally without AWS credentials.
"""
import os
import json
from unittest import mock

# Ensure local imports work
ROOT = os.path.abspath(os.path.dirname(__file__))
import sys
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import handler


def main():
    # Mock fetch_all_content to return a simple html and one resource
    fake_resources = {"https://example.com/image.png": b"PNGDATA"}

    with mock.patch("handler.fetch_all_content") as mfetch, \
         mock.patch("handler.parse_html") as mparse, \
         mock.patch("handler.boto3.client") as mock_boto, \
         mock.patch("handler.summarize_page") as msumm:
        mfetch.return_value = {"html": "<html><img src=\"/image.png\"></html>", "resources": fake_resources, "failed": []}
        mparse.return_value = {"title": "Test", "text_snippet": "Hello world", "images": [{"src": "https://example.com/image.png", "alt": "an image"}], "videos": []}

        mock_s3 = mock.Mock()
        mock_boto.return_value = mock_s3
        mock_s3.put_object.return_value = {}
        mock_s3.generate_presigned_url.return_value = "https://presigned.example.com/get/object"

        msumm.return_value = {"result": {"summary": "3 bullets"}}

        os.environ["S3_UPLOAD_BUCKET"] = "my-bucket"
        os.environ["S3_PRESIGNED_EXPIRES"] = "300"

        event = {"url": "https://example.com/page", "full": True}
        resp = handler.lambda_handler(event)
        print(json.dumps(json.loads(resp["body"]), indent=2))


if __name__ == "__main__":
    main()
