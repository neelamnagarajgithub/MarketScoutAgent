# app/fetchers/startup_tracker.py
import httpx
from typing import List, Dict, Optional
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime

async def fetch_startup_tracker_companies(client: httpx.AsyncClient, api_key: str, query: str, limit: int = 20) -> List[dict]:
    """Fetch startup data from custom startup tracking API"""
    # This would be a custom API implementation
    url = "https://api.startup-tracker.com/v1/companies/search"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {
        "query": query,
        "limit": limit,
        "status": "active"
    }
    
    try:
        r = await client.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for company in data.get("companies", []):
            results.append({
                "title": company.get("name"),
                "url": company.get("website"),
                "content": company.get("description", ""),
                "publishedAt": company.get("founded_date"),
                "metadata": {
                    "provider": "startup_tracker",
                    "funding_stage": company.get("funding_stage"),
                    "total_funding": company.get("total_funding"),
                    "employees": company.get("employee_count"),
                    "industry": company.get("industry"),
                    "location": company.get("location"),
                    "founders": company.get("founders", [])
                }
            })
        return results
    except Exception as e:
        print(f"Startup Tracker API error: {e}")
        return []

async def scrape_angellist_startups(client: httpx.AsyncClient, search_term: str, limit: int = 20) -> List[dict]:
    """Scrape AngelList/Wellfound for startup information"""
    url = f"https://angel.co/companies"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; MarketAggregator/1.0)"
    }
    params = {"search": search_term}
    
    try:
        r = await client.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        
        soup = BeautifulSoup(r.text, 'html.parser')
        
        results = []
        # This is a simplified scraping example - actual implementation would need
        # more sophisticated parsing based on AngelList's current structure
        company_cards = soup.find_all('div', class_='company-card', limit=limit)
        
        for card in company_cards:
            name_elem = card.find('h3') or card.find('h2')
            desc_elem = card.find('p')
            link_elem = card.find('a')
            
            if name_elem:
                results.append({
                    "title": name_elem.get_text(strip=True),
                    "url": f"https://angel.co{link_elem.get('href', '')}" if link_elem else "",
                    "content": desc_elem.get_text(strip=True) if desc_elem else "",
                    "publishedAt": None,
                    "metadata": {
                        "provider": "angellist",
                        "platform": "startup_directory"
                    }
                })
        
        return results[:limit]
    except Exception as e:
        print(f"AngelList scraping error: {e}")
        return []

async def scrape_ycombinator_companies(client: httpx.AsyncClient, batch: str = None, limit: int = 50) -> List[dict]:
    """Scrape Y Combinator company directory"""
    url = "https://www.ycombinator.com/companies"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; MarketAggregator/1.0)"
    }
    params = {}
    if batch:
        params["batch"] = batch
    
    try:
        r = await client.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        
        soup = BeautifulSoup(r.text, 'html.parser')
        
        results = []
        # YC uses a specific structure for company listings
        company_elements = soup.find_all('div', class_='_company', limit=limit)
        
        for company in company_elements:
            name_elem = company.find('span', class_='_name')
            desc_elem = company.find('span', class_='_description') 
            batch_elem = company.find('span', class_='_batch')
            link_elem = company.find('a')
            
            if name_elem:
                results.append({
                    "title": name_elem.get_text(strip=True),
                    "url": link_elem.get('href', '') if link_elem else "",
                    "content": desc_elem.get_text(strip=True) if desc_elem else "",
                    "publishedAt": None,
                    "metadata": {
                        "provider": "ycombinator",
                        "batch": batch_elem.get_text(strip=True) if batch_elem else "",
                        "platform": "accelerator"
                    }
                })
        
        return results[:limit]
    except Exception as e:
        print(f"Y Combinator scraping error: {e}")
        return []

async def scrape_crunchbase_news(client: httpx.AsyncClient, query: str, limit: int = 20) -> List[dict]:
    """Scrape Crunchbase news without API"""
    url = "https://news.crunchbase.com/search/"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; MarketAggregator/1.0)"
    }
    params = {"q": query}
    
    try:
        r = await client.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        
        soup = BeautifulSoup(r.text, 'html.parser')
        
        results = []
        article_elements = soup.find_all('article', limit=limit)
        
        for article in article_elements:
            title_elem = article.find('h2') or article.find('h3')
            link_elem = article.find('a')
            excerpt_elem = article.find('p')
            date_elem = article.find('time')
            
            if title_elem and link_elem:
                results.append({
                    "title": title_elem.get_text(strip=True),
                    "url": link_elem.get('href', ''),
                    "content": excerpt_elem.get_text(strip=True) if excerpt_elem else "",
                    "publishedAt": date_elem.get('datetime') if date_elem else None,
                    "metadata": {
                        "provider": "crunchbase_news",
                        "platform": "startup_news"
                    }
                })
        
        return results[:limit]
    except Exception as e:
        print(f"Crunchbase news scraping error: {e}")
        return []

async def fetch_techcrunch_startups(client: httpx.AsyncClient, tag: str = "startups", limit: int = 20) -> List[dict]:
    """Fetch TechCrunch startup articles via RSS/scraping"""
    url = f"https://techcrunch.com/tag/{tag}/feed/"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; MarketAggregator/1.0)"
    }
    
    try:
        r = await client.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        
        # Parse RSS feed
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r.content)
        
        results = []
        for item in root.findall('.//item')[:limit]:
            title = item.find('title')
            link = item.find('link')
            description = item.find('description')
            pubDate = item.find('pubDate')
            
            if title is not None and link is not None:
                results.append({
                    "title": title.text,
                    "url": link.text,
                    "content": description.text if description is not None else "",
                    "publishedAt": pubDate.text if pubDate is not None else None,
                    "metadata": {
                        "provider": "techcrunch",
                        "tag": tag,
                        "platform": "tech_news"
                    }
                })
        
        return results
    except Exception as e:
        print(f"TechCrunch RSS error: {e}")
        return []