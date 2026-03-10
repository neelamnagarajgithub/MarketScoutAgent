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
            "content": f"Technologies used by {domain}",
            "publishedAt": None,
            "metadata": {"provider": "builtwith", "domain": domain, "full_data": data}
        }
    except Exception as e:
        print(f"BuiltWith API error: {e}")
        return {}

async def fetch_clearbit_company(client: httpx.AsyncClient, api_key: str, domain: str) -> dict:
    """Fetch company data from Clearbit API"""
    url = "https://company.clearbit.com/v2/companies/find"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {"domain": domain}
    
    try:
        r = await client.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        return {
            "title": data.get("name", f"Company data for {domain}"),
            "url": data.get("site", {}).get("url") if data.get("site") else f"https://{domain}",
            "content": data.get("description", "Company information from Clearbit"),
            "publishedAt": data.get("foundedYear"),
            "metadata": {
                "provider": "clearbit",
                "domain": domain,
                "employees": data.get("metrics", {}).get("employees"),
                "annual_revenue": data.get("metrics", {}).get("annualRevenue"),
                "industry": data.get("category", {}).get("industry"),
                "tech": data.get("tech", [])
            }
        }
    except Exception as e:
        print(f"Clearbit API error: {e}")
        return {}

async def fetch_apollo_contacts(client: httpx.AsyncClient, api_key: str, company_domain: str, limit: int = 10) -> List[dict]:
    """Fetch organization data from Apollo API using organizations/search endpoint"""
    url = "https://api.apollo.io/v1/organizations/search"
    headers = {"Cache-Control": "no-cache", "X-Api-Key": api_key}
    
    payload = {
        "organization_domain": company_domain,  # Updated parameter name
        "page": 1,
        "per_page": limit
    }
    
    try:
        r = await client.post(url, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        results = []
        # Updated to handle organizations response structure
        for org in data.get("organizations", []):
            results.append({
                "title": f"{org.get('name', 'Unknown Company')} - {org.get('industry', 'N/A')}",
                "url": org.get("website_url") or org.get("domain"),
                "content": f"Organization: {org.get('name', 'Unknown')} in {org.get('industry', 'N/A')} industry",
                "publishedAt": None,
                "metadata": {
                    "provider": "apollo",
                    "company_domain": company_domain,
                    "name": org.get("name"),
                    "industry": org.get("industry"),
                    "employees": org.get("estimated_num_employees"),
                    "revenue": org.get("annual_revenue"),
                    "location": f"{org.get('city', '')}, {org.get('state', '')}, {org.get('country', '')}"
                }
            })
        return results
    except Exception as e:
        print(f"Apollo API error: {e}")
        return []

async def fetch_gitlab_projects(client: httpx.AsyncClient, token: str, search_query: str, per_page: int = 20) -> List[dict]:
    """Fetch projects from GitLab API"""
    url = "https://gitlab.com/api/v4/projects"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "search": search_query,
        "order_by": "updated_at",
        "sort": "desc",
        "per_page": per_page,
        "simple": True
    }
    
    try:
        r = await client.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for project in data:
            results.append({
                "title": project.get("name"),
                "url": project.get("web_url"),
                "content": project.get("description", "GitLab project"),
                "publishedAt": project.get("updated_at"),
                "metadata": {
                    "provider": "gitlab",
                    "project_id": project.get("id"),
                    "namespace": project.get("namespace", {}).get("name"),
                    "stars": project.get("star_count"),
                    "forks": project.get("forks_count"),
                    "languages": project.get("languages", {}),
                    "visibility": project.get("visibility")
                }
            })
        return results
    except Exception as e:
        print(f"GitLab API error: {e}")
        return []