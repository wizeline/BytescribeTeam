import hashlib
import os
import datetime
import urllib.parse
from typing import List, Dict, Optional, Any, Tuple

from bs4 import BeautifulSoup


def _extract_text_and_title(html: str) -> Tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    # remove script/style/noscript
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()

    title_tag = soup.find('title')
    title = title_tag.get_text(strip=True) if title_tag else ""

    body = soup.find('body')
    if body:
        text = " ".join(body.stripped_strings)
    else:
        text = " ".join(soup.stripped_strings)

    return text, title


def _compute_id(url: str, text: str) -> str:
    h = hashlib.sha256()
    h.update(url.encode('utf-8'))
    h.update(b"\n")
    h.update(text.encode('utf-8'))
    return h.hexdigest()


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Tuple[int, int, str]]:
    """Return list of (start, end, chunk_text).

    Simple character-based chunking with overlap. For production consider
    using a token-based chunker tuned to your embedding model.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: List[Tuple[int, int, str]] = []
    L = len(text)
    start = 0
    while start < L:
        end = min(start + chunk_size, L)
        chunk = text[start:end]
        chunks.append((start, end, chunk))
        if end == L:
            break
        start = max(0, end - overlap)
    return chunks


def _detect_language(text: str) -> Optional[str]:
    try:
        # optional dependency; returns language code like 'en'
        import importlib

        langdetect = importlib.import_module('langdetect')
        detect = getattr(langdetect, 'detect')
        return detect(text)
    except Exception:
        return None


def create_document(
    url: str,
    html: str,
    chunk_size: int = 1000,
    overlap: int = 200,
    parse_snippet_max: Optional[int] = None,
    source: Optional[str] = None,
    crawl_time: Optional[datetime.datetime] = None,
) -> Dict[str, Any]:
    """Create a structured document dict from url+html.

    Returns a dict containing metadata and a `chunks` list suitable for
    embedding & indexing.
    """
    text, title = _extract_text_and_title(html)

    # determine snippet length: param -> env -> default 400
    if parse_snippet_max is None:
        try:
            env_val = os.getenv("PARSE_SNIPPET_MAX")
            parse_snippet_max = int(env_val) if env_val is not None else 400
        except Exception:
            parse_snippet_max = 400

    snippet = text[:parse_snippet_max] if parse_snippet_max and text else ""

    doc_id = _compute_id(url, text)

    if crawl_time is None:
        crawl_time = datetime.datetime.utcnow()

    parsed = urllib.parse.urlparse(url)
    inferred_source = parsed.netloc

    language = _detect_language(text)

    # Build chunk objects
    raw_chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    chunks: List[Dict[str, Any]] = []
    for i, (start, end, chunk_text_str) in enumerate(raw_chunks):
        chunk_id = f"{doc_id}-{i}"
        chunks.append(
            {
                "chunk_id": chunk_id,
                "index": i,
                "start": start,
                "end": end,
                "text": chunk_text_str,
            }
        )

    document: Dict[str, Any] = {
        "id": doc_id,
        "url": url,
        "title": title,
        "text": text,
        "snippet": snippet,
        "content_type": "text/html",
        "source": source or inferred_source,
        "crawl_time": crawl_time.isoformat() + "Z",
        "language": language,
        "metadata": {},
        "chunks": chunks,
    }

    return document


def chunks_for_upsert(document: Dict[str, Any]) -> List[Tuple[str, str, Dict[str, Any]]]:
    """Return a list of tuples (vector_id, text, metadata) ready for upsert to a vector DB.

    Metadata contains minimal context to locate the chunk.
    """
    out: List[Tuple[str, str, Dict[str, Any]]] = []
    base_meta = {"url": document.get("url"), "title": document.get("title"), "doc_id": document.get("id")}
    for c in document.get("chunks", []):
        vec_id = c.get("chunk_id")
        text = c.get("text")
        meta = {**base_meta, "chunk_index": c.get("index"), "start": c.get("start"), "end": c.get("end")}
        out.append((vec_id, text, meta))
    return out
