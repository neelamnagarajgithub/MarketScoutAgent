# app/fetchers/rss.py
import feedparser
from typing import List

def fetch_rss_feed(url: str, limit: int = 10) -> List[dict]:
    feed = feedparser.parse(url)
    out = []
    for entry in feed.entries[:limit]:
        out.append({
            "title": entry.get("title"),
            "url": entry.get("link"),
            "content": entry.get("summary"),
            "publishedAt": entry.get("published") or entry.get("published_parsed"),
            "metadata": {"id": entry.get("id")}
        })
    return out