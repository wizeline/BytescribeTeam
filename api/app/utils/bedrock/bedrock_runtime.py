
"""
Lists the available Amazon Bedrock models.
"""
import logging
import json
import boto3
import os


from botocore.exceptions import ClientError
from app.constants import (
    BEDROCK_MODEL_AWS_TITANT
)
from app.core.config import settings

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
    prompt="Summarize the benefits of Amazon Bedrock in 3 bullet points.",
    text_config={},
    model_id=BEDROCK_MODEL_AWS_TITANT
):
    _TextGenerationConfig = {
        "maxTokenCount": 1024,
        "temperature": 0.7
    }

    body = json.dumps({
        "inputText": prompt,
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
    except ClientError:
        logger.error("Couldn't list foundation models.")
        raise

    output = json.loads(resp["body"].read())
    results = output.get("results", [])
    # --------------------------------------
    if settings.DEBUG:
        print(json.dumps(output, indent=4))
        for idx, result in enumerate(results):
            print(f"---> Result {idx}:", result.get("outputText", ""))

    return {"result": results[0] if results else {}}


def initialize():
    global bedrock_client
    region = os.environ.get("REGION", "us-east-1")
    bedrock_client = boto3.client(service_name="bedrock-runtime", region_name=region)


initialize()
