"""webapp package

This package initializer will attempt to load Confluence credentials for
local development. It prefers environment variables but will fallback to a
local file kept in `dzun-local/confluence-api-token` (this file is in the
workspace root and is intended for local, private use only).

Two accepted methods:
- Set `CONFLUENCE_API_TOKEN` (or `CONFLUENCE_PASSWORD`) in environment.
- Create a file `dzun-local/confluence-api-token` containing the token.

If a `CONFLUENCE_USER` is also set in the environment, the crawler will use
basic auth. If only a bearer token is present, it will use the `CONFLUENCE_BEARER_TOKEN`.
For convenience this module will set the appropriate environment variables so
that `crawler.fetcher` can pick them up unchanged.
"""

import os
from pathlib import Path

__all__ = []
