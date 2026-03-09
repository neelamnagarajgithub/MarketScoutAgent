# app/fetchers/newsapi.py
import httpx
from typing import List

async def search_newsapi(client: httpx.AsyncClient, api_key: str, query: str, page_size: int = 20) -> List[dict]:
    """Fetch from NewsAPI"""
    url = "https://newsapi.org/v2/everything"
    headers = {"X-API-Key": api_key}
    params = {
        "q": query,
        "pageSize": page_size,
        "sortBy": "publishedAt",
        "language": "en"
    }
    
    try:
        r = await client.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for article in data.get("articles", []):
            results.append({
                "title": article.get("title"),
                "url": article.get("url"),
                "content": article.get("description") or article.get("content"),
                "publishedAt": article.get("publishedAt"),
                "metadata": {
                    "provider": "newsapi",
                    "source": article.get("source", {}).get("name"),
                    "author": article.get("author"),
                    "urlToImage": article.get("urlToImage")
                }
            })
        return results
    except Exception as e:
        print(f"NewsAPI error: {e}")
        return []