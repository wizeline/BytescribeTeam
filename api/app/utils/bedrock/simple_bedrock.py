import boto3
import json

runtime = boto3.client("bedrock-runtime", region_name="us-east-1")

prompt = "Summarize the benefits of Amazon Bedrock in 3 bullet points."

body = json.dumps({
    "inputText": prompt,
    "textGenerationConfig": {
        "maxTokenCount": 200,
        "temperature": 0.7
    }
})
print(body)

resp = runtime.invoke_model(
    modelId="amazon.titan-text-express-v1",  # modelId từ list_foundation_models
    body=body,
    contentType="application/json",
    accept="application/json"
)

output = json.loads(resp["body"].read())
print(json.dumps(output, indent=4))
for idx, result in enumerate(output.get("results", [])):
    print(f"---> Result {idx}:", result.get("outputText", ""))
