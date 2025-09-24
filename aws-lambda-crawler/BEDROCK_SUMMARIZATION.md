# AWS Bedrock Content Summarization

This document explains how to use the new AWS Bedrock integration to summarize web content crawled by the application.

## Overview

The crawler now supports `action=summarize` which:

1. Crawls and extracts content from a URL
2. Sends the content to AWS Bedrock (Claude 3 or other LLMs)
3. Returns a concise summary based on your specifications

## Setup Requirements

### 1. AWS Credentials

Ensure your environment has AWS credentials configured:

```bash
# Option 1: AWS CLI
aws configure

# Option 2: Environment variables
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1

# Option 3: IAM Role (recommended for Lambda/EC2)
```

### 2. Bedrock Model Access

Enable model access in AWS Bedrock console:

1. Go to AWS Bedrock → Model access
2. Request access to desired models (e.g., Claude 3 models)
3. Wait for approval (usually immediate for Claude 3)

### 3. Required Permissions

Your AWS user/role needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel"],
      "Resource": "arn:aws:bedrock:*::foundation-model/*"
    }
  ]
}
```

## Usage Examples

### 1. Basic Summarization (CLI)

```bash
# Navigate to the aws-lambda-crawler directory
cd aws-lambda-crawler

# Basic summary (medium length)
python3 local_runner.py 'https://example.com/article' --action summarize

# Short summary (1-2 sentences)
python3 local_runner.py 'https://example.com/article' --action summarize --summary-length short

# Long summary (2-3 paragraphs)
python3 local_runner.py 'https://example.com/article' --action summarize --summary-length long

# Focus on specific aspects
python3 local_runner.py 'https://example.com/article' --action summarize --focus "key findings"
python3 local_runner.py 'https://example.com/article' --action summarize --focus "technical details"
python3 local_runner.py 'https://example.com/article' --action summarize --focus "action items"

# Use different model
python3 local_runner.py 'https://example.com/article' --action summarize --model-id "anthropic.claude-3-sonnet-20240229-v1:0"

# Save output to file
python3 local_runner.py 'https://example.com/article' --action summarize --output summary.json
```

### 2. API Usage (Lambda/HTTP)

#### Basic Request

```json
{
  "url": "https://example.com/article",
  "action": "summarize"
}
```

#### Advanced Request

```json
{
  "url": "https://example.com/article",
  "action": "summarize",
  "summary_length": "short",
  "focus": "key findings",
  "model_id": "anthropic.claude-3-sonnet-20240229-v1:0"
}
```

#### Response Format

```json
{
  "statusCode": 200,
  "body": {
    "url": "https://example.com/article",
    "title": "Article Title",
    "summary": "This article discusses...",
    "summary_metadata": {
      "model_used": "anthropic.claude-3-haiku-20240307-v1:0",
      "input_length": 5420,
      "summary_length": 245,
      "focus": "key findings",
      "length_setting": "medium"
    }
  }
}
```

### 3. Programmatic Usage

```python
from handler import lambda_handler

# Basic summarization
event = {
    "url": "https://example.com/article",
    "action": "summarize"
}
response = lambda_handler(event)

# Advanced summarization
event = {
    "url": "https://example.com/article",
    "action": "summarize",
    "summary_length": "short",
    "focus": "technical details",
    "model_id": "anthropic.claude-3-sonnet-20240229-v1:0"
}
response = lambda_handler(event)
```

## Available Models

### Claude 3 Models (Recommended)

- `anthropic.claude-3-haiku-20240307-v1:0` - Fast, cost-effective
- `anthropic.claude-3-sonnet-20240229-v1:0` - Balanced performance
- `anthropic.claude-3-opus-20240229-v1:0` - Highest quality

### Amazon Titan Models

- `amazon.titan-text-express-v1` - Amazon's general model
- `amazon.titan-text-lite-v1` - Lightweight option

### AI21 Labs Models

- `ai21.j2-mid-v1` - Mid-tier performance
- `ai21.j2-ultra-v1` - Premium option

## Parameters

### `summary_length`

- `"short"` - 1-2 sentences
- `"medium"` - 1 paragraph (3-5 sentences) [default]
- `"long"` - 2-3 paragraphs

### `focus` (optional)

Examples of focus areas:

- `"key findings"`
- `"technical details"`
- `"action items"`
- `"main arguments"`
- `"conclusions"`
- `"methodology"`

### `model_id`

Choose based on your needs:

- **Speed/Cost**: Claude 3 Haiku
- **Balance**: Claude 3 Sonnet
- **Quality**: Claude 3 Opus

## Error Handling

The API returns specific error messages:

- `400` - Missing URL or invalid parameters
- `502` - Failed to fetch URL or Bedrock API error
- `500` - Internal processing error

Example error response:

```json
{
  "statusCode": 502,
  "body": {
    "error": "summarization failed",
    "detail": "AWS Error (AccessDenied): Model access not granted",
    "url": "https://example.com/article"
  }
}
```

## Cost Considerations

- **Input tokens**: Based on the crawled text length
- **Output tokens**: Based on summary length setting
- **Model pricing**: Varies by model (Haiku < Sonnet < Opus)

Typical costs (as of 2025):

- Short article (1000 words) + medium summary: ~$0.001-0.005
- Long document (5000 words) + short summary: ~$0.005-0.02

## Best Practices

1. **Use appropriate summary length**: Short for quick overviews, long for detailed analysis
2. **Specify focus**: Helps the model generate more relevant summaries
3. **Choose the right model**: Balance cost vs. quality for your use case
4. **Handle errors gracefully**: Implement retry logic for transient failures
5. **Monitor costs**: Track token usage in high-volume scenarios

## Integration with Existing Features

### Combined with Full Content

```bash
# Summarize with resource fetching
python3 local_runner.py 'https://example.com/article' --action summarize --full
```

### Batch Processing

```python
urls = ["https://site1.com/article", "https://site2.com/doc"]
summaries = []

for url in urls:
    event = {"url": url, "action": "summarize", "summary_length": "short"}
    response = lambda_handler(event)
    summaries.append(response)
```

## Testing

Test the integration with a simple example:

```bash
cd aws-lambda-crawler
python3 local_runner.py 'https://example.com' --action summarize --summary-length short --output test_summary.json
```

This should create a `test_summary.json` file with the summarized content.
