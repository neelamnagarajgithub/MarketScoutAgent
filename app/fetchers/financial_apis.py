# app/fetchers/financial_apis.py
import httpx
from typing import List, Dict
import asyncio
from datetime import datetime, timedelta

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

async def fetch_polygon_news(client: httpx.AsyncClient, api_key: str, ticker: str = None, limit: int = 10) -> List[dict]:
    """Fetch news from Polygon API"""
    url = "https://api.polygon.io/v2/reference/news"
    params = {
        "apikey": api_key,
        "limit": limit,
        "order": "desc"
    }
    if ticker:
        params["ticker"] = ticker
        
    try:
        r = await client.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for article in data.get("results", []):
            results.append({
                "title": article.get("title"),
                "url": article.get("article_url"),
                "content": article.get("description"),
                "publishedAt": article.get("published_utc"),
                "metadata": {
                    "provider": "polygon",
                    "author": article.get("author"),
                    "tickers": article.get("tickers", []),
                    "keywords": article.get("keywords", [])
                }
            })
        return results
    except Exception as e:
        print(f"Polygon API error: {e}")
        return []

async def fetch_finnhub_news(client: httpx.AsyncClient, api_key: str, symbol: str = "AAPL", days_back: int = 7) -> List[dict]:
    """Fetch news from Finnhub API"""
    url = "https://finnhub.io/api/v1/company-news"
    params = {
        "symbol": symbol,
        "from": (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d"),
        "to": datetime.now().strftime("%Y-%m-%d"),
        "token": api_key
    }
    
    try:
        r = await client.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for article in data:
            results.append({
                "title": article.get("headline"),
                "url": article.get("url"),
                "content": article.get("summary"),
                "publishedAt": datetime.fromtimestamp(article.get("datetime", 0)).isoformat(),
                "metadata": {
                    "provider": "finnhub",
                    "category": article.get("category"),
                    "source": article.get("source"),
                    "image": article.get("image")
                }
            })
        return results
    except Exception as e:
        print(f"Finnhub API error: {e}")
        return []

async def fetch_quandl_data(client: httpx.AsyncClient, api_key: str, dataset: str = "WIKI/AAPL") -> List[dict]:
    """Fetch financial data from Quandl API"""
    url = f"https://www.quandl.com/api/v3/datasets/{dataset}.json"
    params = {
        "api_key": api_key,
        "limit": 10,
        "order": "desc"
    }
    
    try:
        r = await client.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        dataset_info = data.get("dataset", {})
        columns = dataset_info.get("column_names", [])
        data_rows = dataset_info.get("data", [])
        
        results = []
        for row in data_rows:
            row_dict = dict(zip(columns, row))
            results.append({
                "title": f"{dataset_info.get('name', 'Financial Data')} - {row_dict.get('Date', 'N/A')}",
                "content": f"Financial metrics for {dataset}",
                "publishedAt": str(row_dict.get("Date", "")),
                "metadata": {
                    "provider": "quandl",
                    "dataset_code": dataset,
                    "data": row_dict,
                    "database_code": dataset_info.get("database_code"),
                    "dataset_name": dataset_info.get("name")
                }
            })
        return results
    except Exception as e:
        print(f"Quandl API error: {e}")
        return []

async def fetch_massive_dividends(client: httpx.AsyncClient, api_key: str, symbols: List[str] = None) -> List[dict]:
    """Fetch dividend data from Massive.com financial API"""
    url = "https://api.massive.com/v3/reference/dividends"
    params = {"apiKey": api_key, "limit": 20}
    
    # Add symbol filter if provided
    if symbols:
        params["ticker"] = ",".join(symbols)
    
    try:
        r = await client.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        if data.get("status") != "OK":
            print(f"Massive API error: {data}")
            return []
        
        results = []
        for dividend in data.get("results", []):
            results.append({
                "title": f"{dividend.get('ticker', 'Unknown')} Dividend - ${dividend.get('cash_amount', 0)}",
                "url": f"https://finance.yahoo.com/quote/{dividend.get('ticker', '')}",
                "content": f"Dividend: ${dividend.get('cash_amount', 0)} {dividend.get('currency', 'USD')} "
                          f"Ex-Date: {dividend.get('ex_dividend_date', 'N/A')} "
                          f"Pay Date: {dividend.get('pay_date', 'N/A')} "
                          f"Type: {dividend.get('dividend_type', 'N/A')}",
                "publishedAt": dividend.get('declaration_date'),
                "metadata": {
                    "provider": "massive",
                    "ticker": dividend.get("ticker"),
                    "cash_amount": dividend.get("cash_amount"),
                    "currency": dividend.get("currency"),
                    "ex_dividend_date": dividend.get("ex_dividend_date"),
                    "pay_date": dividend.get("pay_date"),
                    "record_date": dividend.get("record_date"),
                    "dividend_type": dividend.get("dividend_type"),
                    "frequency": dividend.get("frequency"),
                    "full_data": dividend
                }
            })
        
        return results
    except Exception as e:
        print(f"Massive API error: {e}")
        return []

async def fetch_massive_market_data(client: httpx.AsyncClient, api_key: str, symbols: List[str]) -> List[dict]:
    """Fetch market data from Massive.com (alternative endpoint)"""
    # Note: This would use other Massive endpoints like trades, quotes, etc.
    # For now, we'll use dividends as the main data source
    return await fetch_massive_dividends(client, api_key, symbols)