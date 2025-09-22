import json

from crawler.fetcher import fetch_html, fetch_all_content
from crawler.parser import parse_html
import os


def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "http://localhost:3000",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "POST,OPTIONS",
    }


def _proxy_response(status_code: int, payload: dict):
    return {
        "statusCode": status_code,
        "headers": _cors_headers(),
        "body": json.dumps(payload),
    }


def lambda_handler(event, context=None):
    """AWS Lambda handler.

    Accepts two shapes:
    - direct invocation: event is dict with `url` key
    - API Gateway proxy: event contains `httpMethod` and `body` (JSON string)

    Returns API Gateway proxy-style response with CORS headers so browsers receive
    `Access-Control-Allow-Origin` on success and error responses.
    """
    # Handle preflight from browsers
    if isinstance(event, dict) and event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": _cors_headers(), "body": ""}

    # Extract URL from API Gateway body or direct event
    url = None
    if isinstance(event, dict):
        if "body" in event and event["body"]:
            try:
                body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
            except Exception:
                return _proxy_response(400, {"error": "invalid JSON body"})
            url = body.get("url")
        else:
            url = event.get("url")

    if not url:
        return _proxy_response(400, {"error": "missing 'url' in event"})

    # Support asking for full content by providing `full`, `full_content` or `full_text`
    # flag in event or JSON body
    want_full = False
    if isinstance(event, dict):
        # API Gateway: body may contain JSON
        if "body" in event and event["body"]:
            try:
                body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
                want_full = bool(
                    body.get("full") or body.get("full_content") or body.get("full_text")
                )
            except Exception:
                pass
        else:
            want_full = bool(
                event.get("full") or event.get("full_content") or event.get("full_text")
            )

    try:
        if want_full:
            fetched = fetch_all_content(url)
            if fetched is None:
                return _proxy_response(502, {"error": "failed to fetch url (full)", "url": url})
            html = fetched.get("html")
        else:
            html = fetch_html(url)
    except Exception as exc:
        return _proxy_response(502, {"error": "failed to fetch url", "url": url, "detail": str(exc)})

    if html is None:
        return _proxy_response(502, {"error": "failed to fetch url", "url": url})

    try:
        # Allow overriding snippet length via environment variable
        parse_max = None
        try:
            env_val = os.getenv("PARSE_SNIPPET_MAX")
            parse_max = int(env_val) if env_val is not None else None
        except Exception:
            parse_max = None

        parsed = parse_html(html, max_snippet_chars=parse_max, full_text=want_full)
    except Exception as exc:
        return _proxy_response(500, {"error": "failed to parse html", "detail": str(exc)})

    response_payload = {"url": url, **parsed}
    if want_full and isinstance(fetched, dict):
        resources = fetched.get("resources", {})
        failed = fetched.get("failed", [])
        response_payload["resource_count"] = len(resources)
        response_payload["failed_resources"] = failed

    return _proxy_response(200, response_payload)
