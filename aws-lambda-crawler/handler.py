import json

from crawler.fetcher import fetch_html, fetch_all_content
from crawler.parser import parse_html
import traceback

# Import summarize_page from the local app module
try:
    from app.utils.bedrock.bedrock_runtime import summarize_page
except Exception as e:
    print(f"Warning: Could not import summarize_page: {e}")
    summarize_page = None
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

    # Check if this is a model access test request
    if isinstance(event, dict) and "body" in event and event["body"]:
        try:
            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
            if body.get("action") == "check_models":
                if summarize_page is not None:
                    try:
                        from app.utils.bedrock.bedrock_runtime import check_model_access
                        accessible_models = check_model_access()
                        return _proxy_response(200, {
                            "action": "check_models",
                            "accessible_models": accessible_models,
                            "total_accessible": len(accessible_models)
                        })
                    except Exception as exc:
                        return _proxy_response(500, {
                            "action": "check_models",
                            "error": str(exc),
                            "accessible_models": []
                        })
                else:
                    return _proxy_response(500, {
                        "action": "check_models", 
                        "error": "Bedrock integration not available"
                    })
        except Exception:
            pass  # Not a JSON body, continue with normal processing

    # Extract URL from API Gateway body or direct event
    url = None
    # Also build a dict of parsed body content for optional params
    body_dict = {}
    if isinstance(event, dict):
        if "body" in event and event["body"]:
            try:
                body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
            except Exception:
                return _proxy_response(400, {"error": "invalid JSON body"})
            url = body.get("url")
            body_dict = body or {}
        else:
            url = event.get("url")
            body_dict = event

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

    # If bedrock summarize_page is available, call it with the parsed text.
    # Allow callers to provide `model_id` and `text_config` in the request body.
    if summarize_page is not None:
        try:
            content_to_summary = parsed.get("text_snippet") or ""
            model_id = body_dict.get("model_id") if isinstance(body_dict, dict) else None
            text_config = body_dict.get("text_config") if isinstance(body_dict, dict) else None
            # Call with defaults when not provided
            kwargs = {}
            if model_id:
                kwargs["model_id"] = model_id
            if text_config and isinstance(text_config, dict):
                kwargs["text_config"] = text_config

            summary_resp = summarize_page(content_page=content_to_summary, **kwargs)
            # summary_resp is typically a dict like {"result": ...}
            response_payload["summary"] = summary_resp
        except Exception as exc:
            # Don't fail the whole request if summarization fails
            error_msg = str(exc)
            response_payload["summary_error"] = {
                "error": error_msg,
                "trace": traceback.format_exc(),
            }
            
            # Add helpful information for common errors
            if "AccessDeniedException" in error_msg:
                response_payload["summary_error"]["help"] = {
                    "message": "Model access not enabled. Enable model access in AWS Bedrock Console.",
                    "instructions": [
                        "1. Go to AWS Bedrock Console",
                        "2. Navigate to 'Model access' in sidebar",
                        "3. Click 'Request model access'", 
                        "4. Enable access for: amazon.titan-text-express-v1, anthropic.claude-3-haiku-20240307-v1:0",
                        "5. Wait for approval (usually instant for Titan models)"
                    ],
                    "console_url": "https://console.aws.amazon.com/bedrock/home#/modelaccess"
                }
    else:
        response_payload["summary_error"] = {
            "error": "Bedrock integration not available",
            "help": "summarize_page function could not be imported"
        }

    return _proxy_response(200, response_payload)
