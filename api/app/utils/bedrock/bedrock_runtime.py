
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


def summarize_page(
    content_page="",
    text_config={},
    model_id=BEDROCK_MODEL_AWS_TITANT
):
    _TextGenerationConfig = {
        "maxTokenCount": 8192,
        "temperature": 0.7
    }

    body = json.dumps({
        "inputText": _DEFAULT_PROMPT + content_page,
        "textGenerationConfig": {
            **_TextGenerationConfig,
            **text_config
        }
    })

    try:
        resp = bedrock_client.invoke_model(
            modelId=model_id,
            body=body,
            contentType="application/json",
            accept="application/json"
        )
    except ClientError as ex:
        logger.error(f"Couldn't invoke a model: {str(ex)}")
        raise

    output = json.loads(resp["body"].read())
    results = output.get("results", [])
    # --------------------------------------
    if settings.DEBUG:
        print(json.dumps(output, indent=4))
        for idx, result in enumerate(results):
            print(f"---> Result {idx}:", result.get("outputText", ""))

    return {"result": results[0] if results else {}}


def summarize_and_select_images(article_text: str, images_json: list[dict]):
    """
    - This function summarize the page basing on the `article_text` into 3 main bullets,
    then select at most 3 images from the `image_json` that is suitable for each bullet.

    - Parameters:
        * article_text: then full page content
        * images_json: the list of images that has title, caption, tags & s3_url as below
            sample_images = [
                {
                    "title": "Application diagram",
                    "caption": "How application works",
                    "tags": ["application", "diagram"],
                    "s3_url": "s3://bytescribeteam/application_diagram.png"
                },
                {
                    "title": "Stepfunction workflow",
                    "caption": "Stepfunction for all tasks",
                    "tags": ["stepfunction"],
                    "s3_url": "s3://bytescribeteam/stepfuction-workflow.png"
                }
            ]
    """
    prompt = f"""You are given a long article and a list of candidate images (each includes title, caption/tags, and an S3 URL).
        Tasks:
        1) Produce 3 main bullet points summarizing the core ideas of the article (≤60 words each, no overlap).
        2) For each bullet point, select at most three best-matching images from the provided list.
        3) If there is no any suitable images, return empty images and not invent images.
        4) Return a valid JSON object with this schema:
        {{
        "bullets": [
            {{
            "text": "<<=60 words>>",
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

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 8192,
        "temperature": 0.2,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    res = bedrock_client.invoke_model(
        modelId=BEDROCK_MODEL_ANTHROPIC_CLAUDE35,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body)
    )
    out = json.loads(res["body"].read())
    print(json.dumps(out, indent=4))
    text = json.loads(out["content"][0].get("text", {})).get("bullets", [])
    print("\n\n--------------------------------")
    print(json.dumps(text, indent=4))
    return text


def initialize():
    global bedrock_client
    region = os.environ.get("REGION", "us-east-1")
    bedrock_client = boto3.client(service_name="bedrock-runtime", region_name=region)


initialize()
