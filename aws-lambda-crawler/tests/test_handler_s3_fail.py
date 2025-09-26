import os
import sys
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import handler as handler_module


def test_s3_upload_failure_does_not_break_summary():
    with mock.patch("handler.fetch_all_content") as mfetch, \
         mock.patch("handler.parse_html") as mparse, \
         mock.patch("handler.boto3.client") as mock_boto, \
         mock.patch("handler.summarize_page") as msumm:
        mfetch.return_value = {"html": "<html></html>", "resources": {"https://x/a.png": b"d"}, "failed": []}
        mparse.return_value = {"title": "T", "text_snippet": "text", "images": [{"src": "https://x/a.png"}], "videos": []}

        mock_s3 = mock.Mock()
        mock_boto.return_value = mock_s3
        # Simulate put_object raising a ClientError
        from botocore.exceptions import ClientError
        mock_s3.put_object.side_effect = ClientError({"Error": {"Code": "AccessDenied", "Message": "denied"}}, "PutObject")

        msumm.return_value = {"result": {}}

        os.environ["S3_UPLOAD_BUCKET"] = "my-bucket"
        event = {"url": "https://example.com/page", "full": True}
        resp = handler_module.lambda_handler(event)
        assert resp["statusCode"] == 200
        body = resp["body"]
        assert body is not None
