# AWS Lambda HTML Crawler

Minimal project to crawl HTML pages using AWS Lambda (Python).

Features:

- Fetch HTML from a URL
- Parse title and text content
- Lambda handler that accepts `url` in the event

Additional output fields (new):

- `images`: array of image objects with `src`, `alt`, `title`, `width`, `height`, `class`.
- `videos`: array of video objects with `sources` (each has `src` and `type`), `poster`, `controls`, `autoplay`, `loop`, `width`, `height`.
- `references`: array of link objects with `href`, `text`, `title`, `target`, `rel`.
- `embedded`: array of embedded items (iframes) with `src`, `title`, `width`, `height`, `type`.

Using Poetry:

1. Install Poetry (if not installed):

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Install dependencies and create virtualenv via Poetry:

```bash
poetry install
poetry shell
```

Run locally:

```bash
python local_runner.py https://example.com
```

Deploy:

- Package with dependencies into a zip and upload to AWS Lambda, or use AWS SAM / Serverless Framework.

Run tests:

```bash
poetry run pytest -q
```

Package for AWS Lambda (simple):

```bash
poetry export -f requirements.txt --output requirements.txt --without-hashes
pip install -r requirements.txt -t package/
cp -r crawler handler.py local_runner.py package/
cd package && zip -r ../deployment.zip .
```

Deploy with AWS SAM:

1. Ensure AWS CLI is configured with credentials.
2. Build and deploy with SAM:

```bash
sam build --use-container
sam deploy --guided
```

Notes on crawler improvements:

- `crawler/fetcher.py` now honors `robots.txt` when possible and includes a small retry/backoff strategy.
- If a site blocks or refuses `robots.txt`, the fetcher will assume allowed.
- The `pyproject.toml` now uses `tool.poetry.group.dev.dependencies` for dev deps and accepts Python `>=3.9,<4.0`.
