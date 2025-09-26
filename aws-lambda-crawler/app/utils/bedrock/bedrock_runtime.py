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

_DEFAULT_PROMPT = """
    Summarize the following text into exactly 3 main bullet points:
    - Each bullet point must be no longer than 100 words.
    - Focus only on the core ideas, avoid minor details or repetition.
    - Return the output as plain text bullets.

    Text:\n
"""
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
        logger.error(f"Couldn't list foundation models. {ex}")
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
            # Try a minimal request to test access
            body = json.dumps({
                "inputText": "test",
                "textGenerationConfig": {
                    "maxTokenCount": 10,
                    "temperature": 0.1
                }
            })
            
            bedrock_client.invoke_model(
                modelId=model_id,
                body=body,
                contentType="application/json",
                accept="application/json"
            )
            accessible_models.append(model_id)
            logger.info(f"✓ Model {model_id} is accessible")
            
        except ClientError as ex:
            error_code = ex.response.get('Error', {}).get('Code', 'Unknown')
            logger.warning(f"✗ Model {model_id} not accessible: {error_code}")
        except Exception as ex:
            logger.warning(f"✗ Model {model_id} test failed: {str(ex)}")
    
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

    body = json.dumps({
        "inputText": _DEFAULT_PROMPT + content_page + media_block,
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
            error_code = ex.response.get('Error', {}).get('Code', 'Unknown')
            logger.warning(f"Model {try_model} failed with {error_code}: {str(ex)}")
            
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
    region = os.environ.get("REGION", "us-east-1")
    bedrock_client = boto3.client(service_name="bedrock-runtime", region_name=region)


initialize()