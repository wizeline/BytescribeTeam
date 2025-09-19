from bs4 import BeautifulSoup


def parse_html(html: str) -> dict:
    """Parse HTML and return a small dict with `title` and `text_snippet`."""
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Extract visible text from body and return a short snippet
    body = soup.find("body")
    if body:
        text = " ".join(body.stripped_strings)
    else:
        text = " ".join(soup.stripped_strings)

    snippet = text[:400]
    return {"title": title, "text_snippet": snippet}
