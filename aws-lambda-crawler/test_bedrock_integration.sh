#!/bin/bash

# Test commands for aws-lambda-crawler with Bedrock integration

echo "=== Checking Bedrock model access ==="
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"action": "check_models"}' \
  https://fw1yarpl2c.execute-api.ap-southeast-2.amazonaws.com/Prod/crawl

echo -e "\n\n=== Basic crawling with Bedrock summarization (default model) ==="
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"url":"https://wizeline.atlassian.net/wiki/spaces/VS/pages/4589223950/Technical+Overview", "full": true}' \
  https://fw1yarpl2c.execute-api.ap-southeast-2.amazonaws.com/Prod/crawl

echo -e "\n\n=== Summarization with custom model (Claude Haiku) ==="
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"url":"https://wizeline.atlassian.net/wiki/spaces/VS/pages/4589223950/Technical+Overview", "full": true, "model_id": "anthropic.claude-3-haiku-20240307-v1:0"}' \
  https://fw1yarpl2c.execute-api.ap-southeast-2.amazonaws.com/Prod/crawl

echo -e "\n\n=== Summarization with custom model and text generation config ==="
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"url":"https://wizeline.atlassian.net/wiki/spaces/VS/pages/4589223950/Technical+Overview", "full": true, "model_id": "amazon.titan-text-express-v1", "text_config": {"temperature": 0.3, "maxTokenCount": 2048}}' \
  https://fw1yarpl2c.execute-api.ap-southeast-2.amazonaws.com/Prod/crawl

echo -e "\n\n=== Test with httpbin (simple page) ==="
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"url":"https://httpbin.org/html"}' \
  https://fw1yarpl2c.execute-api.ap-southeast-2.amazonaws.com/Prod/crawl