# app/fetchers/search_apis.py
import httpx
from typing import List
import asyncio

async def fetch_bing_search(client: httpx.AsyncClient, api_key: str, query: str, count: int = 20) -> List[dict]:
    """Fetch from Bing Search API"""
    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    params = {"q": query, "count": count, "responseFilter": "Webpages"}
    
    try:
        r = await client.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for item in data.get("webPages", {}).get("value", []):
            results.append({
                "title": item.get("name"),
                "url": item.get("url"),
                "content": item.get("snippet"),
                "publishedAt": item.get("dateLastCrawled"),
                "metadata": {"provider": "bing", "id": item.get("id")}
            })
        return results
    except Exception as e:
        print(f"Bing Search API error: {e}")
        return []

async def fetch_google_custom_search(client: httpx.AsyncClient, api_key: str, search_engine_id: str, query: str, num: int = 10) -> List[dict]:
    """Fetch from Google Custom Search API"""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": search_engine_id,
        "q": query,
        "num": num
    }
    
    try:
        r = await client.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for item in data.get("items", []):
            results.append({
                "title": item.get("title"),
                "url": item.get("link"),
                "content": item.get("snippet"),
                "publishedAt": None,
                "metadata": {"provider": "google_custom", "cacheId": item.get("cacheId")}
            })
        return results
    except Exception as e:
        print(f"Google Custom Search API error: {e}")
        return []