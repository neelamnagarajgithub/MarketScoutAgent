# app/fetchers/social_media.py
import httpx
from typing import List, Dict, Optional
import asyncio
import json
import base64
from datetime import datetime

async def fetch_twitter_tweets(client: httpx.AsyncClient, bearer_token: str, query: str, max_results: int = 10) -> List[dict]:
    """Fetch tweets from Twitter API v2"""
    url = "https://api.twitter.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {bearer_token}"}
    params = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": "created_at,author_id,public_metrics,context_annotations,lang",
        "expansions": "author_id",
        "user.fields": "name,username,verified,public_metrics"
    }
    
    try:
        r = await client.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        # Create user lookup
        users = {user["id"]: user for user in data.get("includes", {}).get("users", [])}
        
        results = []
        for tweet in data.get("data", []):
            author = users.get(tweet.get("author_id"), {})
            results.append({
                "title": f"Tweet by @{author.get('username', 'unknown')}",
                "url": f"https://twitter.com/{author.get('username', 'i')}/status/{tweet.get('id')}",
                "content": tweet.get("text", ""),
                "publishedAt": tweet.get("created_at"),
                "metadata": {
                    "provider": "twitter",
                    "tweet_id": tweet.get("id"),
                    "author": {
                        "username": author.get("username"),
                        "name": author.get("name"),
                        "verified": author.get("verified", False),
                        "followers": author.get("public_metrics", {}).get("followers_count", 0)
                    },
                    "metrics": tweet.get("public_metrics", {}),
                    "language": tweet.get("lang", "en")
                }
            })
        return results
    except Exception as e:
        print(f"Twitter API error: {e}")
        return []

async def fetch_linkedin_posts(client: httpx.AsyncClient, access_token: str, person_id: str = "me", limit: int = 10) -> List[dict]:
    """Fetch LinkedIn posts (requires authentication)"""
    url = f"https://api.linkedin.com/v2/shares"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "q": "owners",
        "owners": f"urn:li:person:{person_id}",
        "count": limit,
        "sortBy": "CREATED"
    }
    
    try:
        r = await client.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for share in data.get("elements", []):
            content = share.get("text", {}).get("text", "")
            
            results.append({
                "title": f"LinkedIn Post - {content[:50]}...",
                "url": f"https://www.linkedin.com/feed/update/{share.get('id', '')}",
                "content": content,
                "publishedAt": datetime.fromtimestamp(share.get("created", {}).get("time", 0) / 1000).isoformat(),
                "metadata": {
                    "provider": "linkedin",
                    "share_id": share.get("id"),
                    "owner": share.get("owner"),
                    "metrics": share.get("totalSocialActionCounts", {})
                }
            })
        return results
    except Exception as e:
        print(f"LinkedIn API error: {e}")
        return []

async def search_linkedin_companies(client: httpx.AsyncClient, access_token: str, keyword: str, limit: int = 10) -> List[dict]:
    """Search LinkedIn companies"""
    url = "https://api.linkedin.com/v2/companySearch"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "keywords": keyword,
        "count": limit
    }
    
    try:
        r = await client.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for company in data.get("elements", []):
            results.append({
                "title": company.get("name", ""),
                "url": f"https://www.linkedin.com/company/{company.get('id', '')}",
                "content": company.get("description", "LinkedIn company profile"),
                "publishedAt": None,
                "metadata": {
                    "provider": "linkedin_company",
                    "company_id": company.get("id"),
                    "industry": company.get("industry"),
                    "size": company.get("size"),
                    "headquarters": company.get("headquarters", {})
                }
            })
        return results
    except Exception as e:
        print(f"LinkedIn company search error: {e}")
        return []

async def scrape_x_tweets(client: httpx.AsyncClient, query: str, limit: int = 10) -> List[dict]:
    """Scrape X/Twitter without API (limited functionality)"""
    # Note: This is a basic implementation - X/Twitter has strong anti-scraping measures
    url = f"https://twitter.com/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    params = {
        "q": query,
        "src": "typed_query",
        "f": "live"
    }
    
    try:
        r = await client.get(url, headers=headers, params=params, timeout=15)
        
        # Basic fallback - just return a placeholder since actual scraping would require 
        # complex JavaScript rendering and is often blocked
        results = []
        results.append({
            "title": f"X/Twitter search: {query}",
            "url": f"https://twitter.com/search?q={query}",
            "content": f"X/Twitter search results for: {query} (API access required for full functionality)",
            "publishedAt": datetime.now().isoformat(),
            "metadata": {
                "provider": "x_scraper",
                "query": query,
                "note": "Limited functionality without API access"
            }
        })
        return results
    except Exception as e:
        print(f"X/Twitter scraping error: {e}")
        return []