import os
import asyncio
import httpx
import logging
from typing import Dict, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class APIKeyValidator:
    """Validate API keys and check rate limits"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.validation_results = {}
    
    async def validate_all_keys(self) -> Dict[str, bool]:
        """Validate all configured API keys"""
        keys_config = self.config.get('keys', {})
        
        validation_tasks = []
        for service, key in keys_config.items():
            if key and key.strip():
                validation_tasks.append(self._validate_key(service, key))
        
        if validation_tasks:
            results = await asyncio.gather(*validation_tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                service = list(keys_config.keys())[i]
                if isinstance(result, Exception):
                    self.validation_results[service] = False
                    logger.error(f"❌ {service}: Validation failed - {result}")
                else:
                    self.validation_results[service] = result
                    status = "✅" if result else "❌"
                    logger.info(f"{status} {service}: {'Valid' if result else 'Invalid'}")
        
        return self.validation_results
    
    async def _validate_key(self, service: str, api_key: str) -> bool:
        """Validate individual API key"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                if service == 'serpapi':
                    return await self._validate_serpapi(client, api_key)
                elif service == 'newsapi':  
                    return await self._validate_newsapi(client, api_key)
                elif service == 'gnews':
                    return await self._validate_gnews(client, api_key)
                elif service == 'github':
                    return await self._validate_github(client, api_key)
                elif service == 'alpha_vantage':
                    return await self._validate_alpha_vantage(client, api_key)
                elif service == 'polygon':
                    return await self._validate_polygon(client, api_key)
                else:
                    return True  # Unknown service, assume valid
                    
        except Exception as e:
            logger.error(f"Validation error for {service}: {e}")
            return False
    
    async def _validate_serpapi(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate SerpAPI key"""
        try:
            response = await client.get(
                "https://serpapi.com/search.json",
                params={"q": "test", "api_key": api_key, "engine": "google"},
                timeout=5
            )
            return response.status_code == 200 and 'error' not in response.json()
        except:
            return False
    
    async def _validate_newsapi(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate NewsAPI key"""
        try:
            response = await client.get(
                "https://newsapi.org/v2/top-headlines",
                headers={"X-API-Key": api_key},
                params={"country": "us", "pageSize": 1},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    async def _validate_gnews(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate GNews API key"""
        try:
            response = await client.get(
                "https://gnews.io/api/v4/search",
                params={"q": "test", "token": api_key, "max": 1},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    async def _validate_github(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate GitHub token"""
        try:
            response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {api_key}"},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    async def _validate_alpha_vantage(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate Alpha Vantage API key"""
        try:
            response = await client.get(
                "https://www.alphavantage.co/query",
                params={"function": "TIME_SERIES_INTRADAY", "symbol": "AAPL", "interval": "1min", "apikey": api_key},
                timeout=10
            )
            data = response.json()
            return "Error Message" not in data and "Note" not in data
        except:
            return False
    
    async def _validate_polygon(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate Polygon API key"""
        try:
            response = await client.get(
                f"https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/day/2023-01-01/2023-01-02",
                params={"apikey": api_key},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def get_valid_keys(self) -> List[str]:
        """Get list of valid API services"""
        return [service for service, valid in self.validation_results.items() if valid]
    
    def get_invalid_keys(self) -> List[str]:
        """Get list of invalid API services"""
        return [service for service, valid in self.validation_results.items() if not valid]