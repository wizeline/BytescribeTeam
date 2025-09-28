import boto3
import json


region = "us-east-1"
runtime = boto3.client("bedrock-runtime", region_name=region)

# Embedded text
texts = [
    "The capital of Vietnam is Hanoi.",
    "Hanoi is the capital city of Vietnam.",
    "Ho Chi Minh City is the largest city in Vietnam."
]


def titan_embed(text: str):
    body = {
        "inputText": text
    }
    response = runtime.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body)
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


for t in texts:
    vec = titan_embed(t)
    print(f"Text: {t}")
    print(f"Embedding vector length: {len(vec)}")
    print(f"First 5 dims: {vec[:5]}")
    print("=" * 50)
