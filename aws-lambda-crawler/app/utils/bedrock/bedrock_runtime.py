"""
Lists the available Amazon Bedrock models.
"""
import logging
import json
import boto3
import os

from botocore.exceptions import ClientError
from app.constants import (
    BEDROCK_MODEL_AWS_TITANT,
    BEDROCK_MODEL_ANTHROPIC_CLAUDE35
)
from app.core.config import settings
from .gen_captions import batch_caption_s3_images

# Allow overriding with inference profile ARN for models that require it
CLAUDE_INFERENCE_PROFILE = os.environ.get("CLAUDE_INFERENCE_PROFILE_ARN")
_CAPTION_MODE = "caption"
_TITLE_MODE = "title"
_DEFAULT_PROMPT = """
    Summarize the following text into exactly {num_bullets} main bullet points:
    - Each bullet point must be no longer than {max_words_per_bullet} words.
    - Focus only on the core ideas, avoid minor details or repetition.
    - Return the output as plain text bullets.

    Text:\n
"""

# Module-level default for number of bullets
DEFAULT_NUM_BULLETS = 3
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def list_foundation_models():
    """
    Gets a list of available Amazon Bedrock foundation models.

    :return: The list of available bedrock foundation models.
    """

    try:
        response = bedrock_client.list_foundation_models()
        fm_models = response["modelSummaries"]
        logger.info("Got %s foundation models.", len(fm_models))
        for model in fm_models:
            print(f"Model: {model['modelName']}")
            print(json.dumps(model, indent=2))
            print("---------------------------\n")

        logger.info("Done.")
        return fm_models

    except ClientError as ex:
        err = ex.response.get('Error', {}) if hasattr(ex, 'response') else {}
        logger.error(f"Couldn't list foundation models. Code={err.get('Code')} Message={err.get('Message')}")
        logger.debug("Full ClientError response: %s", getattr(ex, 'response', str(ex)))
        raise


def check_model_access():
    """
    Check which models are accessible by trying to list them.
    
    :return: List of accessible model IDs
    """
    accessible_models = []
    test_models = [
        "amazon.titan-text-express-v1",
        "amazon.titan-text-lite-v1",
        "anthropic.claude-3-haiku-20240307-v1:0",
        "anthropic.claude-3-sonnet-20240229-v1:0",
        "anthropic.claude-3-5-sonnet-20240620-v1:0",
    ]
    
    for model_id in test_models:
        try:
            # Build a minimal request that matches the model's expected schema.
            # Anthropic/Claude models expect a `messages` array, while Titan
            # models expect an `inputText` + `textGenerationConfig`.
            if "anthropic" in (model_id or "") or "claude" in (model_id or ""):
                body_obj = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 10,
                    "temperature": 0.1,
                    "messages": [{"role": "user", "content": "test"}],
                }
            else:
                body_obj = {
                    "inputText": "test",
                    "textGenerationConfig": {"maxTokenCount": 10, "temperature": 0.1},
                }

            bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(body_obj),
                contentType="application/json",
                accept="application/json",
            )
            accessible_models.append(model_id)
            logger.info(f"✓ Model {model_id} is accessible")

        except ClientError as ex:
            err = ex.response.get('Error', {}) if hasattr(ex, 'response') else {}
            error_code = err.get('Code', 'Unknown')
            # Keep the message but avoid confusing ValidationExceptions caused
            # by using the wrong request schema when probing models.
            logger.warning(f"✗ Model {model_id} not accessible: {error_code} Message={err.get('Message')}")
            logger.debug("ClientError response for model %s: %s", model_id, getattr(ex, 'response', str(ex)))
        except Exception as ex:
            logger.warning(f"✗ Model {model_id} test failed: {str(ex)}")
    
    # If an inference profile ARN is configured for Claude models, try invoking it
    # as well. Many Anthropic/Claude 3.5 variants require invocation via an
    # inference profile ARN rather than the raw model ID; probing the ARN lets
    # us report the downstream model as accessible to UI clients.
    try:
        if CLAUDE_INFERENCE_PROFILE:
            try:
                logger.info(f"Probing inference profile ARN: {CLAUDE_INFERENCE_PROFILE}")
                # Use an Anthropic/Claude-style minimal probe body
                probe_body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 5,
                    "temperature": 0.1,
                    "messages": [{"role": "user", "content": "test"}],
                })
                bedrock_client.invoke_model(
                    modelId=CLAUDE_INFERENCE_PROFILE,
                    body=probe_body,
                    contentType="application/json",
                    accept="application/json",
                )
                # If invocation succeeded, surface the known Claude 3.5 model id
                if BEDROCK_MODEL_ANTHROPIC_CLAUDE35 not in accessible_models:
                    accessible_models.append(BEDROCK_MODEL_ANTHROPIC_CLAUDE35)
                    logger.info(f"✓ Inference profile probe succeeded; reporting {BEDROCK_MODEL_ANTHROPIC_CLAUDE35} as accessible")
            except Exception as ex:
                logger.debug(f"Inference profile probe failed: {str(ex)}")
    except Exception:
        pass

    return accessible_models


def summarize_page(
    content_page="",
    text_config={},
    model_id=BEDROCK_MODEL_AWS_TITANT,
    media_refs=None,
):
    _TextGenerationConfig = {
        "maxTokenCount": 8192,
        "temperature": 0.7
    }

    # List of models to try in order of preference
    fallback_models = [
        model_id,  # Use the requested model first
        "amazon.titan-text-express-v1",
        "anthropic.claude-3-haiku-20240307-v1:0",
        "amazon.titan-text-lite-v1",
    ]
    
    # Remove duplicates while preserving order
    models_to_try = []
    seen = set()
    for model in fallback_models:
        if model not in seen:
            models_to_try.append(model)
            seen.add(model)

    # If media references were provided, build a small JSON block to append for structured context
    media_block = ""
    try:
        if media_refs:
            # Normalize media refs to only include useful keys
            normalized = []
            for m in media_refs:
                normalized.append({
                    "source_url": m.get("source_url"),
                    "presigned_url": m.get("presigned_url") or m.get("s3_url"),
                    "s3_key": m.get("s3_key"),
                    "alt": m.get("alt"),
                    "title": m.get("title"),
                    "type": m.get("type"),
                })
            media_json = json.dumps(normalized, indent=2)
            media_block = f"\n\nAdditional media references (JSON):\n{media_json}\n"
    except Exception:
        media_block = ""

    # Resolve num_bullets from text_config only (no explicit arg)
    num_bullets = (text_config or {}).get('num_bullets', DEFAULT_NUM_BULLETS)
    body = json.dumps({
        "inputText": _DEFAULT_PROMPT.format(num_bullets=num_bullets, max_words_per_bullet=(text_config or {}).get('max_words_per_bullet', 100)) + content_page + media_block,
        "textGenerationConfig": {
            **_TextGenerationConfig,
            **text_config
        }
    })

    last_error = None
    
    for try_model in models_to_try:
        try:
            logger.info(f"Attempting to use model: {try_model}")
            resp = bedrock_client.invoke_model(
                modelId=try_model,
                body=body,
                contentType="application/json",
                accept="application/json"
            )
            
            output = json.loads(resp["body"].read())
            results = output.get("results", [])
            
            if settings.DEBUG:
                print(json.dumps(output, indent=4))
                for idx, result in enumerate(results):
                    print(f"---> Result {idx}:", result.get("outputText", ""))

            # If we get here, the model worked
            logger.info(f"Successfully used model: {try_model}")
            return {"result": results[0] if results else {}, "model_used": try_model}
            
        except ClientError as ex:
            last_error = ex
            err = ex.response.get('Error', {}) if hasattr(ex, 'response') else {}
            error_code = err.get('Code', 'Unknown')
            logger.warning(f"Model {try_model} failed with {error_code}: {err.get('Message')} - {str(ex)}")
            logger.debug("Full ClientError response for model %s: %s", try_model, getattr(ex, 'response', str(ex)))
            
            # If it's an access denied error, try the next model
            if error_code == 'AccessDeniedException':
                continue
            else:
                # For other errors, don't try more models
                break
        except Exception as ex:
            last_error = ex
            logger.warning(f"Model {try_model} failed with unexpected error: {str(ex)}")
            continue
    
    # If we get here, all models failed
    logger.error(f"All models failed. Last error: {str(last_error)}")
    raise last_error


def initialize():
    global bedrock_client
    region = os.environ.get("REGION", "ap-southeast-2")
    bedrock_client = boto3.client(service_name="bedrock-runtime", region_name=region)


initialize()


def summarize_and_select_images(article_text: str, images_json: list[dict], model_id: str = None, text_config: dict = None):
    """
    Summarize article into N bullets (configurable via text_config['num_bullets']) and select up to 3 matching images per bullet.

    Returns a list of bullet objects (may be empty on failure).
    """
    try:
        # ----------------------------------------
        # Generate suitable caption/title for each image (defensive)
        # Collect S3 URIs (skip missing ones but preserve order)
        s3_images = []
        idx_map = []  # maps caption index -> images_json index
        for i, image in enumerate(images_json):
            s3_uri = image.get("s3_url") or image.get("s3_uri") or image.get("presigned_url")
            if s3_uri:
                s3_images.append(s3_uri)
                idx_map.append(i)
            else:
                # Leave existing caption/title in place if present
                logger.debug(f"Image at index {i} has no s3_url/presigned_url; skipping caption generation")

        captions = []
        titles = []
        try:
            if s3_images:
                captions = batch_caption_s3_images(s3_images, _CAPTION_MODE)
                titles = batch_caption_s3_images(s3_images, _TITLE_MODE)
                # Log summary of caption/title generation for debugging
                try:
                    success_captions = sum(1 for c in captions if isinstance(c, dict) and c.get("result"))
                    success_titles = sum(1 for t in titles if isinstance(t, dict) and t.get("result"))
                    logger.info(f"Generated captions: {success_captions}/{len(s3_images)}, titles: {success_titles}/{len(s3_images)}")
                    # Log per-image status (truncate long text)
                    for k, s3 in enumerate(s3_images):
                        cap = captions[k] if k < len(captions) else None
                        tit = titles[k] if k < len(titles) else None
                        cap_ok = isinstance(cap, dict) and cap.get("result")
                        tit_ok = isinstance(tit, dict) and tit.get("result")
                        cap_preview = (cap.get("result")[:200] + "...") if cap_ok and len(cap.get("result")) > 200 else (cap.get("result") if cap_ok else None)
                        tit_preview = (tit.get("result")[:200] + "...") if tit_ok and len(tit.get("result")) > 200 else (tit.get("result") if tit_ok else None)
                        logger.info(f"Caption/title for {s3}: caption_ok={bool(cap_ok)} title_ok={bool(tit_ok)} caption_preview={cap_preview} title_preview={tit_preview}")
                        # Also print debug lines to CloudWatch to help tracing
                        try:
                            print(json.dumps({
                                "s3": s3,
                                "caption_ok": bool(cap_ok),
                                "title_ok": bool(tit_ok),
                                "caption_preview": cap_preview,
                                "title_preview": tit_preview
                            }, ensure_ascii=False))
                        except Exception:
                            pass
                except Exception:
                    logger.debug("Failed to log caption/title summary", exc_info=True)
        except Exception as e:
            logger.warning(f"batch_caption_s3_images failed: {str(e)}")

        # Apply results back into images_json, being defensive about missing keys
        for j, orig_idx in enumerate(idx_map):
            cap_entry = captions[j] if j < len(captions) else None
            title_entry = titles[j] if j < len(titles) else None

            # caption
            caption_text = None
            if isinstance(cap_entry, dict) and cap_entry.get("result"):
                caption_text = cap_entry.get("result")
            elif isinstance(cap_entry, dict) and cap_entry.get("error"):
                logger.warning(f"Caption generation error for {cap_entry.get('s3_uri')}: {cap_entry.get('error')}")

            # title
            title_text = None
            if isinstance(title_entry, dict) and title_entry.get("result"):
                title_text = title_entry.get("result")
            elif isinstance(title_entry, dict) and title_entry.get("error"):
                logger.warning(f"Title generation error for {title_entry.get('s3_uri')}: {title_entry.get('error')}")

            # Fallbacks: keep existing values or empty string
            if caption_text is None:
                caption_text = images_json[orig_idx].get("caption") or ""
            if title_text is None:
                title_text = images_json[orig_idx].get("title") or ""

            images_json[orig_idx]["caption"] = caption_text
            images_json[orig_idx]["title"] = title_text
            images_json[orig_idx]["tags"] = images_json[orig_idx].get("tags", []) or []

        # ----------------------------------------
        # Allow callers to override the per-bullet max word count via text_config.
        # Supported keys (in order): max_words_per_bullet, max_words, max_word_count, max_words_each
        max_words_per_bullet = 60
        if isinstance(text_config, dict):
            for _k in ("max_words_per_bullet", "max_words", "max_word_count", "max_words_each"):
                if _k in text_config:
                    try:
                        v = int(text_config.get(_k))
                        if v > 0:
                            max_words_per_bullet = v
                            break
                    except Exception:
                        # ignore invalid values and keep default
                        pass

        # Resolve num_bullets from text_config only
        num_bullets = (text_config or {}).get('num_bullets', DEFAULT_NUM_BULLETS)

        prompt = f"""You are given a long article and a list of candidate images (each includes title, caption/tags, and an S3 URL).
        Tasks:
        1) Produce {num_bullets} main bullet points summarizing the core ideas of the article (≤{max_words_per_bullet} words each, no overlap).
        2) For each bullet point, select at most three best-matching images from the provided list.
        3) If there are no suitable images, return empty images and do not invent images.
        4) Return a valid JSON object with this schema:
        {{
          "bullets": [
            {{
              "text": "<<= {max_words_per_bullet} words>>",
              "reason": "<<why this image fits, 1 sentence>>",
              "image_url": "<<a list of suitable provided images in s3 URLs>>"
            }}
          ]
        }}

        Important rules:
        - Base your image choice ONLY on the provided image titles/captions/tags (no external fetching).
        - Output JSON only. No markdown. No explanations outside JSON.

        ARTICLE:
        <<<
        {article_text}
        >>>

        IMAGES:
        <<<
        {json.dumps(images_json, ensure_ascii=False)}
        >>>
        """

        # We need to construct the request body according to the target model's
        # expected schema. Anthropic/Claude models accept a `messages` style
        # request (and optional "anthropic_version"/"max_tokens"), while
        # Amazon Titan models expect an `inputText` + `textGenerationConfig`.
        # Build per-model bodies inside the loop so we don't send the wrong
        # schema and trigger ValidationException (schema violations).

        # allow caller-provided model_id; otherwise use fallback list
        try_models = []
        if model_id:
            try_models.append(model_id)
        
        # Prefer inference profile ARN if set, otherwise use accessible models
        if CLAUDE_INFERENCE_PROFILE:
            try_models.append(CLAUDE_INFERENCE_PROFILE)
        
        # Add accessible models in order of preference (avoid the problematic 3.5 sonnet)  
        try_models.extend([
            "anthropic.claude-3-haiku-20240307-v1:0",
            "anthropic.claude-3-sonnet-20240229-v1:0", 
            "amazon.titan-text-express-v1",
            BEDROCK_MODEL_ANTHROPIC_CLAUDE35  # keep as last resort
        ])
        
        # Remove duplicates while preserving order
        seen = set()
        try_models = [m for m in try_models if m and m not in seen and not seen.add(m)]

        last_exc = None
        out = None
        for try_model in try_models:
            try:
                # Prepare a model-specific request body
                model_body = None
                # Merge caller-provided text_config into generated config when present
                cfg = {}
                if isinstance(text_config, dict):
                    cfg = text_config.copy()

                if "anthropic" in (try_model or "") or "claude" in (try_model or ""):
                    # Anthropic-style schema
                    model_body = {
                        "anthropic_version": cfg.get("anthropic_version", "bedrock-2023-05-31"),
                        "max_tokens": cfg.get("max_tokens") or cfg.get("max_tokens", cfg.get("maxTokenCount", 8192)),
                        "temperature": cfg.get("temperature", 0.2),
                        "messages": [
                            {"role": "user", "content": prompt}
                        ]
                    }
                else:
                    # Amazon Titan / generic Bedrock text schema
                    text_gen_cfg = {
                        "maxTokenCount": cfg.get("maxTokenCount", cfg.get("max_tokens", 8192)),
                        "temperature": cfg.get("temperature", 0.2)
                    }
                    model_body = {
                        "inputText": prompt,
                        "textGenerationConfig": text_gen_cfg
                    }

                # Log a truncated preview of the body to aid debugging schema issues
                try:
                    logger.debug(f"Invoking model {try_model} with request body preview: {json.dumps(model_body)[:1000]}")
                except Exception:
                    pass

                res = bedrock_client.invoke_model(
                    modelId=try_model,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(model_body)
                )
                out = json.loads(res["body"].read())
                break
            except ClientError as ex:
                last_exc = ex
                # Log detailed ClientError info for debugging ValidationExceptions
                err = ex.response.get('Error', {}) if hasattr(ex, 'response') else {}
                logger.warning(f"Model {try_model} ClientError: Code={err.get('Code')} Message={err.get('Message')}")
                logger.debug("Full ClientError response for model %s: %s", try_model, getattr(ex, 'response', str(ex)))

                # If validation mentions inference profile, try to discover accessible models
                msg = str(ex)
                if "inference profile" in msg or "Invocation of model ID" in msg:
                    try:
                        accessible = []
                        try:
                            accessible = check_model_access()
                        except Exception:
                            accessible = []
                        # try accessible models not already attempted
                        for m in accessible:
                            if m in try_models:
                                continue
                            try:
                                # Build body for the accessible model as well
                                model_body = None
                                if "anthropic" in (m or "") or "claude" in (m or ""):
                                    model_body = {
                                        "anthropic_version": (text_config or {}).get("anthropic_version", "bedrock-2023-05-31"),
                                        "max_tokens": (text_config or {}).get("max_tokens", (text_config or {}).get("maxTokenCount", 8192)),
                                        "temperature": (text_config or {}).get("temperature", 0.2),
                                        "messages": [{"role": "user", "content": prompt}]
                                    }
                                else:
                                    text_gen_cfg = {
                                        "maxTokenCount": (text_config or {}).get("maxTokenCount", (text_config or {}).get("max_tokens", 8192)),
                                        "temperature": (text_config or {}).get("temperature", 0.2)
                                    }
                                    model_body = {"inputText": prompt, "textGenerationConfig": text_gen_cfg}

                                res = bedrock_client.invoke_model(
                                    modelId=m,
                                    contentType="application/json",
                                    accept="application/json",
                                    body=json.dumps(model_body)
                                )
                                out = json.loads(res["body"].read())
                                try_model = m
                                last_exc = None
                                break
                            except Exception as inner_ex:
                                last_exc = inner_ex
                        if last_exc is None:
                            break
                    except Exception:
                        pass
                # otherwise continue to next try_model
                continue
        else:
            # if loop completes without break, handle last exception
            if last_exc:
                # If this was a validation about inference profiles, return a structured error
                try:
                    err_code = last_exc.response.get('Error', {}).get('Code')
                    msg = str(last_exc)
                    if err_code == 'ValidationException' and ('inference profile' in msg or 'Invocation of model ID' in msg):
                        return {
                            "error": "ValidationException",
                            "message": msg,
                            "help": {
                                "message": "This model requires invoking via an inference profile or a different model ID/ARN that is enabled for on-demand throughput.",
                                "instructions": [
                                    "Check AWS Bedrock Console > Inference profiles and create/enable an inference profile containing the model.",
                                    "Alternatively, use check_model_access() to see accessible models and select one of those model IDs.",
                                ]
                            }
                        }
                except Exception:
                    pass
                raise last_exc
        # bedrock may return text in out['content'][0]['text'] as a JSON string
        content_arr = out.get("content") or []

        # If no content was returned by the model, try the simpler
        # summarize_page path as a fallback (this uses the alternate
        # Titan/text schema and may succeed where the current call failed).
        if not content_arr:
            logger.warning("No content returned from model in summarize_and_select_images; attempting summarize_page fallback")
            try:
                sp_resp = summarize_page(content_page=article_text, text_config=text_config or {}, model_id=model_id)
                # sp_resp is typically {"result": {...}, "model_used": ...}
                if isinstance(sp_resp, dict):
                    # Try to extract output text from result or top-level
                    result_obj = sp_resp.get("result") or {}
                    # result_obj may contain 'outputText' or 'outputTextArray'
                    if isinstance(result_obj, dict):
                        text_field = result_obj.get("outputText") or ""
                    else:
                        text_field = sp_resp.get("outputText") or ""
                else:
                    text_field = ""
                # If summarize_page returned nothing useful, give up
                if not text_field:
                    return []
            except Exception as sp_ex:
                logger.warning(f"summarize_page fallback failed: {str(sp_ex)}")
                return []

        else:
            text_field = content_arr[0].get("text", "")
        # Try to parse the text as JSON, but be defensive
        def _enrich_bullets(bullets_list, images_list):
            if not isinstance(bullets_list, list):
                return bullets_list
            try:
                # build quick index by possible url keys
                idx_map = {}
                for img in images_list or []:
                    # prefer s3_url, then presigned_url, then source_url
                    for key in ("s3_url", "presigned_url", "source_url"):
                        val = img.get(key)
                        if val:
                            idx_map[val] = img

                enriched = []
                for b in bullets_list:
                    try:
                        if not isinstance(b, dict):
                            enriched.append(b)
                            continue
                        imgs = b.get("image_url")
                        if not imgs:
                            enriched.append(b)
                            continue
                        # normalize to list
                        if isinstance(imgs, str):
                            imgs_list = [imgs]
                        elif isinstance(imgs, list):
                            imgs_list = imgs
                        else:
                            enriched.append(b)
                            continue

                        new_imgs = []
                        for u in imgs_list:
                            if not isinstance(u, str):
                                new_imgs.append(u)
                                continue
                            meta = idx_map.get(u)
                            if meta:
                                new_imgs.append({
                                    "image_url": u,
                                    "title": meta.get("title") or None,
                                    "caption": meta.get("caption") or None,
                                    "tags": meta.get("tags") or [],
                                })
                            else:
                                # fallback: include original URL string
                                new_imgs.append({"image_url": u})

                        nb = dict(b)
                        nb["image_url"] = new_imgs
                        enriched.append(nb)
                    except Exception:
                        enriched.append(b)
                return enriched
            except Exception:
                return bullets_list

        try:
            parsed = json.loads(text_field)
            bullets = parsed.get("bullets", [])
            return _enrich_bullets(bullets, images_json)
        except Exception:
            # If text_field itself isn't JSON, try to extract inline JSON from it
            try:
                # find first `{` and last `}`
                start = text_field.find("{")
                end = text_field.rfind("}")
                if start != -1 and end != -1 and end > start:
                    candidate = text_field[start:end+1]
                    parsed = json.loads(candidate)
                    bullets = parsed.get("bullets", [])
                    return _enrich_bullets(bullets, images_json)
            except Exception:
                pass

        return []
    except Exception as ex:
        logger.error(f"summarize_and_select_images failed: {str(ex)}")
        return []