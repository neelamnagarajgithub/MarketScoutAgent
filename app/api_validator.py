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
        
        # Validate sequentially to avoid rate limiting and timeout issues
        for service, key in keys_config.items():
            if key and key.strip():
                try:
                    result = await self._validate_key(service, key)
                    self.validation_results[service] = result
                    status = "✅" if result else "❌"
                    logger.info(f"{status} {service}: {'Valid' if result else 'Invalid'}")
                except Exception as e:
                    self.validation_results[service] = False
                    logger.error(f"❌ {service}: Validation failed - {e}")
        
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
                elif service == 'mediastack':
                    return await self._validate_mediastack(client, api_key)
                elif service == 'currents':
                    return await self._validate_currents(client, api_key)
                elif service == 'github' or service == 'github_personal_access_token':
                    return await self._validate_github(client, api_key)
                elif service == 'gitlab':
                    return await self._validate_gitlab(client, api_key)
                elif service == 'alpha_vantage':
                    return await self._validate_alpha_vantage(client, api_key)
                elif service == 'polygon':
                    return await self._validate_polygon(client, api_key)
                elif service == 'massive' or service == 'marketstack':
                    return await self._validate_massive(client, api_key)
                elif service == 'nytimes_key':
                    return await self._validate_nytimes_combined(client, api_key)
                elif service == 'nytimes_secret':
                    return True  # Secret is validated together with key
                elif service == 'product_hunt_apikey':
                    return await self._validate_product_hunt_oauth(client, api_key)
                elif service == 'product_hunt_secret':
                    return True  # Secret is used for OAuth2 flow, not directly testable
                elif service == 'finnhub':
                    return await self._validate_finnhub(client, api_key)
                elif service == 'quandl':
                    return await self._validate_quandl(client, api_key)
                elif service == 'crunchbase':
                    return await self._validate_crunchbase(client, api_key)
                elif service == 'clearbit':
                    return await self._validate_clearbit(client, api_key)
                elif service == 'apollo':
                    return await self._validate_apollo(client, api_key)
                elif service == 'builtwith':
                    return await self._validate_builtwith(client, api_key)

                elif service == 'shodan':
                    return await self._validate_shodan(client, api_key)
                elif service == 'twitter' or service == 'x':
                    return await self._validate_twitter(client, api_key)
                elif service == 'linkedin':
                    return await self._validate_linkedin(client, api_key)
                elif service == 'startup_tracker':
                    return await self._validate_startup_tracker(client, api_key)
                elif service == 'bing_search':
                    return await self._validate_bing_search(client, api_key)
                elif service == 'google_custom_search':
                    return await self._validate_google_custom_search(client, api_key)
                elif service == 'google_custom_search_id':
                    return True  # This is just an ID, not a key
                elif service == 'guardian':
                    return await self._validate_guardian(client, api_key)

                elif service == 'stackoverflow':
                    return await self._validate_stackoverflow(client, api_key)
                elif service == 'product_hunt_secret':
                    return True  # OAuth secret, not directly testable
                elif service == 'fred':
                    return await self._validate_fred(client, api_key)
                elif service == 'mastodon_instance_url':
                    return True  # Just a URL, not a key
                elif service == 'mastodon_access_token':
                    return await self._validate_mastodon(client, api_key)
                elif service in ['reddit', 'hacker_news', 'indie_hackers', 'betalist']:
                    return True  # No API key needed, scraping only
                elif service == 'serpapi_engine':
                    return True  # This is just an engine name, not a key
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
        """Validate GitHub PAT token"""
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

    # Additional validation methods for new APIs
    async def _validate_mediastack(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate Mediastack API key"""
        try:
            response = await client.get(
                "http://api.mediastack.com/v1/news",
                params={"access_key": api_key, "limit": 1},
                timeout=5
            )
            return response.status_code == 200 and "error" not in response.json()
        except:
            return False

    async def _validate_currents(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate Currents API key"""
        try:
            response = await client.get(
                "https://api.currentsapi.services/v1/latest-news",
                headers={"Authorization": api_key},
                params={"language": "en", "page_size": 1},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False

    async def _validate_gitlab(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate GitLab API token"""
        try:
            response = await client.get(
                "https://gitlab.com/api/v4/user",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False

    async def _validate_finnhub(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate Finnhub API key"""
        try:
            response = await client.get(
                "https://finnhub.io/api/v1/quote",
                params={"symbol": "AAPL", "token": api_key},
                timeout=5
            )
            return response.status_code == 200 and "error" not in response.json()
        except:
            return False

    async def _validate_quandl(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate Quandl API key"""
        try:
            response = await client.get(
                "https://www.quandl.com/api/v3/datasets/WIKI/AAPL.json",
                params={"api_key": api_key, "limit": 1},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False

    async def _validate_crunchbase(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate Crunchbase API key"""
        try:
            response = await client.post(
                "https://api.crunchbase.com/api/v4/searches/organizations",
                headers={"X-cb-user-key": api_key},
                json={"field_ids": ["name"], "limit": 1},
                timeout=10
            )
            return response.status_code == 200
        except:
            return False

    async def _validate_clearbit(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate Clearbit API key"""
        try:
            response = await client.get(
                "https://company.clearbit.com/v2/companies/find",
                headers={"Authorization": f"Bearer {api_key}"},
                params={"domain": "clearbit.com"},
                timeout=5
            )
            return response.status_code in [200, 202]  # 202 is also valid for Clearbit
        except:
            return False

    async def _validate_apollo(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate Apollo API key"""
        try:
            response = await client.get(
                "https://api.apollo.io/v1/auth/health",
                headers={"X-Api-Key": api_key},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False

    async def _validate_builtwith(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate BuiltWith API key"""
        try:
            response = await client.get(
                "https://api.builtwith.com/v20/api.json",
                params={"KEY": api_key, "LOOKUP": "builtwith.com"},
                timeout=5
            )
            return response.status_code == 200 and "Error" not in response.text
        except:
            return False



    async def _validate_twitter(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate Twitter/X Bearer token"""
        try:
            response = await client.get(
                "https://api.twitter.com/2/users/me",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False

    async def _validate_linkedin(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate LinkedIn API token"""
        try:
            response = await client.get(
                "https://api.linkedin.com/v2/me",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False

    async def _validate_startup_tracker(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate custom Startup Tracker API key"""
        try:
            # This would be for a custom startup tracking API
            response = await client.get(
                "https://api.startup-tracker.com/v1/health",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False

    async def _validate_shodan(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate Shodan API key"""
        try:
            response = await client.get(
                "https://api.shodan.io/api-info",
                params={"key": api_key},
                timeout=10
            )
            if response.status_code == 200:
                # Check if response is valid JSON with expected fields
                data = response.json()
                return "query_credits" in data or "plan" in data
            return False
        except:
            return False

    async def _validate_bing_search(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate Bing Search API key"""
        try:
            response = await client.get(
                "https://api.bing.microsoft.com/v7.0/search",
                headers={"Ocp-Apim-Subscription-Key": api_key},
                params={"q": "test", "count": 1},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False

    async def _validate_google_custom_search(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate Google Custom Search API key"""
        try:
            # Need both API key and search engine ID for full validation
            # This is a basic API key validation
            response = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": api_key, "cx": "test", "q": "test"},
                timeout=5
            )
            # Even with invalid cx, a valid API key won't return 403
            return response.status_code != 403
        except:
            return False

    async def _validate_guardian(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate Guardian API key"""
        try:
            response = await client.get(
                "https://content.guardianapis.com/search",
                params={"api-key": api_key, "page-size": 1},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False



    async def _validate_stackoverflow(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate Stack Overflow API key"""
        try:
            response = await client.get(
                "https://api.stackexchange.com/2.3/questions",
                params={"site": "stackoverflow", "key": api_key, "pagesize": 1},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False

    async def _validate_fred(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate FRED (Federal Reserve Economic Data) API key"""
        try:
            response = await client.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={"series_id": "GDP", "api_key": api_key, "file_type": "json", "limit": 1},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False

    async def _validate_massive(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate Massive.com API key"""
        try:
            # Test with Massive.com dividends endpoint
            response = await client.get(
                "https://api.massive.com/v3/reference/dividends",
                params={"apiKey": api_key, "limit": 1},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return "status" in data and data.get("status") == "OK"
            return False
        except:
            return False

    async def _validate_nytimes_combined(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate NYTimes API key (requires both key and secret in config)"""
        try:
            # Get the secret from config
            nyt_secret = self.config.get('keys', {}).get('nytimes_secret', '')
            if not nyt_secret:
                return False
                
            # NYTimes uses key for API calls, secret for additional auth
            response = await client.get(
                "https://api.nytimes.com/svc/topstories/v2/home.json",
                params={"api-key": api_key},
                timeout=10
            )
            return response.status_code == 200
        except:
            return False

    async def _validate_product_hunt_oauth(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate Product Hunt OAuth2 token (requires both key and secret for OAuth)"""
        try:
            # Product Hunt uses OAuth2 Bearer token authentication
            response = await client.post(
                "https://api.producthunt.com/v2/api/graphql",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"query": "query { viewer { user { id } } }"},
                timeout=10
            )
            return response.status_code == 200 and "errors" not in response.json()
        except:
            return False

    async def _validate_mastodon(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Validate Mastodon access token"""
        try:
            # This would need the instance URL from config, but for now just basic validation
            # Mastodon tokens are typically validated against specific instances
            return len(api_key) > 10  # Basic token format check
        except:
            return False