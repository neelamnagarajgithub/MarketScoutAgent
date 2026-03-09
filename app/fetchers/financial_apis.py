# app/fetchers/financial_apis.py
import httpx
from typing import List, Dict
import asyncio

async def fetch_alpha_vantage_company_overview(client: httpx.AsyncClient, api_key: str, symbol: str) -> dict:
    """Fetch company overview from Alpha Vantage"""
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "OVERVIEW",
        "symbol": symbol,
        "apikey": api_key
    }
    
    try:
        r = await client.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        return {
            "title": f"{data.get('Name', symbol)} - Company Overview",
            "url": f"https://finance.yahoo.com/quote/{symbol}",
            "content": f"Description: {data.get('Description', '')}",
            "publishedAt": None,
            "metadata": {
                "provider": "alpha_vantage",
                "symbol": symbol,
                "sector": data.get("Sector"),
                "industry": data.get("Industry"),
                "market_cap": data.get("MarketCapitalization"),
                "full_data": data
            }
        }
    except Exception as e:
        print(f"Alpha Vantage API error: {e}")
        return {}

async def fetch_polygon_company_details(client: httpx.AsyncClient, api_key: str, ticker: str) -> dict:
    """Fetch company details from Polygon.io"""
    url = f"https://api.polygon.io/v3/reference/tickers/{ticker}"
    params = {"apikey": api_key}
    
    try:
        r = await client.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        results = data.get("results", {})
        return {
            "title": f"{results.get('name', ticker)} - Company Details",
            "url": results.get("homepage_url", f"https://finance.yahoo.com/quote/{ticker}"),
            "content": f"Description: {results.get('description', '')}",
            "publishedAt": None,
            "metadata": {
                "provider": "polygon",
                "ticker": ticker,
                "market": results.get("market"),
                "locale": results.get("locale"),
                "type": results.get("type"),
                "full_data": results
            }
        }
    except Exception as e:
        print(f"Polygon API error: {e}")
        return {}

async def fetch_company_news_alpha_vantage(client: httpx.AsyncClient, api_key: str, tickers: str) -> List[dict]:
    """Fetch company news from Alpha Vantage"""
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": tickers,
        "apikey": api_key,
        "limit": 50
    }
    
    try:
        r = await client.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for article in data.get("feed", []):
            results.append({
                "title": article.get("title"),
                "url": article.get("url"),
                "content": article.get("summary"),
                "publishedAt": article.get("time_published"),
                "metadata": {
                    "provider": "alpha_vantage_news",
                    "source": article.get("source"),
                    "sentiment_score": article.get("overall_sentiment_score"),
                    "sentiment_label": article.get("overall_sentiment_label"),
                    "ticker_sentiment": article.get("ticker_sentiment")
                }
            })
        return results
    except Exception as e:
        print(f"Alpha Vantage News API error: {e}")
        return []