import os
import json
import base64
import mimetypes
from typing import List, Dict, Tuple, Optional
import concurrent.futures as cf

import boto3
from botocore.exceptions import BotoCoreError, ClientError
# --- Config ---
BEDROCK_REGION = os.getenv("REGION", "us-east-1")
CLAUDE_MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"  # Claude 3.5 Sonnet (multimodal)

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

    # Read the file
    obj = s3.get_object(Bucket=bucket, Key=key)
    data = obj["Body"].read()
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
    body = {
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
    resp = runtime.invoke_model(
        modelId=CLAUDE_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    out = json.loads(resp["body"].read())
    text = out["content"][0]["text"].strip()
    # sanitize a bit: remove surrounding quotes if LLM adds them
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()
    return text


def caption_or_title_for_s3_image(s3_uri: str, mode: str = "caption") -> Dict[str, str]:
    """Process a single image S3 URI and return dict with result."""
    try:
        b64, media_type = s3_image_to_base64_and_type(s3_uri)
        result = claude_caption_single(b64, media_type, mode=mode)
        return {"s3_uri": s3_uri, "result": result, "mode": mode}
    except (BotoCoreError, ClientError, ValueError) as e:
        return {"s3_uri": s3_uri, "error": str(e), "mode": mode}


def batch_caption_s3_images(
    s3_uris: List[str],
    mode: str = "caption",
    max_workers: int = 4
) -> List[Dict[str, str]]:
    """
    Process a list of s3:// URIs concurrently.
    mode: "caption" or "title"
    Returns list of dicts in the SAME ORDER as input.
    """
    # We want to preserve order; map futures to index
    results: List[Optional[Dict[str, str]]] = [None] * len(s3_uris)
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
    # type: ignore
    return results  # type: ignore


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
