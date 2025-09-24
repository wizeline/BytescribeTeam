import os
import urllib.parse
from typing import Optional, Dict, List, Any

from bs4 import BeautifulSoup


def extract_media_and_references(soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
    """Extract images, videos, and references from parsed HTML.
    
    Returns dict with:
    - images: list of image objects with src, alt, title, etc.
    - videos: list of video objects with src, poster, etc.
    - references: list of link objects with href, text, title, etc.
    """
    def resolve_url(url: str) -> str:
        """Resolve relative URLs to absolute URLs."""
        if not url:
            return url
        return urllib.parse.urljoin(base_url, url)
    
    # Extract images
    images = []
    for img in soup.find_all("img"):
        src = img.get("src")
        if src:
            image_data = {
                "src": resolve_url(src),
                "alt": img.get("alt", ""),
                "title": img.get("title", ""),
                "width": img.get("width"),
                "height": img.get("height"),
                "class": img.get("class", []) if img.get("class") else []
            }
            # Remove None values
            image_data = {k: v for k, v in image_data.items() if v is not None and v != ""}
            images.append(image_data)
    
    # Extract videos
    videos = []
    for video in soup.find_all("video"):
        video_sources = []
        src = video.get("src")
        if src:
            video_sources.append({"src": resolve_url(src), "type": video.get("type", "")})
        
        # Check for source elements
        for source in video.find_all("source"):
            src = source.get("src")
            if src:
                video_sources.append({"src": resolve_url(src), "type": source.get("type", "")})
        
        if video_sources:
            video_data = {
                "sources": video_sources,
                "poster": resolve_url(video.get("poster", "")),
                "controls": video.has_attr("controls"),
                "autoplay": video.has_attr("autoplay"),
                "loop": video.has_attr("loop"),
                "width": video.get("width"),
                "height": video.get("height")
            }
            # Remove empty values
            video_data = {k: v for k, v in video_data.items() if v is not None and v != ""}
            videos.append(video_data)
    
    # Extract references (links)
    references = []
    for link in soup.find_all("a"):
        href = link.get("href")
        if href and not href.startswith("#"):  # Skip anchor links
            link_text = link.get_text(strip=True)
            if link_text:  # Only include links with text
                reference_data = {
                    "href": resolve_url(href),
                    "text": link_text,
                    "title": link.get("title", ""),
                    "target": link.get("target", ""),
                    "rel": link.get("rel", []) if link.get("rel") else []
                }
                # Remove empty values
                reference_data = {k: v for k, v in reference_data.items() if v is not None and v != ""}
                references.append(reference_data)
    
    # Also extract embedded content (iframes)
    embedded = []
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src")
        if src:
            embedded_data = {
                "src": resolve_url(src),
                "title": iframe.get("title", ""),
                "width": iframe.get("width"),
                "height": iframe.get("height"),
                "type": "iframe"
            }
            # Remove empty values
            embedded_data = {k: v for k, v in embedded_data.items() if v is not None and v != ""}
            embedded.append(embedded_data)
    
    return {
        "images": images,
        "videos": videos,
        "references": references,
        "embedded": embedded
    }


def parse_html(html: str, max_snippet_chars: Optional[int] = None, full_text: bool = False, extract_resources: bool = True, base_url: str = "") -> dict:
    """Parse HTML and return a dict with text content and optional media resources.

    Parameters
    - html: the HTML source
    - max_snippet_chars: maximum number of characters to include in the
      `text_snippet`. If None, the function will consult the environment
      variable `PARSE_SNIPPET_MAX`. If that is not set or invalid, defaults
      to 400.
    - full_text: if True, return full text instead of snippet
    - extract_resources: if True, extract images, videos, and references
    - base_url: base URL for resolving relative URLs in resources
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

    result = {"title": title}
    
    if full_text:
        result["text_snippet"] = text
    else:
        snippet = text[: max_snippet_chars]
        result["text_snippet"] = snippet

    # Extract media and references if requested
    if extract_resources and base_url:
        resources = extract_media_and_references(soup, base_url)
        result.update(resources)
    
    return result
