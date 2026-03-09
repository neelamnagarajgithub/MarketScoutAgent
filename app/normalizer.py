# app/normalizer.py
from app.extractor import canonical_datetime, compute_hash

def normalize_item(source: str, raw: dict) -> dict:
    """
    Map a source-specific payload into canonical schema:
    {
      "source", "title", "url", "published_at", "content", "metadata", "content_hash"
    }
    """
    title = raw.get("title") or raw.get("name") or raw.get("headline") or ""
    url = raw.get("url") or raw.get("html_url") or raw.get("link") or raw.get("id")
    content = raw.get("content") or raw.get("body") or raw.get("summary") or ""
    published_at = raw.get("publishedAt") or raw.get("published_at") or raw.get("created_at") or raw.get("date")
    published_dt = canonical_datetime(published_at) if published_at else None
    metadata = raw.get("metadata") or {k:v for k,v in raw.items() if k not in ("title","url","content","publishedAt","published_at","date","id")}
    content_hash = compute_hash(content or title or url)
    return {
        "source": source,
        "title": title,
        "url": url,
        "content": content,
        "published_at": published_dt,
        "metadata": metadata,
        "content_hash": content_hash
    }