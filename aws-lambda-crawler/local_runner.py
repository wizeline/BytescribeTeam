import sys
from handler import lambda_handler


def main():
    if len(sys.argv) < 2:
        print("Usage: python local_runner.py <url>")
        return
    url = sys.argv[1]
    event = {"url": url}
    result = lambda_handler(event)
    print(result)


if __name__ == "__main__":
    main()
