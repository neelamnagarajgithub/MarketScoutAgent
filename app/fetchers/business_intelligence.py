# app/fetchers/business_intelligence.py
import httpx
from typing import List, Optional
import asyncio
import base64

async def fetch_crunchbase_organizations(client: httpx.AsyncClient, api_key: str, query: str, limit: int = 25) -> List[dict]:
    """Fetch from Crunchbase API"""
    url = "https://api.crunchbase.com/api/v4/searches/organizations"
    headers = {"X-cb-user-key": api_key}
    
    payload = {
        "field_ids": ["name", "short_description", "website", "founded_on", "categories", "funding_total"],
        "query": [{"type": "predicate", "field_id": "name", "operator_id": "contains", "values": [query]}],
        "limit": limit
    }
    
    try:
        r = await client.post(url, headers=headers, json=payload, timeout=20)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for item in data.get("entities", []):
            props = item.get("properties", {})
            results.append({
                "title": props.get("name"),
                "url": props.get("website", {}).get("value") if props.get("website") else None,
                "content": props.get("short_description"),
                "publishedAt": props.get("founded_on", {}).get("value") if props.get("founded_on") else None,
                "metadata": {
                    "provider": "crunchbase",
                    "categories": props.get("categories", []),
                    "funding_total": props.get("funding_total", {}).get("value_usd") if props.get("funding_total") else None
                }
            })
        return results
    except Exception as e:
        print(f"Crunchbase API error: {e}")
        return []

async def fetch_builtwith_domain(client: httpx.AsyncClient, api_key: str, domain: str) -> dict:
    """Fetch technology stack from BuiltWith API"""
    url = f"https://api.builtwith.com/v20/api.json"
    params = {
        "KEY": api_key,
        "LOOKUP": domain
    }
    
    try:
        r = await client.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        return {
            "title": f"Technology Stack for {domain}",
            "url": f"https://{domain}",
            "content": f"Technologies: {', '.join([tech.get('Name', '') for result in data.get('Results', []) for tech in result.get('Result', {}).get('Paths', []) for tech_group in tech.get('Technologies', [])])}",
            "publishedAt": None,
            "metadata": {"provider": "builtwith", "domain": domain, "full_data": data}
        }
    except Exception as e:
        print(f"BuiltWith API error: {e}")
        return {}