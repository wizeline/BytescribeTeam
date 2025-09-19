# Webapp to Test Lambda Handler

Run locally to invoke the `lambda_handler` in `handler.py`.

Setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run (from repo root):

```bash
python -m webapp.app
```

Or run directly from the `webapp` folder:

````bash
cd webapp
source .venv/bin/activate
# Webapp to Test Lambda Handler

Run locally to invoke the `lambda_handler` in `handler.py`.

Setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
````

Run (from repo root):

```bash
python -m webapp.app
```

Or run directly from the `webapp` folder:

```bash
cd webapp
source .venv/bin/activate
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

Poetry (preferred):

```bash
cd webapp
poetry install
poetry run run-webapp
```

This uses the `run-webapp` script defined in `pyproject.toml`.

## Credentials

The webapp (and the crawler) can use Confluence credentials when fetching
cloud-hosted pages. Provide credentials in one of two ways:

- Environment variables (recommended):

  ```bash
  export CONFLUENCE_USER='you@example.com'               # optional for basic auth
  export CONFLUENCE_API_TOKEN='your_api_token_here'      # or CONFLUENCE_PASSWORD
  # or for bearer token:
  export CONFLUENCE_BEARER_TOKEN='your_bearer_token'
  ```
