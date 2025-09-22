import os
from typing import Optional

from bs4 import BeautifulSoup


def parse_html(html: str, max_snippet_chars: Optional[int] = None, full_text: bool = False) -> dict:
    """Parse HTML and return a small dict with `title` and `text_snippet`.

    Parameters
    - html: the HTML source
    - max_snippet_chars: maximum number of characters to include in the
      `text_snippet`. If None, the function will consult the environment
      variable `PARSE_SNIPPET_MAX`. If that is not set or invalid, defaults
      to 400.
    """
    # Resolve max length: explicit param -> env var -> default 400
    if max_snippet_chars is None:
        try:
            env_val = os.getenv("PARSE_SNIPPET_MAX")
            max_snippet_chars = int(env_val) if env_val is not None else 400
        except Exception:
            max_snippet_chars = 400
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Extract visible text from body and return either the full text or a short snippet
    body = soup.find("body")
    if body:
        text = " ".join(body.stripped_strings)
    else:
        text = " ".join(soup.stripped_strings)

    if full_text:
        return {"title": title, "text_snippet": text}

    snippet = text[: max_snippet_chars]
    return {"title": title, "text_snippet": snippet}
