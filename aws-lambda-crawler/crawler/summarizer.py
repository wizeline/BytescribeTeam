import json
import os
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError


def get_bedrock_client(region_name: str = None):
    """Get AWS Bedrock Runtime client."""
    region = region_name or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    return boto3.client("bedrock-runtime", region_name=region)


def summarize_text(
    text: str,
    model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
    max_tokens: int = 2000,
    summary_length: str = "medium",
    focus: Optional[str] = None,
    bedrock_client=None
) -> Dict[str, Any]:
    """
    Summarize text using AWS Bedrock.
    
    Args:
        text: The text to summarize
        model_id: Bedrock model ID to use for summarization
        max_tokens: Maximum tokens in the response
        summary_length: "short" (1-2 sentences), "medium" (1 paragraph), "long" (2-3 paragraphs)
        focus: Optional focus area (e.g., "technical details", "key findings", "action items")
        bedrock_client: Optional pre-configured Bedrock client
        
    Returns:
        Dict with "summary", "model_used", "input_length", "summary_length"
    """
    if not text or not text.strip():
        return {
            "summary": "",
            "model_used": model_id,
            "input_length": 0,
            "summary_length": 0,
            "error": "No text provided"
        }

    if bedrock_client is None:
        bedrock_client = get_bedrock_client()

    # Build prompt based on summary length and focus
    length_instructions = {
        "short": "Provide a very concise summary in 1-2 sentences.",
        "medium": "Provide a concise summary in one paragraph (3-5 sentences).", 
        "long": "Provide a comprehensive summary in 2-3 paragraphs."
    }
    
    length_instruction = length_instructions.get(summary_length, length_instructions["medium"])
    
    focus_instruction = ""
    if focus:
        focus_instruction = f" Focus specifically on {focus}."

    prompt = f"""Please summarize the following text. {length_instruction}{focus_instruction}

Text to summarize:
{text}

Summary:"""

    try:
        # Claude 3 format
        if "claude" in model_id.lower():
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
        else:
            # Generic format for other models
            payload = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": max_tokens,
                    "temperature": 0.3,
                    "topP": 0.9
                }
            }

        response = bedrock_client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )

        response_body = json.loads(response["body"].read().decode())

        # Extract summary based on model response format
        summary = ""
        if "claude" in model_id.lower():
            # Claude 3 response format
            if "content" in response_body and len(response_body["content"]) > 0:
                summary = response_body["content"][0].get("text", "")
        elif "completion" in response_body:
            # Amazon Titan or similar
            summary = response_body["completion"]
        elif "results" in response_body:
            # Other models
            summary = response_body["results"][0].get("outputText", "")
        else:
            # Fallback - try to find text content
            summary = str(response_body)

        return {
            "summary": summary.strip(),
            "model_used": model_id,
            "input_length": len(text),
            "summary_length": len(summary.strip()),
            "focus": focus,
            "length_setting": summary_length
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        
        return {
            "summary": "",
            "model_used": model_id,
            "input_length": len(text),
            "summary_length": 0,
            "error": f"AWS Error ({error_code}): {error_message}"
        }
    except Exception as e:
        return {
            "summary": "",
            "model_used": model_id,
            "input_length": len(text),
            "summary_length": 0,
            "error": f"Unexpected error: {str(e)}"
        }


def summarize_document(
    document: Dict[str, Any],
    model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
    summary_length: str = "medium",
    focus: Optional[str] = None,
    bedrock_client=None
) -> Dict[str, Any]:
    """
    Summarize a structured document (output from crawler.processor.create_document).
    
    Args:
        document: Document dict with 'text', 'title', 'url', etc.
        model_id: Bedrock model ID
        summary_length: "short", "medium", or "long"
        focus: Optional focus area
        bedrock_client: Optional pre-configured client
        
    Returns:
        Updated document with "summary" field added
    """
    text = document.get("text", "")
    title = document.get("title", "")
    
    # Include title in the text for better context
    full_text = f"Title: {title}\n\n{text}" if title else text
    
    summary_result = summarize_text(
        text=full_text,
        model_id=model_id,
        summary_length=summary_length,
        focus=focus,
        bedrock_client=bedrock_client
    )
    
    # Add summary info to the document
    enhanced_document = document.copy()
    enhanced_document["summary"] = summary_result["summary"]
    enhanced_document["summary_metadata"] = {
        "model_used": summary_result["model_used"],
        "input_length": summary_result["input_length"],
        "summary_length": summary_result["summary_length"],
        "focus": summary_result.get("focus"),
        "length_setting": summary_result.get("length_setting"),
        "error": summary_result.get("error")
    }
    
    return enhanced_document


def get_available_models():
    """Return a list of commonly available Bedrock models for summarization."""
    return [
        "anthropic.claude-3-haiku-20240307-v1:0",  # Fast, cost-effective
        "anthropic.claude-3-sonnet-20240229-v1:0",  # Balanced performance
        "anthropic.claude-3-opus-20240229-v1:0",    # Highest quality
        "amazon.titan-text-express-v1",              # Amazon's model
        "amazon.titan-text-lite-v1",                 # Lightweight option
        "ai21.j2-mid-v1",                           # AI21 Labs
        "ai21.j2-ultra-v1",                         # AI21 Labs premium
    ]