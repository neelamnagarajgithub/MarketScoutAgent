# app/fetchers/generic_scraper.py
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from app.extractor import extract_main_text
from typing import Optional
from datetime import datetime

HEADERS = {"User-Agent": "MarketScoutBot/1.0 (+https://example.com)"}

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def fetch_html(client: httpx.AsyncClient, url: str, timeout: int = 20) -> Optional[str]:
    r = await client.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text

async def scrape_url(client: httpx.AsyncClient, url: str) -> dict:
    html = await fetch_html(client, url)
    content = extract_main_text(html) if html else ""
    return {
        "title": None,
        "url": url,
        "content": content,
        "publishedAt": None,
        "metadata": {"fetched_at": datetime.utcnow().isoformat()}
    }