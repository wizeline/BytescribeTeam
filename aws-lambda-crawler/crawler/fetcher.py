
import os
import time
import urllib.parse
import urllib.robotparser
from typing import Optional

from crawler.secrets import get_confluence_credentials

import requests
from requests.exceptions import RequestException
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Tuple, List


class RobotsChecker:
    def __init__(self, user_agent: str = "aws-lambda-crawler"):
        self.user_agent = user_agent
        self._parsers: dict[str, urllib.robotparser.RobotFileParser] = {}

    def allowed(self, url: str) -> bool:
        parsed = urllib.parse.urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        rp = self._parsers.get(base)
        if rp is None:
            robots_url = urllib.parse.urljoin(base, "/robots.txt")
            rp = urllib.robotparser.RobotFileParser()
            try:
                rp.set_url(robots_url)
                rp.read()
            except Exception:
                # If robots can't be fetched, assume allowed
                rp = None
            self._parsers[base] = rp

        if rp is None:
            return True
        return rp.can_fetch(self.user_agent, url)


def fetch_html(url: str, timeout: int = 10, max_retries: int = 2, backoff: float = 1.0) -> Optional[str]:
    """Fetch HTML content from `url` with robots.txt respect, retries, and timeout.

    Returns HTML text on success or None on error / disallowed by robots.
    """
    headers = {"User-Agent": "aws-lambda-crawler/1.0 (+https://example.com)"}
    # Support optional Confluence authentication via Secrets Manager or environment variables:
    # - Preferred: store secret in AWS Secrets Manager and set CONFLUENCE_SECRET_NAME in env
    #   Secret should be JSON like {"user":"...","token":"..."} or {"bearer":"..."}
    # - Fallback: Basic auth via CONFLUENCE_USER + CONFLUENCE_API_TOKEN or CONFLUENCE_PASSWORD
    auth = None
    creds = get_confluence_credentials()
    bearer = creds.get("bearer")
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    else:
        user = creds.get("user") or os.getenv("CONFLUENCE_USER")
        token = creds.get("token") or os.getenv("CONFLUENCE_API_TOKEN") or os.getenv("CONFLUENCE_PASSWORD")
        if user and token:
            auth = HTTPBasicAuth(user, token)
    parsed = urllib.parse.urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    # Helper: try Confluence REST API for a page id (returns HTML string or None)
    def _try_confluence_rest_api() -> Optional[str]:
        # require auth for REST API
        if not (bearer or auth):
            return None
        # find a numeric page id in the URL path
        parts = parsed.path.rstrip("/").split("/")
        page_id = None
        for p in reversed(parts):
            if p.isdigit():
                page_id = p
                break
        if not page_id:
            return None
        api_url = f"{base}/wiki/rest/api/content/{page_id}?expand=body.view"
        headers_rest = headers.copy()
        headers_rest["Accept"] = "application/json"
        try:
            resp = requests.get(api_url, headers=headers_rest, timeout=timeout, auth=auth)
            resp.raise_for_status()
            data = resp.json()
            html = data.get("body", {}).get("view", {}).get("value")
            return html
        except RequestException as e:
            # debug: surface status code for local troubleshooting
            try:
                status = e.response.status_code if e.response is not None else None
            except Exception:
                status = None
            print(f"Confluence REST API request failed: {api_url} status={status} error={e}")
            return None
        except Exception as e:
            print(f"Confluence REST API parsing failed: {e}")
            return None

    # If the caller passed a REST API URL already, try to extract the stored HTML
    if "/rest/api/content" in parsed.path:
        try:
            headers_rest = headers.copy()
            headers_rest["Accept"] = "application/json"
            resp = requests.get(url, headers=headers_rest, timeout=timeout, auth=auth)
            resp.raise_for_status()
            try:
                data = resp.json()
                html = data.get("body", {}).get("view", {}).get("value")
                if html:
                    return html
            except Exception:
                # not JSON or missing view -> return raw text
                return resp.text
        except RequestException:
            try:
                print(f"Confluence API request failed: status={resp.status_code} url={url}")
            except Exception:
                pass
            return None

    # For normal page URLs, respect robots.txt. Skip robots for API endpoints already handled.
    rc = RobotsChecker(user_agent=headers["User-Agent"])
    if not rc.allowed(url):
        return None

    attempt = 0
    while attempt <= max_retries:
        try:
            resp = requests.get(url, headers=headers, timeout=timeout, auth=auth)
            resp.raise_for_status()
            text = resp.text
            # Prefer REST API for Atlassian Cloud hosts when auth is available
            # (regular page URLs often return client-side JS placeholders or login HTML)
            if parsed.netloc.endswith("atlassian.net") and (bearer or auth):
                api_html = _try_confluence_rest_api()
                if api_html:
                    return api_html
            # If Confluence returned the JS-disabled placeholder, and we have auth, also try REST API
            if ("Atlassian JavaScript is disabled" in text or "Atlassian JavaScript load error" in text) and (bearer or auth):
                api_html = _try_confluence_rest_api()
                if api_html:
                    return api_html
            return text
        except RequestException:
            attempt += 1
            if attempt > max_retries:
                return None
            time.sleep(backoff * attempt)


def fetch_all_content(url: str, timeout: int = 10, max_retries: int = 2) -> Optional[Dict[str, object]]:
    """Fetch the HTML and attempt to download common external resources.

    Returns dict with keys:
      - "html": str HTML text
      - "resources": dict mapping absolute URL -> bytes
      - "failed": list of resource URLs that failed to download

    Returns None if the main HTML could not be fetched.
    """
    html = fetch_html(url, timeout=timeout, max_retries=max_retries)
    if html is None:
        return None

    soup = BeautifulSoup(html, "html.parser")
    parsed_page = urllib.parse.urlparse(url)
    base = f"{parsed_page.scheme}://{parsed_page.netloc}"

    # Gather resource references
    resource_urls: List[str] = []
    for img in soup.find_all("img"):
        src = img.get("src")
        if src:
            resource_urls.append(src)
    for link in soup.find_all("link", rel=lambda x: x and "stylesheet" in x):
        href = link.get("href")
        if href:
            resource_urls.append(href)
    for script in soup.find_all("script"):
        src = script.get("src")
        if src:
            resource_urls.append(src)

    # Resolve and dedupe
    resolved: List[str] = []
    seen = set()
    for r in resource_urls:
        abs_url = urllib.parse.urljoin(base, r)
        if abs_url not in seen:
            seen.add(abs_url)
            resolved.append(abs_url)

    resources: Dict[str, bytes] = {}
    failed: List[str] = []

    def _download(res_url: str) -> Tuple[str, Optional[bytes]]:
        try:
            resp = requests.get(res_url, headers={"User-Agent": "aws-lambda-crawler/1.0"}, timeout=timeout)
            resp.raise_for_status()
            return res_url, resp.content
        except Exception:
            return res_url, None

    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(_download, u): u for u in resolved}
        for fut in as_completed(futures):
            u = futures[fut]
            try:
                url_got, data = fut.result()
                if data is None:
                    failed.append(url_got)
                else:
                    resources[url_got] = data
            except Exception:
                failed.append(u)

    return {"html": html, "resources": resources, "failed": failed}

