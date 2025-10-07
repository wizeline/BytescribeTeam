import json

from crawler.fetcher import fetch_html, fetch_all_content
from crawler.parser import parse_html
import traceback

# Import Bedrock helper functions from the local app module
try:
    from app.utils.bedrock.bedrock_runtime import summarize_and_select_images, summarize_page
except Exception as e:
    print(f"Warning: Could not import bedrock helpers: {e}")
    summarize_and_select_images = None
    summarize_page = None
import os
import hashlib
import boto3
import mimetypes
from urllib.parse import urlparse, unquote
from botocore.exceptions import ClientError
from botocore.config import Config as BotoConfig


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


def _detect_content_type_from_bytes(data: bytes) -> str:
    """Detect content type from magic bytes (file signature)."""
    if not data or len(data) < 12:
        return None
    
    # JPEG
    if data[:2] == b'\xff\xd8':
        return 'image/jpeg'
    # PNG
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png'
    # GIF
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return 'image/gif'
    # WebP (RIFF....WEBP)
    if data[8:12] == b'WEBP':
        return 'image/webp'
    # BMP
    if data[:2] == b'BM':
        return 'image/bmp'
    # SVG (starts with < or whitespace then <)
    try:
        text_start = data[:100].decode('utf-8', errors='ignore').lstrip()
        if text_start.startswith('<svg') or text_start.startswith('<?xml'):
            return 'image/svg+xml'
    except:
        pass
    # ICO
    if data[:4] == b'\x00\x00\x01\x00':
        return 'image/x-icon'
    
    return None


def _process_async_job(event, context):
    """Process an async job in the background"""
    try:
        body_str = event.get("body", "{}")
        job_data = json.loads(body_str)
        
        job_id = job_data["job_id"]
        content_to_summary = job_data["content_to_summary"]
        images_json = job_data["images_json"]
        model_id = job_data.get("model_id")
        text_config = job_data.get("text_config")
        s3_bucket = job_data["s3_bucket"]
        media_refs = job_data.get("media_refs", [])
        response_payload = job_data["response_payload"]
        
        # Update job status
        region = os.getenv("REGION") or os.getenv("AWS_DEFAULT_REGION")
        s3_config = BotoConfig(signature_version="s3v4", region_name=region) if region else BotoConfig(signature_version="s3v4")
        s3_client = boto3.client("s3", config=s3_config)
        
        def update_job_status(status, progress=None, result=None, error=None):
            job_update = {
                "job_id": job_id,
                "status": status,
                "updated_at": context.aws_request_id if context else None,
            }
            if progress:
                job_update["progress"] = progress
            if result:
                job_update["result"] = result
            if error:
                job_update["error"] = error
                
            job_key = f"jobs/{job_id}.json"
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=job_key,
                Body=json.dumps(job_update),
                ContentType="application/json"
            )
        
        update_job_status("processing", "Generating captions and summary...")
        
        # Process the job using existing logic
        kwargs = {}
        if model_id:
            kwargs["model_id"] = model_id
        if text_config and isinstance(text_config, dict):
            kwargs["text_config"] = text_config
        if media_refs:
            kwargs["media_refs"] = media_refs
            
        # Run the summarization
        summary_resp = None
        if summarize_and_select_images is not None:
            summary_resp = summarize_and_select_images(
                article_text=content_to_summary,
                images_json=images_json,
                model_id=kwargs.get("model_id"),
                text_config=kwargs.get("text_config")
            )
        elif summarize_page is not None:
            summary_resp = summarize_page(content_page=content_to_summary, **kwargs)
        
        # Process summary response
        if isinstance(summary_resp, list):
            response_payload["summary"] = {"bullets": summary_resp}
        else:
            response_payload["summary"] = summary_resp
            
        # Convert outputText to array if needed
        try:
            if isinstance(summary_resp, dict):
                def _convert_output_to_array(obj: dict):
                    if not isinstance(obj, dict):
                        return
                    out = obj.get("outputText")
                    if isinstance(out, str):
                        obj["outputTextArray"] = [line.strip() for line in out.splitlines() if line.strip()]

                _convert_output_to_array(summary_resp)
                if isinstance(summary_resp.get("result"), dict):
                    _convert_output_to_array(summary_resp["result"])
        except Exception:
            pass
        
        # Mark job as completed
        update_job_status("completed", "Processing completed successfully", response_payload)
        
        return {"statusCode": 200, "body": json.dumps({"status": "job completed"})}
        
    except Exception as exc:
        # Mark job as failed
        try:
            update_job_status("failed", error=str(exc))
        except:
            pass
        return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}


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

    # Handle async job processing (background invocation)
    if isinstance(event, dict) and event.get("action") == "process_job":
        return _process_async_job(event, context)

    # Check if this is a model access test request or job status poll
    if isinstance(event, dict) and "body" in event and event["body"]:
        try:
            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]

            # If client wants to poll job status, handle early and return job JSON
            if body.get("action") == "job_status":
                job_id = body.get("job_id")
                if not job_id:
                    return _proxy_response(400, {"error": "missing job_id"})
                region = os.getenv("REGION") or os.getenv("AWS_DEFAULT_REGION")
                s3_config = BotoConfig(signature_version="s3v4", region_name=region) if region else BotoConfig(signature_version="s3v4")
                s3_client = boto3.client("s3", config=s3_config)
                s3_bucket = os.getenv("S3_UPLOAD_BUCKET") or os.getenv("BUCKET_NAME")
                if not s3_bucket:
                    return _proxy_response(500, {"error": "S3 upload bucket not configured"})
                try:
                    job_key = f"jobs/{job_id}.json"
                    result = s3_client.get_object(Bucket=s3_bucket, Key=job_key)
                    job_data = json.loads(result["Body"].read())
                    return _proxy_response(200, job_data)
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchKey':
                        return _proxy_response(404, {"error": "job not found", "job_id": job_id})
                    return _proxy_response(500, {"error": f"failed to get job status: {str(e)}"})

            # Model access checks and diagnostics
            if body.get("action") in ("check_models", "diagnostics"):
                # Consider Bedrock integration available if either helper is present
                if summarize_and_select_images is not None or summarize_page is not None:
                    try:
                        from app.utils.bedrock.bedrock_runtime import check_model_access
                        accessible_models = check_model_access()
                    except Exception as exc:
                        return _proxy_response(500, {
                            "action": body.get("action"),
                            "error": str(exc),
                            "accessible_models": []
                        })

                    # Return just the accessible models for check_models
                    if body.get("action") == "check_models":
                        return _proxy_response(200, {
                            "action": "check_models",
                            "accessible_models": accessible_models,
                            "total_accessible": len(accessible_models)
                        })

                    # diagnostics: include a few environment keys plus the accessible models
                    env = dict(os.environ)
                    interesting = {
                        "REGION": env.get("REGION") or env.get("AWS_DEFAULT_REGION"),
                        "CLAUDE_INFERENCE_PROFILE_ARN": env.get("CLAUDE_INFERENCE_PROFILE_ARN"),
                        "S3_UPLOAD_BUCKET": env.get("S3_UPLOAD_BUCKET") or env.get("BUCKET_NAME"),
                        "S3_UPLOAD_PREFIX": env.get("S3_UPLOAD_PREFIX"),
                    }
                    return _proxy_response(200, {
                        "action": "diagnostics",
                        "environment": interesting,
                        "accessible_models": accessible_models,
                        "total_accessible": len(accessible_models)
                    })
                else:
                    return _proxy_response(500, {
                        "action": body.get("action"), 
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

        # Extract resources unless explicitly disabled
        extract_resources = True
        if isinstance(body_dict, dict):
            extract_resources = body_dict.get("extract_resources", True)

        parsed = parse_html(
            html, 
            max_snippet_chars=parse_max, 
            full_text=want_full,
            extract_resources=extract_resources,
            base_url=url
        )
    except Exception as exc:
        return _proxy_response(500, {"error": "failed to parse html", "detail": str(exc)})

    response_payload = {"url": url, **parsed}
    if want_full and isinstance(fetched, dict):
        resources = fetched.get("resources", {})
        failed = fetched.get("failed", [])
        response_payload["resource_count"] = len(resources)
        response_payload["failed_resources"] = failed

    # Check if this is an async job status request
    if isinstance(body_dict, dict) and body_dict.get("action") == "job_status":
        job_id = body_dict.get("job_id")
        if not job_id:
            return _proxy_response(400, {"error": "missing job_id"})
        
        # Check job status in S3
        try:
            s3_client = boto3.client("s3", config=s3_config)
            job_key = f"jobs/{job_id}.json"
            result = s3_client.get_object(Bucket=s3_bucket, Key=job_key)
            job_data = json.loads(result["Body"].read())
            return _proxy_response(200, job_data)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return _proxy_response(404, {"error": "job not found", "job_id": job_id})
            return _proxy_response(500, {"error": f"failed to get job status: {str(e)}"})

    # Check if async processing is requested
    async_mode = isinstance(body_dict, dict) and body_dict.get("async", False)
    
    # If any Bedrock summarization helper is available, call it with the parsed text.
    # Allow callers to provide `model_id` and `text_config` in the request body.
    if summarize_and_select_images is not None or summarize_page is not None:
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

            # If fetched resources exist, attempt to upload media (images/videos) to S3
            media_refs = []
            # ensure these are defined even if the upload attempt fails
            s3_bucket = None
            s3_prefix = ""
            try:
                # Determine bucket and optional prefix from environment
                s3_bucket = os.getenv("S3_UPLOAD_BUCKET") or os.getenv("BUCKET_NAME")
                s3_prefix = os.getenv("S3_UPLOAD_PREFIX", "")

                # Helper to upload bytes to S3 and return an https URL
                # Create the S3 client with explicit SigV4 signing and the
                # current region so generated presigned URLs include the
                # correct regional endpoint / signature format.
                region = os.getenv("REGION") or os.getenv("AWS_DEFAULT_REGION")
                s3_config = BotoConfig(signature_version="s3v4", region_name=region) if region else BotoConfig(signature_version="s3v4")
                s3_client = boto3.client("s3", config=s3_config)

                def _upload_to_s3(key: str, data: bytes, content_type: str = None):
                    """Upload bytes to S3 and return a dict with upload_key and presigned_url (or None on failure)."""
                    upload_key = f"{s3_prefix.rstrip('/')}/{key}".lstrip('/') if s3_prefix else key
                    try:
                        # Build put_object kwargs - ACL may fail on buckets with BPA enabled
                        put_kwargs = {"Bucket": s3_bucket, "Key": upload_key, "Body": data}
                        if content_type:
                            put_kwargs["ContentType"] = content_type
                        # Try with ACL first, fallback without it if bucket blocks ACLs
                        try:
                            s3_client.put_object(**put_kwargs, ACL="private")
                        except ClientError as acl_err:
                            # If ACL is not supported (BucketOwnerEnforced), retry without it
                            if "AccessControlListNotSupported" in str(acl_err):
                                s3_client.put_object(**put_kwargs)
                            else:
                                raise

                        # Generate a presigned GET URL so downstream consumers can fetch the object
                        expires = int(os.getenv("S3_PRESIGNED_EXPIRES", "3600"))
                        # Include ResponseContentType in presigned URL to ensure browser gets correct MIME type
                        presign_params = {"Bucket": s3_bucket, "Key": upload_key}
                        if content_type:
                            presign_params["ResponseContentType"] = content_type
                        presigned = s3_client.generate_presigned_url(
                            "get_object",
                            Params=presign_params,
                            ExpiresIn=expires,
                        )
                        # Emit a debug line so CloudWatch logs show the key,
                        # guessed content type and the presigned URL for
                        # troubleshooting in environments where images do
                        # not render in the client.
                        print(f"S3 uploaded: {upload_key} size={len(data)} bytes content_type={content_type} presigned={presigned[:100]}...")
                        # Also log first few bytes as hex for debugging corruption
                        print(f"  First 16 bytes (hex): {data[:16].hex() if len(data) >= 16 else data.hex()}")
                        return {"upload_key": upload_key, "presigned_url": presigned}
                    except ClientError as exc:
                        print(f"S3 upload or presign failed for {upload_key}: {exc}")
                        return None

                # Only upload if bucket configured and we have resource bytes
                if s3_bucket and isinstance(fetched, dict):
                    resources = fetched.get("resources", {})
                    # Upload each resource keyed by sha256 of url + basename
                    for url_res, data in resources.items():
                        if not data:
                            continue
                        # Ensure data is bytes (not string) - this is critical for binary files like images
                        if not isinstance(data, bytes):
                            print(f"WARNING: Resource {url_res} is not bytes, type={type(data)}, skipping upload")
                            continue
                        
                        # DEBUG: Log what we're about to upload
                        print(f"Processing resource: {url_res}")
                        print(f"  Size: {len(data)} bytes")
                        print(f"  First 16 bytes: {data[:16].hex() if len(data) >= 16 else data.hex()}")
                        
                        # Create a stable key name. Use the path portion of the
                        # source URL (drop query string and fragment) and
                        # decode percent-encodings. This avoids producing S3
                        # object keys that contain '?' or '&' which later
                        # confuse presigned URL generation / usage.
                        parsed_name = urlparse(url_res).path.split("/")[-1] or "resource"
                        parsed_name = unquote(parsed_name)
                        sha = hashlib.sha256(url_res.encode("utf-8")).hexdigest()[:10]
                        key = f"{sha}_{parsed_name}"
                        # Try to guess a sensible Content-Type for the object
                        content_type = mimetypes.guess_type(parsed_name)[0]
                        # If mimetypes couldn't guess, try to detect from magic bytes
                        if not content_type:
                            content_type = _detect_content_type_from_bytes(data)
                        # Final fallback for images
                        if not content_type and any(ext in parsed_name.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']):
                            # Default to jpeg if filename suggests image but type detection failed
                            content_type = 'image/jpeg'
                        uploaded = _upload_to_s3(key, data, content_type=content_type)
                        if uploaded:
                            media_refs.append({
                                "source_url": url_res,
                                "s3_key": uploaded.get("upload_key"),
                                "presigned_url": uploaded.get("presigned_url")
                            })

                    # Also include images and videos parsed from the HTML (may be duplicates)
                    for img in parsed.get("images", []) or []:
                        src = img.get("src")
                        # find matching uploaded entry
                        match = next((m for m in media_refs if m.get("source_url") == src), None)
                        if not match:
                            media_refs.append({
                                "source_url": src,
                                "presigned_url": None,
                                "alt": img.get("alt"),
                                "title": img.get("title"),
                            })
                    for vid in parsed.get("videos", []) or []:
                        for srcobj in vid.get("sources", []) or []:
                            src = srcobj.get("src")
                            match = next((m for m in media_refs if m.get("source_url") == src), None)
                            if not match:
                                media_refs.append({
                                    "source_url": src,
                                    "presigned_url": None,
                                    "type": srcobj.get("type")
                                })
            except Exception as exc:
                # Don't let S3 issues stop summarization; record in payload later
                print(f"S3 upload pass failed: {exc}")

            if media_refs:
                kwargs["media_refs"] = media_refs
                # Also expose the uploaded media list in the response so API clients can use presigned URLs
                response_payload["uploaded_media"] = media_refs

            # Build images_json now (used by summarization and needed for async jobs)
            images_json = []
            # Use media_refs (uploaded S3 objects / presigned URLs) first
            for m in (media_refs or []):
                img = {}
                if m.get("s3_key"):
                    img["s3_url"] = f"s3://{s3_bucket}/{m.get('s3_key')}" if s3_bucket and m.get('s3_key') else None
                    img["presigned_url"] = m.get("presigned_url")
                else:
                    img["source_url"] = m.get("source_url")
                img["title"] = m.get("title") or m.get("alt") or None
                img["caption"] = m.get("alt") or m.get("title") or None
                img["tags"] = m.get("tags") or []
                images_json.append(img)

            # Also include images/videos parsed directly from HTML that might not be uploaded
            for img in parsed.get("images", []) or []:
                images_json.append({
                    "title": img.get("title"),
                    "caption": img.get("alt") or img.get("caption"),
                    "tags": img.get("tags") or [],
                    "s3_url": None,
                    "source_url": img.get("src")
                })

            for vid in parsed.get("videos", []) or []:
                for srcobj in vid.get("sources", []) or []:
                    images_json.append({
                        "title": vid.get("title") or None,
                        "caption": vid.get("caption") or None,
                        "tags": [],
                        "s3_url": None,
                        "source_url": srcobj.get("src")
                    })

            # Expose the images_json in the immediate response payload so
            # clients (and tests) can see what was sent to the captioning
            # routine. Also log it to CloudWatch for troubleshooting.
            try:
                response_payload["images_json"] = images_json
                print(f"DEBUG images_json (first 3): {json.dumps(images_json[:3], ensure_ascii=False)}")
            except Exception:
                # If serialization fails for any reason, keep going silently
                print("DEBUG: failed to serialize images_json for log")

            # If async mode requested, start background job and return immediately
            if async_mode:
                import uuid
                job_id = str(uuid.uuid4())
                
                # Create initial job record
                job_data = {
                    "job_id": job_id,
                    "status": "processing",
                    "created_at": context.aws_request_id if context else None,
                    "url": url,
                    "progress": "Starting image analysis and summarization..."
                }
                
                # Save job status to S3
                try:
                    job_key = f"jobs/{job_id}.json"
                    s3_client.put_object(
                        Bucket=s3_bucket, 
                        Key=job_key, 
                        Body=json.dumps(job_data),
                        ContentType="application/json"
                    )
                    
                    # Invoke another Lambda asynchronously to process the job
                    lambda_client = boto3.client("lambda", region_name=region)
                    async_payload = {
                        "job_id": job_id,
                        "content_to_summary": content_to_summary,
                        "images_json": images_json,
                        "model_id": kwargs.get("model_id"),
                        "text_config": kwargs.get("text_config"),
                        "s3_bucket": s3_bucket,
                        "media_refs": media_refs,
                        "response_payload": response_payload
                    }
                    
                    lambda_client.invoke(
                        FunctionName=context.function_name if context else "aws-lambda-crawler",
                        InvocationType='Event',  # Async
                        Payload=json.dumps({
                            "action": "process_job",
                            "body": json.dumps(async_payload)
                        })
                    )
                    
                    return _proxy_response(202, {
                      "job_id": job_id,
                      "status": "processing",
                      "message": "AI-powered analysis and summarization in progress. Check back soon for your enhanced content and insights.",
                      "basic_content": response_payload  # Return basic content immediately
                    })
                    
                except Exception as e:
                    return _proxy_response(500, {"error": f"Failed to start async job: {str(e)}"})

            # Prefer the newer summarize_and_select_images API which accepts
            # the article text and a list of image metadata. Build images_json
            # from uploaded media, parsed images and videos. Fall back to the
            # original summarize_page when the newer function is unavailable.
            summary_resp = None
            try:
                # summarize_and_select_images expects images_json which was
                # constructed earlier (and included in the async payload when
                # async mode is used). Use the existing images_json variable.
                if summarize_and_select_images is not None:
                    summary_resp = summarize_and_select_images(
                        article_text=content_to_summary,
                        images_json=images_json,
                        model_id=kwargs.get("model_id"),
                        text_config=kwargs.get("text_config")
                    )
                elif summarize_page is not None:
                    summary_resp = summarize_page(content_page=content_to_summary, **kwargs)
                else:
                    raise RuntimeError("No Bedrock summarization function available")
            except Exception:
                # If anything in the new path fails, try the fallback summarize_page
                if summary_resp is None and summarize_page is not None:
                    try:
                        summary_resp = summarize_page(content_page=content_to_summary, **kwargs)
                    except Exception:
                        raise
            # summary_resp is typically a dict like {"result": ...}
            # If the model returned an `outputText` string, convert it to an
            # array by splitting on newlines, trimming whitespace and removing
            # any empty lines. This makes it easier for clients to consume
            # list-like summaries.
            try:
                if isinstance(summary_resp, dict):
                    # helper to convert any dict's outputText string into a
                    # list of trimmed non-empty lines and store it under
                    # `outputTextArray` so we don't overwrite the original
                    # `outputText` field.
                    def _convert_output_to_array(obj: dict):
                        if not isinstance(obj, dict):
                            return
                        out = obj.get("outputText")
                        if isinstance(out, str):
                            obj["outputTextArray"] = [line.strip() for line in out.splitlines() if line.strip()]

                    # Convert top-level outputText if present
                    _convert_output_to_array(summary_resp)

                    # Also convert nested result.outputText when the model
                    # returns a `result` wrapper (common for some runtimes)
                    if isinstance(summary_resp.get("result"), dict):
                        _convert_output_to_array(summary_resp["result"])
            except Exception:
                # Be defensive: if something goes wrong transforming the
                # field, keep the original summary_resp unchanged.
                pass

            # Normalize summarize_and_select_images output (typically a list)
            if isinstance(summary_resp, list):
                response_payload["summary"] = {"bullets": summary_resp}
            else:
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
