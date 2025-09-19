import os
import json
from unittest.mock import MagicMock, patch

import pytest


def make_boto_resp(secret_string: str):
    return {"SecretString": secret_string}


def test_get_confluence_credentials_from_secretsmanager_json(tmp_path, monkeypatch):
    # Arrange: mock boto3 client to return JSON secret
    secret_data = {"user": "alice@example.com", "token": "s3cr3t"}
    client = MagicMock()
    client.get_secret_value.return_value = make_boto_resp(json.dumps(secret_data))

    with patch("crawler.secrets.boto3"):
        with patch("crawler.secrets.boto3.client", return_value=client):
            # Clear any cached secret
            from crawler import secrets

            secrets._cached_secret = None
            os.environ["CONFLUENCE_SECRET_NAME"] = "confluence/cred"
            creds = secrets.get_confluence_credentials()

    assert creds.get("user") == "alice@example.com"
    assert creds.get("token") == "s3cr3t"


def test_get_confluence_credentials_from_secretsmanager_nonjson(monkeypatch):
    client = MagicMock()
    client.get_secret_value.return_value = make_boto_resp("plainstringtoken")

    with patch("crawler.secrets.boto3"):
        with patch("crawler.secrets.boto3.client", return_value=client):
            from crawler import secrets

            secrets._cached_secret = None
            os.environ["CONFLUENCE_SECRET_NAME"] = "confluence/cred"
            creds = secrets.get_confluence_credentials()

    assert creds.get("token") == "plainstringtoken"


def test_get_confluence_credentials_boto_error(monkeypatch):
    # Simulate boto throwing an error
    def raising_client(*args, **kwargs):
        raise Exception("boto error")

    with patch("crawler.secrets.boto3"):
        with patch("crawler.secrets.boto3.client", side_effect=raising_client):
            from crawler import secrets

            secrets._cached_secret = None
            os.environ["CONFLUENCE_SECRET_NAME"] = "confluence/cred"
            creds = secrets.get_confluence_credentials()

    assert creds == {}


def test_get_confluence_credentials_env_fallback(monkeypatch):
    from crawler import secrets

    secrets._cached_secret = None
    os.environ.pop("CONFLUENCE_SECRET_NAME", None)
    os.environ["CONFLUENCE_USER"] = "bob@example.com"
    os.environ["CONFLUENCE_API_TOKEN"] = "envtoken"

    creds = secrets.get_confluence_credentials()
    assert creds.get("user") == "bob@example.com"
    assert creds.get("token") == "envtoken"
