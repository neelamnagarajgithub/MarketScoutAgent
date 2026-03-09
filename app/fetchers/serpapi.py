# app/fetchers/serpapi.py
import httpx
from typing import List

SERPAPI_URL = "https://serpapi.com/search.json"

async def serp_search(client: httpx.AsyncClient, api_key: str, q: str, engine: str = "google") -> List[dict]:
    params = {"q": q, "api_key": api_key, "engine": engine}
    r = await client.get(SERPAPI_URL, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    # serpapi response is complex; we will extract organic results
    organic = data.get("organic_results", []) or data.get("organic", [])
    results = []
    for item in organic:
        results.append({
            "title": item.get("title"),
            "url": item.get("link") or item.get("url"),
            "content": item.get("snippet") or item.get("description"),
            "publishedAt": item.get("date"),
            "metadata": item
        })
    return results