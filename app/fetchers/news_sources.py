# app/fetchers/news_sources.py
import httpx
from typing import List, Optional
import asyncio

class NewsSourceError(Exception):
    pass

async def fetch_gnews(client: httpx.AsyncClient, api_key: str, query: str, max_articles: int = 10) -> List[dict]:
    """Fetch from GNews API"""
    url = "https://gnews.io/api/v4/search"
    params = {
        "q": query,
        "token": api_key,
        "lang": "en",
        "max": max_articles,
        "sortby": "publishedAt"
    }
    
    try:
        r = await client.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("articles", [])
    except Exception as e:
        print(f"GNews API error: {e}")
        return []

async def fetch_mediastack(client: httpx.AsyncClient, api_key: str, keywords: str, limit: int = 25) -> List[dict]:
    """Fetch from Mediastack API"""
    url = "http://api.mediastack.com/v1/news"
    params = {
        "access_key": api_key,
        "keywords": keywords,
        "languages": "en",
        "limit": limit,
        "sort": "published_desc"
    }
    
    try:
        r = await client.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("data", [])
    except Exception as e:
        print(f"Mediastack API error: {e}")
        return []

async def fetch_currents_api(client: httpx.AsyncClient, api_key: str, keywords: str, page_size: int = 20) -> List[dict]:
    """Fetch from Currents API"""
    url = "https://api.currentsapi.services/v1/search"
    headers = {"Authorization": api_key}
    params = {
        "keywords": keywords,
        "language": "en",
        "page_size": page_size
    }
    
    try:
        r = await client.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("news", [])
    except Exception as e:
        print(f"Currents API error: {e}")
        return []