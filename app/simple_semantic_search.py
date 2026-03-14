#!/usr/bin/env python3
"""
Simplified Semantic Search System for Market Intelligence
No external vector DB dependencies - uses local similarity search
"""

import asyncio
import json
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import yaml
import httpx
import numpy as np
from sentence_transformers import SentenceTransformer

from app.fetchers import (
    serpapi, newsapi, github, 
    news_sources, financial_apis, business_intelligence,
    community_sources, social_media, startup_tracker, shodan
)
from app.normalizer import normalize_item
from app.db import Database
from app.api_validator import APIKeyValidator
from app.query_optimizer import QueryOptimizer

logger = logging.getLogger(__name__)

class QueryType(Enum):
    COMPANY_ANALYSIS = "company_analysis"
    MARKET_TREND = "market_trend" 
    PRODUCT_RESEARCH = "product_research"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    FUNDING_INTELLIGENCE = "funding_intelligence"
    TECHNOLOGY_STACK = "technology_stack"
    NEWS_MONITORING = "news_monitoring"
    GENERAL_INTELLIGENCE = "general_intelligence"

@dataclass 
class SearchPlan:
    query_type: QueryType
    entities: List[str]
    keywords: List[str]
    sources: List[str]
    search_terms: List[str]
    financial_symbols: List[str]

class SimpleSemanticSearch:
    """Simplified semantic search without external vector databases"""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r") as fh:
            self.config = yaml.safe_load(fh)

        logger.info("Loading sentence transformer model...")
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.db = Database(self.config)
        self.query_optimizer = QueryOptimizer()
        self.api_validator = APIKeyValidator(self.config)
        self.document_embeddings = []
        self.documents = []

        # ── dynamic key helpers ───────────────────────────────────────────────
        self._keys = self.config.get("keys", {})

    # ── Key helpers (dynamic – reads from config at call time) ─────────────────
    def _key(self, *names: str) -> Optional[str]:
        """Return first non-empty key from the given config key names."""
        for name in names:
            v = self._keys.get(name, "")
            if v and str(v).strip():
                return str(v).strip()
        return None

    def _add_task(self, tasks: List[Dict[str, Any]], task_type: str, source: str, query: str, fetcher, *args, **kwargs) -> None:
        """Safely register a task coroutine without breaking the whole pipeline."""
        if not callable(fetcher):
            logger.warning(f"Fetcher not available for source '{source}'; skipping")
            return
        try:
            coro = fetcher(*args, **kwargs)
            tasks.append({
                "type": task_type,
                "source": source,
                "query": query,
                "coro": coro,
            })
        except Exception as e:
            logger.warning(f"Failed to create task for source '{source}' query '{query}': {e}")

    # ── Task builders ──────────────────────────────────────────────────────────
    async def _create_search_tasks(self, client: httpx.AsyncClient, search_terms: List[str]) -> List:
        tasks = []
        serp_key = self._key("serpapi")
        if serp_key:
            engine = self._keys.get("serpapi_engine", "google")
            for term in search_terms[:3]:
                tasks.append({
                    "type": "search_discovery", "source": "serpapi", "query": term,
                    "coro": serpapi.serp_search(client, serp_key, term, engine=engine),
                })
        return tasks

    async def _create_news_tasks(self, client: httpx.AsyncClient, search_terms: List[str]) -> List:
        tasks = []

        if k := self._key("newsapi"):
            for term in search_terms[:3]:
                tasks.append({
                    "type": "news_intelligence",
                    "source": "newsapi",
                    "query": term,
                    "coro": newsapi.search_newsapi(client, k, term),
                })

        if k := self._key("gnews"):
            for term in search_terms[:2]:
                tasks.append({
                    "type": "news_intelligence",
                    "source": "gnews",
                    "query": term,
                    "coro": news_sources.fetch_gnews(client, k, term),
                })

        if k := self._key("currents"):
            for term in search_terms[:2]:
                tasks.append({
                    "type": "news_intelligence",
                    "source": "currents",
                    "query": term,
                    "coro": news_sources.fetch_currents_api(client, k, term),
                })

        # Safe dynamic resolution to avoid AttributeError + un-awaited coroutine warnings
        guardian_fn = getattr(news_sources, "fetch_guardian_api", None) or getattr(news_sources, "fetch_guardian", None)
        if k := self._key("guardian"):
            if callable(guardian_fn):
                for term in search_terms[:2]:
                    tasks.append({
                        "type": "news_intelligence",
                        "source": "guardian",
                        "query": term,
                        "coro": guardian_fn(client, k, term),
                    })
            else:
                logger.warning("Guardian fetcher not found in news_sources; skipping")

        nytimes_fn = getattr(news_sources, "fetch_nytimes_api", None) or getattr(news_sources, "fetch_nytimes", None)
        if k := self._key("nytimes_key"):
            if callable(nytimes_fn):
                tasks.append({
                    "type": "news_intelligence",
                    "source": "nytimes",
                    "query": "technology",
                    "coro": nytimes_fn(client, k, "technology"),
                })
            else:
                logger.warning("NYTimes fetcher not found in news_sources; skipping")

        for term in search_terms[:2]:
            tasks.append({
                "type": "community_intelligence",
                "source": "hackernews",
                "query": term,
                "coro": community_sources.scrape_hackernews_search(client, term),
            })

        return tasks

    async def _create_github_tasks(self, client: httpx.AsyncClient, entities: List[str]) -> List:
        tasks = []
        # Use PAT token key name from config
        gh_key = self._key("github_personal_access_token")
        if not gh_key:
            return tasks

        org_map = {
            "NVIDIA": "nvidia", "OPENAI": "openai", "MICROSOFT": "microsoft",
            "GOOGLE": "google", "VERCEL": "vercel", "STRIPE": "stripe",
            "AMAZON": "aws", "META": "facebook", "NETFLIX": "netflix",
        }
        orgs = [org_map[e] for e in entities if e in org_map]
        if not orgs:
            orgs = self.config.get("sources", {}).get("github_orgs", ["openai", "vercel"])[:4]

        for org in orgs[:4]:
            tasks.append({"type": "github_intelligence", "source": "github", "query": org,
                          "coro": github.fetch_org_repos(client, gh_key, org)})

        # Trending repos
        tasks.append({"type": "github_intelligence", "source": "github_trending", "query": "ai",
                      "coro": github.fetch_trending_repos(client, gh_key, language="python", days=7)})
        return tasks

    async def _create_financial_tasks(self, client: httpx.AsyncClient, symbols: List[str]) -> List:
        tasks = []

        if k := self._key("alpha_vantage"):
            for sym in symbols[:3]:
                self._add_task(tasks, "financial_intelligence", "alpha_vantage", sym,
                               financial_apis.fetch_alpha_vantage_company_overview, client, k, sym)
            if symbols:
                joined_symbols = ",".join(symbols[:3])
                self._add_task(tasks, "financial_intelligence", "alpha_vantage_news", joined_symbols,
                               financial_apis.fetch_company_news_alpha_vantage, client, k, joined_symbols)

        if k := self._key("massive"):
            joined_symbols = ",".join(symbols[:3])
            self._add_task(tasks, "financial_intelligence", "massive", joined_symbols,
                           financial_apis.fetch_massive_dividends, client, k, symbols[:3])

            massive_market_fn = getattr(financial_apis, "fetch_massive_market_data", None)
            if callable(massive_market_fn):
                self._add_task(tasks, "financial_intelligence", "massive_market", joined_symbols,
                               massive_market_fn, client, k, symbols[:3])

        # Free – Yahoo Finance
        yahoo_fn = getattr(financial_apis, "fetch_yahoo_finance_quote", None)
        for sym in symbols[:3]:
            if callable(yahoo_fn):
                self._add_task(tasks, "financial_intelligence", "yahoo_finance", sym, yahoo_fn, client, sym)

        if symbols and not callable(yahoo_fn):
            logger.info("Yahoo finance fetcher not implemented; skipped yahoo_finance tasks")

        return tasks

    async def _create_community_tasks(self, client: httpx.AsyncClient, search_terms: List[str]) -> List:
        tasks = []
        subreddits = self.config.get("sources", {}).get("subreddits", ["technology", "startups"])

        # Reddit – no API key
        for sub in subreddits[:4]:
            tasks.append({"type": "community_intelligence", "source": "reddit", "query": sub,
                          "coro": community_sources.scrape_reddit_posts(client, sub)})

        # Mastodon
        if k := self._key("mastodon_access_token"):
            instance = self._keys.get("mastodon_instance_url", "mastodon.social")
            if "urn:ietf" in instance:
                instance = "mastodon.social"
            tasks.append({"type": "community_intelligence", "source": "mastodon",
                          "query": "technology",
                          "coro": community_sources.fetch_mastodon_timeline(client, k, instance, hashtag="ai")})

        # Stack Overflow – no key
        for term in search_terms[:2]:
            tasks.append({"type": "community_intelligence", "source": "stackoverflow", "query": term,
                          "coro": community_sources.fetch_stackoverflow_questions(client, term)})

        return tasks

    async def _create_business_intelligence_tasks(self, client: httpx.AsyncClient, entities: List[str]) -> List:
        tasks = []

        if k := self._key("apollo"):
            for entity in entities[:2]:
                domain = f"{entity.lower()}.com"
                tasks.append({"type": "business_intelligence", "source": "apollo", "query": domain,
                               "coro": business_intelligence.fetch_apollo_contacts(client, k, domain)})

        if k := self._key("gitlab"):
            for entity in entities[:2]:
                tasks.append({"type": "business_intelligence", "source": "gitlab", "query": entity,
                               "coro": business_intelligence.fetch_gitlab_projects(client, k, entity)})

        if k := self._key("shodan"):
            for entity in entities[:1]:
                tasks.append({"type": "security_intelligence", "source": "shodan", "query": entity,
                               "coro": shodan.search_shodan(client, k, entity)})

        return tasks

    async def _create_social_media_tasks(self, client: httpx.AsyncClient, search_terms: List[str]) -> List:
        tasks = []

        if k := self._key("twitter_bearer_token"):
            for term in search_terms[:2]:
                self._add_task(tasks, "social_media", "twitter", term,
                               social_media.fetch_twitter_tweets, client, k, term)
        else:
            for term in search_terms[:1]:
                self._add_task(tasks, "social_media", "x_scraper", term,
                               social_media.scrape_x_tweets, client, term)

        if k := self._key("linkedin_access_token"):
            for term in search_terms[:2]:
                self._add_task(tasks, "social_media", "linkedin_company", term,
                               social_media.search_linkedin_companies, client, k, term)

        return tasks

    async def _create_startup_tasks(self, client: httpx.AsyncClient, entities: List[str]) -> List:
        tasks = []

        if k := self._key("startup_tracker"):
            for entity in entities[:2]:
                self._add_task(tasks, "startup_intelligence", "startup_tracker", entity,
                               startup_tracker.fetch_startup_tracker_companies, client, k, entity)

        for entity in entities[:2]:
            self._add_task(tasks, "startup_intelligence", "angellist", entity,
                           startup_tracker.scrape_angellist_startups, client, entity)
            self._add_task(tasks, "startup_intelligence", "crunchbase_news", entity,
                           startup_tracker.scrape_crunchbase_news, client, entity)

        self._add_task(tasks, "startup_intelligence", "techcrunch", "startups",
                       startup_tracker.fetch_techcrunch_startups, client, "startups")

        return tasks

    async def _create_security_tasks(self, client: httpx.AsyncClient, search_terms: List[str], entities: List[str]) -> List:
        tasks = []

        if k := self._key("shodan"):
            for term in (search_terms[:1] + entities[:1]):
                self._add_task(tasks, "security_intelligence", "shodan", term,
                               shodan.search_shodan, client, k, term)

            shodan_exploit_fn = getattr(shodan, "search_shodan_exploits", None)
            if callable(shodan_exploit_fn):
                for term in search_terms[:1]:
                    self._add_task(tasks, "security_intelligence", "shodan_exploits", term,
                                   shodan_exploit_fn, client, k, term)

        return tasks

    async def execute_search(self, plan: SearchPlan) -> Dict[str, Any]:
        """Execute the search plan"""
        results = {
            'search_discovery': {},
            'news_intelligence': {}, 
            'github_intelligence': {},
            'financial_intelligence': {},
            'business_intelligence': {},
            'social_media': {},
            'community_intelligence': {},
            'startup_intelligence': {},
            'security_intelligence': {}
        }
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            tasks = []

            async def _safe_extend(source_name: str, builder_coro):
                try:
                    built_tasks = await builder_coro
                    if built_tasks:
                        tasks.extend(built_tasks)
                except Exception as e:
                    logger.error(f"Task builder failed for {source_name}: {e}")
            
            # Search discovery (SerpAPI)
            if 'search_discovery' in plan.sources:
                await _safe_extend('search_discovery', self._create_search_tasks(client, plan.search_terms))
            
            # News intelligence
            if 'news_intelligence' in plan.sources:
                await _safe_extend('news_intelligence', self._create_news_tasks(client, plan.search_terms))
            
            # GitHub intelligence  
            if 'github_intelligence' in plan.sources:
                await _safe_extend('github_intelligence', self._create_github_tasks(client, plan.entities))
            
            # Financial intelligence
            if 'financial_intelligence' in plan.sources:
                await _safe_extend('financial_intelligence', self._create_financial_tasks(client, plan.financial_symbols))

            # Business intelligence
            if 'business_intelligence' in plan.sources:
                await _safe_extend('business_intelligence', self._create_business_intelligence_tasks(client, plan.entities))

            # Social media intelligence
            if 'social_media' in plan.sources:
                await _safe_extend('social_media', self._create_social_media_tasks(client, plan.search_terms))

            # Community intelligence
            if 'community_intelligence' in plan.sources:
                await _safe_extend('community_intelligence', self._create_community_tasks(client, plan.search_terms))

            # Startup intelligence
            if 'startup_intelligence' in plan.sources:
                await _safe_extend('startup_intelligence', self._create_startup_tasks(client, plan.entities))

            # Security intelligence
            if 'security_intelligence' in plan.sources:
                await _safe_extend('security_intelligence', self._create_security_tasks(client, plan.search_terms, plan.entities))
            
            # Execute all tasks
            if tasks:
                # Extract coroutines and metadata
                coroutines = []
                task_metadata = []
                
                for task in tasks:
                    coroutines.append(task['coro'])
                    task_metadata.append({
                        'type': task['type'],
                        'source': task['source'],
                        'query': task['query']
                    })
                
                # Execute coroutines
                coro_results = await asyncio.gather(*coroutines, return_exceptions=True)
                
                # Combine results with metadata
                task_results = []
                for i, result in enumerate(coro_results):
                    if isinstance(result, Exception):
                        task_results.append(result)
                    else:
                        combined_result = task_metadata[i].copy()
                        combined_result['data'] = result
                        task_results.append(combined_result)
                
                results = self._process_task_results(task_results)
        
        return results

    def _process_task_results(self, task_results: List) -> Dict[str, Any]:
        """Process and organize task results"""
        organized_results = {
            'search_discovery': {},
            'news_intelligence': {},
            'github_intelligence': {},
            'financial_intelligence': {},
            'business_intelligence': {},
            'social_media': {},
            'community_intelligence': {},
            'startup_intelligence': {},
            'security_intelligence': {}
        }
        
        successful_count = 0
        total_count = len(task_results)
        
        for result in task_results:
            if isinstance(result, Exception):
                logger.error(f"Task failed: {result}")
                continue
                
            if not isinstance(result, dict) or 'type' not in result:
                continue
            
            result_type = result['type']
            source = result.get('source', 'unknown')
            query = result.get('query', '')
            data = result.get('data', [])
            
            # Normalize data
            normalized_data = []
            if isinstance(data, list):
                for item in data:
                    try:
                        normalized = normalize_item(source, item)
                        normalized_data.append(normalized)
                    except Exception as e:
                        logger.error(f"Normalization error: {e}")
            elif isinstance(data, dict) and data:
                try:
                    normalized = normalize_item(source, data)
                    normalized_data = [normalized]
                except Exception as e:
                    logger.error(f"Normalization error: {e}")
            
            # Store results
            if result_type in organized_results:
                if source not in organized_results[result_type]:
                    organized_results[result_type][source] = {}
                organized_results[result_type][source][query] = normalized_data
                successful_count += 1
        
        # Add metadata
        organized_results['_metadata'] = {
            'total_tasks': total_count,
            'successful_tasks': successful_count,
            'success_rate': successful_count / total_count if total_count > 0 else 0
        }
        
        return organized_results

    async def validate_apis(self) -> bool:
        """Validate API keys before starting"""
        logger.info("🔍 Validating API keys...")
        
        results = await self.api_validator.validate_all_keys()
        valid_keys = self.api_validator.get_valid_keys()
        invalid_keys = self.api_validator.get_invalid_keys()
        
        if valid_keys:
            logger.info(f"✅ Valid APIs: {', '.join(valid_keys)}")
        
        if invalid_keys:
            logger.warning(f"⚠️  Invalid APIs: {', '.join(invalid_keys)}")
        
        # Need at least one search API
        search_apis = ['serpapi', 'newsapi', 'gnews']
        has_search = any(api in valid_keys for api in search_apis)
        
        if not has_search:
            logger.error("❌ No valid search APIs available")
            return False
        
        return True

    async def plan_search(self, query: str) -> SearchPlan:
        """Create intelligent search plan"""
        
        # Use query optimizer for better search terms
        optimized = self.query_optimizer.optimize_query(query)
        
        # Determine query type
        query_type = self._classify_query(query)
        
        # Extract entities and keywords
        entities = self._extract_entities(query)
        keywords = optimized.get('keywords', [])
        
        # Plan data sources based on query type
        sources = self._plan_sources(query_type)
        
        # Generate search terms
        search_terms = self._generate_search_terms(query, entities, keywords)
        
        # Map to financial symbols if relevant
        financial_symbols = self._map_to_symbols(entities)
        
        plan = SearchPlan(
            query_type=query_type,
            entities=entities,
            keywords=keywords,
            sources=sources,
            search_terms=search_terms,
            financial_symbols=financial_symbols
        )
        
        logger.info(f"Query plan: {query_type.value}, Sources: {sources}")
        return plan

    def _classify_query(self, query: str) -> QueryType:
        """Classify query type using keyword matching"""
        query_lower = query.lower()
        
        # Company-specific analysis
        if any(word in query_lower for word in ['nvidia', 'openai', 'microsoft', 'google', 'apple']):
            return QueryType.COMPANY_ANALYSIS
        
        # Funding and investment queries
        if any(word in query_lower for word in ['funding', 'investment', 'round', 'venture', 'capital']):
            return QueryType.FUNDING_INTELLIGENCE
        
        # Market trend queries
        if any(word in query_lower for word in ['market', 'trend', 'growth', 'industry']):
            return QueryType.MARKET_TREND
        
        # Product research
        if any(word in query_lower for word in ['product', 'launch', 'announcement', 'release']):
            return QueryType.PRODUCT_RESEARCH
        
        # Competitor analysis
        if any(word in query_lower for word in ['competitor', 'competition', 'vs', 'compare']):
            return QueryType.COMPETITOR_ANALYSIS
        
        return QueryType.GENERAL_INTELLIGENCE

    def _extract_entities(self, query: str) -> List[str]:
        """Extract company names and key entities"""
        # Known companies - could be enhanced with NLP
        companies = ['nvidia', 'openai', 'microsoft', 'google', 'apple', 'amazon', 'tesla', 'meta', 
                    'stripe', 'vercel', 'anthropic', 'aws', 'azure']
        entities = []
        
        query_lower = query.lower()
        
        # Check for known companies first
        for company in companies:
            if company in query_lower:
                entities.append(company.upper())
        
        # If no specific companies found, extract generic business entities from query context
        if not entities:
            # For business/funding/startup queries, use relevant tech companies
            if any(term in query_lower for term in ['startup', 'funding', 'venture', 'investment', 'business']):
                entities.extend(['NVIDIA', 'OPENAI', 'STRIPE'])  # Major tech/AI companies for business context
            # For product/tech queries, use major tech companies  
            elif any(term in query_lower for term in ['product', 'tech', 'software', 'development', 'api']):
                entities.extend(['GOOGLE', 'MICROSOFT', 'VERCEL'])
            # For AI/ML queries 
            elif any(term in query_lower for term in ['ai', 'artificial', 'machine learning', 'ml', 'neural']):
                entities.extend(['NVIDIA', 'OPENAI', 'MICROSOFT'])
            # Default fallback for other queries
            else:
                entities.extend(['GOOGLE', 'MICROSOFT'])  # Major companies with broad business data
        
        return entities

    def _plan_sources(self, query_type: QueryType) -> List[str]:
        """Plan which data sources to use based on query type"""
        base_sources = ['search_discovery', 'news_intelligence', 'community_intelligence']
        
        if query_type in [QueryType.COMPANY_ANALYSIS, QueryType.FUNDING_INTELLIGENCE]:
            base_sources.extend(['financial_intelligence', 'github_intelligence', 'business_intelligence', 'startup_intelligence', 'social_media'])
        elif query_type == QueryType.TECHNOLOGY_STACK:
            base_sources.extend(['github_intelligence', 'business_intelligence', 'security_intelligence'])
        elif query_type == QueryType.MARKET_TREND:
            base_sources.extend(['financial_intelligence', 'social_media', 'startup_intelligence'])
        elif query_type == QueryType.COMPETITOR_ANALYSIS:
            base_sources.extend(['business_intelligence', 'financial_intelligence', 'social_media', 'startup_intelligence', 'security_intelligence'])
        elif query_type == QueryType.PRODUCT_RESEARCH:
            base_sources.extend(['github_intelligence', 'community_intelligence', 'social_media'])
        else:
            # Default for unknown query types
            base_sources.extend(['business_intelligence', 'startup_intelligence'])
            
        return base_sources

    def _generate_search_terms(self, query: str, entities: List[str], keywords: List[str]) -> List[str]:
        """Generate optimized search terms"""
        terms = [query]
        
        # Add entity-specific terms
        for entity in entities:
            terms.append(f"{entity} news")
            terms.append(f"{entity} analysis")
        
        # Add keyword combinations
        if len(keywords) >= 2:
            terms.append(" ".join(keywords[:3]))
        
        return terms[:5]  # Limit to prevent rate limiting

    def _map_to_symbols(self, entities: List[str]) -> List[str]:
        """Map company names to stock symbols"""
        symbol_map = {
            'NVIDIA': 'NVDA',
            'MICROSOFT': 'MSFT', 
            'GOOGLE': 'GOOGL',
            'APPLE': 'AAPL',
            'AMAZON': 'AMZN',
            'TESLA': 'TSLA',
            'META': 'META'
        }
        
        symbols = []
        for entity in entities:
            if entity in symbol_map:
                symbols.append(symbol_map[entity])
        
        # Add default tech symbols if none found
        if not symbols:
            symbols = ['NVDA', 'GOOGL', 'MSFT']
        
        return symbols

    async def comprehensive_search(self, query: str) -> Dict[str, Any]:
        """Main search interface"""
        logger.info(f"Starting comprehensive search for: {query}")
        
        try:
            # Validate APIs first
            if not await self.validate_apis():
                return {
                    'error': 'No valid APIs available',
                    'query': query,
                    'status': 'failed'
                }
            
            # Create search plan
            plan = await self.plan_search(query)
            
            # Execute search
            raw_results = await self.execute_search(plan)
            
            # Generate final response
            final_results = await self._generate_final_response(query, plan, raw_results)
            
            # Save to database
            await self._save_search_session(final_results)
            
            # Save JSON file
            await self._save_json_file(final_results)
            
            return final_results
            
        except Exception as e:
            logger.error(f"Comprehensive search failed: {e}")
            return {
                'error': str(e),
                'query': query,
                'status': 'failed'
            }

    async def _generate_final_response(self, query: str, plan: SearchPlan, raw_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured final response"""
        
        # Count successful sources and documents
        successful_sources = 0
        total_documents = 0
        
        for source_type, source_data in raw_results.items():
            if source_type.startswith('_'):
                continue
            if source_data:
                successful_sources += 1
                for source_name, query_results in source_data.items():
                    for query_key, documents in query_results.items():
                        if isinstance(documents, list):
                            total_documents += len(documents)
                        elif documents:
                            total_documents += 1
        
        # Extract search terms used
        search_terms_used = len(plan.search_terms)
        
        # Generate insights and recommendations
        insights = [
            f"Successfully gathered data from {successful_sources} different sources",
        ]
        
        if plan.financial_symbols:
            insights.append(f"Financial analysis included symbols: {', '.join(plan.financial_symbols)}")
        
        recommendations = [
            "Review financial metrics and recent news for comprehensive analysis",
            "Check competitor activity and market positioning"
        ]
        
        # Build final response
        final_response = {
            'query': query,
            'query_type': plan.query_type.value,
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'plan': {
                'entities': plan.entities,
                'keywords': plan.keywords,
                'sources': plan.sources,
                'search_terms': plan.search_terms,
                'financial_symbols': plan.financial_symbols
            },
            'summary': {
                'total_sources_queried': len(plan.sources),
                'successful_sources': successful_sources,
                'total_documents': total_documents,
                'search_terms_used': search_terms_used
            },
            'insights': insights,
            'recommendations': recommendations,
            'raw_data': raw_results
        }
        
        return final_response

    async def _save_search_session(self, results: Dict[str, Any]):
        """Save search session to database"""
        try:
            await self.db.init_pool()
            
            doc = {
                'source': 'semantic_search',
                'title': f"Semantic Search: {results.get('query', 'Unknown')}",
                'url': f"internal://semantic_search_{int(datetime.now().timestamp())}",
                'content': json.dumps(results.get('summary', {}), indent=2),
                'published_at': datetime.now(),
                'metadata': {
                    'query_type': results.get('query_type'),
                    'status': results.get('status'),
                    'total_documents': results.get('summary', {}).get('total_documents', 0)
                },
                'content_hash': str(hash(str(results.get('summary', {}))))[:64]
            }
            
            await self.db.save_document(doc)
            logging.getLogger(__name__).info("✅ Search session saved to database")
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to save search session: {e}")

    async def _save_json_file(self, results: Dict[str, Any]) -> str:
        """Save results to JSON file"""
        try:
            # Create search_results directory
            os.makedirs('search_results', exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            query_type = results.get('query_type', 'search')
            query_slug = "".join(c.lower() if c.isalnum() else "_" for c in results.get('query', 'query'))[:50]
            
            filename = f"search_results/{timestamp}_{query_type}_{query_slug}.json"
            
            # Save file
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"JSON result saved to: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Failed to save JSON file: {e}")
            return ""

# Convenience function
async def semantic_search(query: str) -> Dict[str, Any]:
    """Simple interface for semantic search"""
    engine = SimpleSemanticSearch()
    return await engine.comprehensive_search(query)