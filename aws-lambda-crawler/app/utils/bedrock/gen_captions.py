import os
import json
import base64
import mimetypes
from typing import List, Dict, Tuple, Optional
import concurrent.futures as cf

import boto3
from botocore.exceptions import BotoCoreError, ClientError
import urllib.request
from urllib.error import URLError, HTTPError
# --- Config ---
BEDROCK_REGION = os.getenv("REGION", "ap-southeast-2")
# Allow overriding the Claude model via env var. If not provided, try a list
# of commonly available multimodal Claude IDs in order of preference.
CLAUDE_MODEL_ENV = os.getenv("CLAUDE_MODEL_ID")
# Allow using an inference profile ARN (preferred for some Claude 3.5 variants)
CLAUDE_INFERENCE_PROFILE = os.getenv("CLAUDE_INFERENCE_PROFILE_ARN")
CLAUDE_MODEL_CANDIDATES = [
    # Try the inference-profile ARN first when available (Bedrock accepts
    # an inference profile ARN in the modelId parameter for invoke_model).
    CLAUDE_INFERENCE_PROFILE,
    # Try safer Claude models that don't require inference profiles
    "anthropic.claude-3-haiku-20240307-v1:0",
    "anthropic.claude-3-sonnet-20240229-v1:0",
    # Only try user-specified model if different from problematic one
    CLAUDE_MODEL_ENV if CLAUDE_MODEL_ENV != "anthropic.claude-3-5-sonnet-20240620-v1:0" else None,
    # Keep the problematic model last as a fallback (will likely fail without inference profile)
    "anthropic.claude-3-5-sonnet-20240620-v1:0",  # Claude 3.5 Sonnet (requires inference profile)
]

session = boto3.Session(region_name=BEDROCK_REGION)
s3 = session.client("s3")
runtime = session.client("bedrock-runtime")


# --- Helpers ---
def parse_s3_uri(s3_uri: str) -> Tuple[str, str]:
    if not s3_uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    _, _, rest = s3_uri.partition("s3://")
    bucket, _, key = rest.partition("/")
    if not bucket or not key:
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    return bucket, key


def s3_image_to_base64_and_type(s3_uri: str) -> Tuple[str, str]:
    """Download image from S3, return (base64, media_type)."""
    # Support both s3:// URIs and presigned HTTP(S) URLs
    data = None
    content_type = ""
    try:
        if s3_uri.startswith("s3://"):
            bucket, key = parse_s3_uri(s3_uri)
            try:
                # Try to get ContentType from head
                head = s3.head_object(Bucket=bucket, Key=key)
                content_type = head.get("ContentType") or ""
            except ClientError:
                content_type = ""

            # Fallback: guess from file extension
            if not content_type or content_type == "binary/octet-stream":
                guessed, _ = mimetypes.guess_type(key)
                if guessed:
                    content_type = guessed

            # Read the file from S3
            obj = s3.get_object(Bucket=bucket, Key=key)
            data = obj["Body"].read()
        elif s3_uri.startswith("http://") or s3_uri.startswith("https://"):
            # Fetch via HTTP(S) (presigned URL or public URL)
            try:
                with urllib.request.urlopen(s3_uri) as resp:
                    # resp.info() is a mapping-like of headers
                    ct = resp.info().get_content_type()
                    if ct:
                        content_type = ct
                    data = resp.read()
            except (HTTPError, URLError) as e:
                raise ValueError(f"Failed to fetch URL {s3_uri}: {e}")
        else:
            raise ValueError(f"Unsupported URI scheme for image: {s3_uri}")
    except Exception:
        # Re-raise to be handled by caller
        raise
    b64 = base64.b64encode(data).decode("utf-8")

    # Normalize common types for Claude
    if not content_type:
        # default to png
        content_type = "image/png"

    return b64, content_type


def build_prompt(mode: str = "caption") -> str:
    """
    mode = "caption"  ≤ 15 words
    mode = "title"    ≤ 8 words
    """
    if mode == "title":
        return (
            "You are a helpful assistant.\n"
            "Provide a concise, catchy TITLE for the image in no more than 8 words.\n"
            "Do not include quotes or extra punctuation.\n"
        )
    # default caption
    return (
        "You are a helpful assistant.\n"
        "Provide a concise CAPTION for the image in no more than 15 words.\n"
        "Avoid emojis and quotes. Keep it descriptive and natural.\n"
    )


def claude_caption_single(image_b64: str, media_type: str, mode: str = "caption", max_tokens: int = 120) -> str:
    prompt = build_prompt(mode)
    body_template = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
                ],
            }
        ],
    }

    last_exc = None
    for candidate in CLAUDE_MODEL_CANDIDATES:
        if not candidate:
            continue
        print(f"Trying Claude model candidate: {candidate}")
        try:
            resp = runtime.invoke_model(
                modelId=candidate,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body_template),
            )
            out = json.loads(resp["body"].read())
            text = out["content"][0]["text"].strip()
            # sanitize a bit: remove surrounding quotes if LLM adds them
            if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
                text = text[1:-1].strip()
            print(f"✓ Successfully used Claude model: {candidate}")
            return text
        except ClientError as ex:
            last_exc = ex
            # If model requires an inference profile, try the next candidate
            err = getattr(ex, 'response', {}) or {}
            code = err.get('Error', {}).get('Code') if isinstance(err, dict) else None
            msg = str(ex)
            if code == 'ValidationException' and ('inference profile' in msg or 'Invocation of model ID' in msg):
                print(f"⚠️ Model {candidate} requires inference profile, trying next candidate")
                # try next candidate
                continue
            # For other client errors, also try next candidate
            print(f"✗ Model {candidate} failed: {code} - {msg}")
            continue
    # If we exhausted candidates, raise the last exception
    if last_exc:
        raise last_exc
    raise RuntimeError("No Claude model candidates configured")
    # sanitize a bit: remove surrounding quotes if LLM adds them
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()
    return text


def caption_or_title_for_s3_image(s3_uri: str, mode: str = "caption") -> Dict[str, str]:
    """Process a single image S3 URI and return dict with result."""
    print(f"[caption] Starting {mode} for: {s3_uri}")
    try:
        b64, media_type = s3_image_to_base64_and_type(s3_uri)
        # b64 length gives an approximate size indicator
        print(f"[caption] Fetched {s3_uri}: media_type={media_type} base64_len={len(b64)}")
        result = claude_caption_single(b64, media_type, mode=mode)
        # Log a preview of the generated text
        preview = result[:200] + "..." if isinstance(result, str) and len(result) > 200 else result
        print(f"[caption] SUCCESS {mode} for {s3_uri}: {preview}")
        return {"s3_uri": s3_uri, "result": result, "mode": mode}
    except (BotoCoreError, ClientError, ValueError) as e:
        print(f"[caption] FETCH/CLIENT error for {s3_uri}: {e}")
        return {"s3_uri": s3_uri, "error": str(e), "mode": mode}
    except Exception as ex:
        print(f"[caption] Unexpected error for {s3_uri}: {ex}")
        return {"s3_uri": s3_uri, "error": str(ex), "mode": mode}


def batch_caption_s3_images(
    s3_uris: List[str],
    mode: str = "caption",
    max_workers: int = 2
) -> List[Dict[str, str]]:
    """
    Process a list of s3:// URIs concurrently.
    mode: "caption" or "title"
    Returns list of dicts in the SAME ORDER as input.
    """
    # We want to preserve order; map futures to index
    results: List[Optional[Dict[str, str]]] = [None] * len(s3_uris)
    print(f"[batch_caption] Starting batch of {len(s3_uris)} images mode={mode} workers={max_workers}")
    with cf.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(caption_or_title_for_s3_image, s3_uri, mode): i
            for i, s3_uri in enumerate(s3_uris)
        }
        for fut in cf.as_completed(future_to_idx):
            idx = future_to_idx[fut]
            try:
                results[idx] = fut.result()
            except Exception as e:
                results[idx] = {"s3_uri": s3_uris[idx], "error": str(e), "mode": mode}
    # Log summary
    try:
        success = sum(1 for r in results if isinstance(r, dict) and r.get("result"))
        errors = sum(1 for r in results if isinstance(r, dict) and r.get("error"))
        print(f"[batch_caption] Completed: success={success} errors={errors} total={len(s3_uris)}")
    except Exception:
        pass
    return results


if __name__ == "__main__":
    images = [
        "s3://bytescribeteam/application_diagram.png",
        "s3://bytescribeteam/stepfuction-workflow.png",
    ]

    # 1) Get caption
    captions = batch_caption_s3_images(images, mode="caption", max_workers=4)
    print("\n------------ caption -------------")
    for caption in captions:
        print(caption)

    # 2) Get title
    titles = batch_caption_s3_images(images, mode="title", max_workers=4)
    print("\n------------ title -------------")
    for title in titles:
        print(title)