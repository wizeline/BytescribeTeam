import argparse
import json
import os
from handler import lambda_handler


def main():
    parser = argparse.ArgumentParser(description="Run the lambda handler locally against a URL")
    parser.add_argument("url", help="URL to fetch")
    parser.add_argument("-f", "--full", action="store_true", help="Request full content (download page resources)")
    parser.add_argument("--full-text", action="store_true", help="Return the full extracted text instead of a snippet")
    parser.add_argument("--snippet-max", type=int, help="Override PARSE_SNIPPET_MAX for this run")
    parser.add_argument("--action", help="Action to perform (e.g. index, summarize)")
    parser.add_argument("--output", help="Write the handler response body to this file (JSON)")
    parser.add_argument("--summary-length", choices=["short", "medium", "long"], default="medium", 
                       help="Summary length for summarize action (default: medium)")
    parser.add_argument("--focus", help="Focus area for summarization (e.g. 'key findings', 'technical details')")
    parser.add_argument("--model-id", default="anthropic.claude-3-haiku-20240307-v1:0",
                       help="Bedrock model ID for summarization (default: Claude 3 Haiku)")
    args = parser.parse_args()

    if args.snippet_max is not None:
        os.environ["PARSE_SNIPPET_MAX"] = str(args.snippet_max)

    event = {"url": args.url}
    if args.full:
        event["full"] = True
    if args.full_text:
        event["full_text"] = True
    if args.action:
        event["action"] = args.action
        # Add summarization parameters if using summarize action
        if args.action == "summarize":
            event["summary_length"] = args.summary_length
            if args.focus:
                event["focus"] = args.focus
            event["model_id"] = args.model_id

    result = lambda_handler(event)
    # Try to parse returned body JSON for nicer output and optional file write
    body = None
    try:
        body = json.loads(result.get("body") or "null")
    except Exception:
        body = result.get("body")

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                import json as _json

                _json.dump({"statusCode": result.get("statusCode"), "body": body}, f, ensure_ascii=False, indent=2)
            print(f"Wrote output to {args.output}")
        except Exception as exc:
            print(f"Failed to write output to {args.output}: {exc}")

    # Print a compact summary
    print("status:", result.get("statusCode"))
    print("body (first 1000 chars):")
    s = result.get("body") or ""
    print(s[:1000])


if __name__ == "__main__":
    main()
