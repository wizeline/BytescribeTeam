"""Helper to load Confluence credentials from AWS Secrets Manager.

Usage:
    from crawler.secrets import get_confluence_credentials
    creds = get_confluence_credentials()
    user = creds.get("user")
    token = creds.get("token")

This module caches the secret in a module-level variable so calls are fast after cold start.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Optional

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except Exception:  # pragma: no cover - boto3 may not be installed locally
    boto3 = None

_cached_secret: Optional[Dict[str, str]] = None


def _load_from_env() -> Optional[Dict[str, str]]:
    user = os.getenv("CONFLUENCE_USER")
    token = os.getenv("CONFLUENCE_API_TOKEN") or os.getenv("CONFLUENCE_PASSWORD")
    if user and token:
        return {"user": user, "token": token}
    bearer = os.getenv("CONFLUENCE_BEARER_TOKEN")
    if bearer:
        return {"bearer": bearer}
    return None


def get_confluence_credentials() -> Dict[str, str]:
    """Return credentials dict. Try module cache, then Secrets Manager, then environment.

    Returns empty dict if nothing found.
    """
    global _cached_secret
    if _cached_secret is not None:
        return _cached_secret

    # 1) Try environment variables (local dev)
    env = _load_from_env()
    if env:
        _cached_secret = env
        return _cached_secret

    # 2) Try AWS Secrets Manager (if boto3 available and env var provided)
    if boto3 is None:
        _cached_secret = {}
        return _cached_secret

    secret_name = os.getenv("CONFLUENCE_SECRET_NAME")
    if not secret_name:
        _cached_secret = {}
        return _cached_secret

    try:
        client = boto3.client("secretsmanager")
        resp = client.get_secret_value(SecretId=secret_name)
        secret_string = resp.get("SecretString")
        if not secret_string:
            _cached_secret = {}
            return _cached_secret
        try:
            data = json.loads(secret_string)
            if isinstance(data, dict):
                # normalize keys to str
                _cached_secret = {str(k): str(v) for k, v in data.items()}
            else:
                _cached_secret = {"token": str(secret_string)}
            return _cached_secret
        except json.JSONDecodeError:
            _cached_secret = {"token": secret_string}
            return _cached_secret
    except Exception as e:
        # Do not raise; log and fallback to empty. Catch broader exceptions
        # because boto3 may raise different exception types in some environments.
        print(f"Failed to load secret '{secret_name}': {e}")
        _cached_secret = {}
        return _cached_secret
