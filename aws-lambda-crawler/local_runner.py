import argparse
import os
from handler import lambda_handler


def main():
    parser = argparse.ArgumentParser(description="Run the lambda handler locally against a URL")
    parser.add_argument("url", help="URL to fetch")
    parser.add_argument("-f", "--full", action="store_true", help="Request full content (download page resources)")
    parser.add_argument("--full-text", action="store_true", help="Return the full extracted text instead of a snippet")
    parser.add_argument("--snippet-max", type=int, help="Override PARSE_SNIPPET_MAX for this run")
    args = parser.parse_args()

    if args.snippet_max is not None:
        os.environ["PARSE_SNIPPET_MAX"] = str(args.snippet_max)

    event = {"url": args.url}
    if args.full:
        event["full"] = True
    if args.full_text:
        event["full_text"] = True

    result = lambda_handler(event)
    print(result)


if __name__ == "__main__":
    main()
