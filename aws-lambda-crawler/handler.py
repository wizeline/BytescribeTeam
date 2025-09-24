import json

from crawler.fetcher import fetch_html, fetch_all_content
from crawler.parser import parse_html
from crawler.processor import create_document
from crawler.summarizer import summarize_document, summarize_text
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

        # Special action: index -> return structured document ready for embedding/indexing
        if isinstance(event, dict):
            action = None
            # check body JSON first
            if "body" in event and event["body"]:
                try:
                    body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
                    action = body.get("action")
                except Exception:
                    action = None
            else:
                action = event.get("action")

            if action == "index":
                # create structured document (includes chunks)
                try:
                    document = create_document(url, html, chunk_size=1000, overlap=200, parse_snippet_max=parse_max)
                except Exception as exc:
                    return _proxy_response(500, {"error": "failed to create document", "detail": str(exc)})

                # If full fetch included resources, attach counts
                if want_full and isinstance(fetched, dict):
                    resources = fetched.get("resources", {})
                    failed = fetched.get("failed", [])
                    document["resource_count"] = len(resources)
                    document["failed_resources"] = failed

                return _proxy_response(200, {"url": url, "document": document})

            if action == "summarize":
                # Extract summarization parameters from body
                summary_length = "medium"  # default
                focus = None
                model_id = "anthropic.claude-3-haiku-20240307-v1:0"  # default
                
                if "body" in event and event["body"]:
                    try:
                        body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
                        summary_length = body.get("summary_length", summary_length)
                        focus = body.get("focus")
                        model_id = body.get("model_id", model_id)
                    except Exception:
                        pass
                else:
                    summary_length = event.get("summary_length", summary_length)
                    focus = event.get("focus")
                    model_id = event.get("model_id", model_id)
                
                # Create document first to get structured text
                try:
                    document = create_document(url, html, chunk_size=1000, overlap=200, parse_snippet_max=parse_max)
                except Exception as exc:
                    return _proxy_response(500, {"error": "failed to create document", "detail": str(exc)})

                # Summarize the document
                try:
                    summarized_doc = summarize_document(
                        document=document,
                        model_id=model_id,
                        summary_length=summary_length,
                        focus=focus
                    )
                except Exception as exc:
                    return _proxy_response(500, {"error": "failed to summarize document", "detail": str(exc)})

                # Check for summarization errors
                summary_meta = summarized_doc.get("summary_metadata", {})
                if summary_meta.get("error"):
                    return _proxy_response(502, {
                        "error": "summarization failed",
                        "detail": summary_meta["error"],
                        "url": url
                    })

                # Return summary response
                response_data = {
                    "url": url,
                    "title": summarized_doc.get("title", ""),
                    "summary": summarized_doc.get("summary", ""),
                    "summary_metadata": summary_meta
                }

                # If full fetch included resources, attach counts
                if want_full and isinstance(fetched, dict):
                    resources = fetched.get("resources", {})
                    failed = fetched.get("failed", [])
                    response_data["resource_count"] = len(resources)
                    response_data["failed_resources"] = failed

                return _proxy_response(200, response_data)

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
