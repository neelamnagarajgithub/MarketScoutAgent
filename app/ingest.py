# app/ingest.py
import asyncio
import httpx
from aiolimiter import AsyncLimiter
import yaml
from app.db import Database
from app.normalizer import normalize_item
from app.fetchers import (
    serpapi, newsapi, github, npm_pypi, rss, generic_scraper,
    news_sources, search_apis, business_intelligence, 
    community_sources, financial_apis
)
from typing import List
from app.extractor import compute_hash
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Ingestor:
    def __init__(self, config_path="config.yaml", config=None):
        from app.config_loader import ConfigLoader
        # Support both file path and direct config dict
        if config is None:
            self.config = ConfigLoader.load(config_path)
        else:
            self.config = config
        self.db = Database(self.config)
        self.concurrency = self.config['fetch'].get('concurrency', 8)
        self.rate_limit = self.config['fetch'].get('rate_limit_per_sec', 5)
        self.limiter = AsyncLimiter(self.rate_limit, time_period=1)

    async def init(self):
        await self.db.init_models()

    async def _gather_with_limit(self, tasks):
        sem = asyncio.Semaphore(self.concurrency)
        results = []

        async def sem_task(coro):
            async with sem:
                async with self.limiter:
                    return await coro

        wrapped = [sem_task(t) for t in tasks]
        return await asyncio.gather(*wrapped, return_exceptions=True)

    async def run_once(self):
        logger.info("Starting comprehensive market intelligence ingestion")
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            tasks = []

            # 1) Search Discovery APIs
            await self._add_search_discovery_tasks(client, tasks)
            
            # 2) News & Market Intelligence
            await self._add_news_intelligence_tasks(client, tasks)
            
            # 3) Tech/Product Intelligence
            await self._add_tech_product_tasks(client, tasks)
            
            # 4) Business Intelligence
            await self._add_business_intelligence_tasks(client, tasks)
            
            # 5) Community & Social Intelligence
            await self._add_community_tasks(client, tasks)
            
            # 6) Financial Intelligence
            await self._add_financial_tasks(client, tasks)
            
            # 7) RSS Feeds
            await self._add_rss_tasks(tasks)

            logger.info(f"Running {len(tasks)} data collection tasks")
            
            # Run all discovery tasks
            raw_results = await self._gather_with_limit(tasks)

            # Process and normalize results
            normalized = []
            for i, res in enumerate(raw_results):
                if isinstance(res, Exception):
                    logger.error(f"Task {i} failed: {res}")
                    continue
                    
                if isinstance(res, list):
                    for item in res:
                        try:
                            doc = normalize_item("discovery", item)
                            normalized.append(doc)
                        except Exception as e:
                            logger.error(f"Normalization error: {e}")
                elif isinstance(res, dict) and res:
                    try:
                        doc = normalize_item("discovery", res)
                        normalized.append(doc)
                    except Exception as e:
                        logger.error(f"Normalization error: {e}")

            logger.info(f"Normalized {len(normalized)} documents")

            # 8) Content Scraping
            scrape_tasks = []
            for doc in normalized[:100]:  # Limit scraping to avoid overload
                url = doc.get("url")
                if url and self._should_scrape_url(url):
                    scrape_tasks.append(generic_scraper.scrape_url(client, url))
            
            if scrape_tasks:
                logger.info(f"Scraping {len(scrape_tasks)} URLs")
                scraped = await self._gather_with_limit(scrape_tasks)
                
                # Process scraped content
                for s in scraped:
                    if isinstance(s, Exception):
                        continue
                    try:
                        doc = normalize_item("scraped", s)
                        await self.db.save_document(doc)
                    except Exception as e:
                        logger.error(f"DB save error: {e}")

            # 9) Save discovery documents
            for doc in normalized:
                try:
                    await self.db.save_document(doc)
                except Exception as e:
                    logger.error(f"DB save error: {e}")

            logger.info("Ingestion run completed")

    async def _add_search_discovery_tasks(self, client, tasks):
        """Add search & discovery API tasks"""
        queries = [
            "site:github.com product launch 2024",
            "startup funding announcement",
            "new SaaS platform launch",
            "AI company product release",
            "developer tools launch"
        ]
        
        # SerpAPI
        serp_key = self.config['keys'].get('serpapi')
        if serp_key:
            for q in queries:
                tasks.append(serpapi.serp_search(client, serp_key, q, 
                    engine=self.config['keys'].get('serpapi_engine','google')))

        # Bing Search
        bing_key = self.config['keys'].get('bing_search')
        if bing_key:
            for q in queries:
                tasks.append(search_apis.fetch_bing_search(client, bing_key, q))

        # Google Custom Search
        google_key = self.config['keys'].get('google_custom_search')
        google_cx = self.config['keys'].get('google_custom_search_id')
        if google_key and google_cx:
            for q in queries:
                tasks.append(search_apis.fetch_google_custom_search(client, google_key, google_cx, q))

    async def _add_news_intelligence_tasks(self, client, tasks):
        """Add news & market intelligence tasks"""
        news_queries = [
            "startup launch",
            "product announcement",
            "funding round",
            "AI company",
            "SaaS platform"
        ]
        
        # NewsAPI
        news_key = self.config['keys'].get('newsapi')
        if news_key:
            for q in news_queries:
                tasks.append(newsapi.search_newsapi(client, news_key, q))

        # GNews
        gnews_key = self.config['keys'].get('gnews')
        if gnews_key:
            for q in news_queries:
                tasks.append(news_sources.fetch_gnews(client, gnews_key, q))

        # Mediastack
        mediastack_key = self.config['keys'].get('mediastack')
        if mediastack_key:
            for q in news_queries:
                tasks.append(news_sources.fetch_mediastack(client, mediastack_key, q))

        # Currents API
        currents_key = self.config['keys'].get('currents')
        if currents_key:
            for q in news_queries:
                tasks.append(news_sources.fetch_currents_api(client, currents_key, q))

    async def _add_tech_product_tasks(self, client, tasks):
        """Add tech/product intelligence tasks"""
        # GitHub organizations
        gh_key = self.config['keys'].get('github')
        if gh_key:
            orgs = self.config.get('sources', {}).get('github_orgs', ["openai", "vercel"])
            for org in orgs:
                tasks.append(github.fetch_org_repos(client, gh_key, org))

        # NPM / PyPI popular packages
        popular_npm = ["react", "vue", "angular", "express", "next"]
        popular_python = ["tensorflow", "pytorch", "fastapi", "django", "requests"]
        
        for pkg in popular_npm[:3]:  # Limit to avoid rate limits
            tasks.append(npm_pypi.fetch_npm_package(client, pkg))
            
        for pkg in popular_python[:3]:
            tasks.append(npm_pypi.fetch_pypi_package(client, pkg))

    async def _add_business_intelligence_tasks(self, client, tasks):
        """Add business intelligence tasks"""
        # Crunchbase
        cb_key = self.config['keys'].get('crunchbase')
        if cb_key:
            companies = ["OpenAI", "Anthropic", "Vercel", "Stripe", "Replicate"]
            for company in companies:
                tasks.append(business_intelligence.fetch_crunchbase_organizations(client, cb_key, company))

        # BuiltWith
        bw_key = self.config['keys'].get('builtwith')
        if bw_key:
            domains = ["openai.com", "vercel.com", "stripe.com", "github.com"]
            for domain in domains:
                tasks.append(business_intelligence.fetch_builtwith_domain(client, bw_key, domain))

    async def _add_community_tasks(self, client, tasks):
        """Add community & social intelligence tasks"""
        # Hacker News
        tasks.append(community_sources.fetch_hackernews_stories(client, "topstories", 30))
        tasks.append(community_sources.fetch_hackernews_stories(client, "newstories", 20))

        # Reddit
        reddit_id = self.config['keys'].get('reddit_client_id')
        reddit_secret = self.config['keys'].get('reddit_client_secret')
        reddit_ua = self.config['keys'].get('reddit_user_agent', 'MarketScoutBot/1.0')
        
        if reddit_id and reddit_secret:
            subreddits = self.config.get('sources', {}).get('subreddits', ['startups', 'entrepreneur'])
            for sub in subreddits:
                tasks.append(community_sources.fetch_reddit_posts(client, reddit_id, reddit_secret, reddit_ua, sub))

    async def _add_financial_tasks(self, client, tasks):
        """Add financial intelligence tasks"""
        # Alpha Vantage
        av_key = self.config['keys'].get('alpha_vantage')
        if av_key:
            symbols = ["MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]
            for symbol in symbols:
                tasks.append(financial_apis.fetch_alpha_vantage_company_overview(client, av_key, symbol))
                
            # Company news
            tasks.append(financial_apis.fetch_company_news_alpha_vantage(client, av_key, ",".join(symbols)))

        # Polygon.io
        polygon_key = self.config['keys'].get('polygon')
        if polygon_key:
            tickers = ["MSFT", "GOOGL", "AMZN"]
            for ticker in tickers:
                tasks.append(financial_apis.fetch_polygon_company_details(client, polygon_key, ticker))

    async def _add_rss_tasks(self, tasks):
        """Add RSS feed tasks"""
        rss_feeds = self.config.get('sources', {}).get('rss_feeds', [
            "https://blog.openai.com/rss/",
            "https://github.blog/feed/"
        ])
        
        for feed in rss_feeds:
            tasks.append(asyncio.to_thread(rss.fetch_rss_feed, feed, 10))

    def _should_scrape_url(self, url: str) -> bool:
        """Determine if URL should be scraped"""
        skip_domains = ['twitter.com', 'x.com', 'youtube.com', 'linkedin.com', 'facebook.com']
        return not any(domain in url.lower() for domain in skip_domains)

    async def run_periodic(self, interval_seconds=3600):
        await self.init()
        while True:
            logger.info(f"Starting ingestion run at {time.ctime()}")
            try:
                await self.run_once()
            except Exception as e:
                logger.error(f"Ingestion run failed: {e}")
            logger.info(f"Sleeping {interval_seconds} seconds")
            await asyncio.sleep(interval_seconds)