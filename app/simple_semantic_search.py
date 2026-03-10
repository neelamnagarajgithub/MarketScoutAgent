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
        # Load config
        with open(config_path, "r") as fh:
            self.config = yaml.safe_load(fh)
        
        # Initialize embedding model
        logger.info("Loading sentence transformer model...")
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        
        # Initialize database
        self.db = Database(self.config)
        
        # Initialize query optimizer for better search quality
        self.query_optimizer = QueryOptimizer()
        
        # API validation
        self.api_validator = APIKeyValidator(self.config)
        
        # In-memory document store for semantic search
        self.document_embeddings = []
        self.documents = []
        
        # Source priorities (higher = more reliable)
        self.source_priorities = {
            'serpapi': 9,
            'newsapi': 8,
            'gnews': 7,
            'github': 6,
            'alpha_vantage': 5
        }

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
            
            # Search discovery (SerpAPI)
            if 'search_discovery' in plan.sources:
                tasks.extend(await self._create_search_tasks(client, plan.search_terms))
            
            # News intelligence
            if 'news_intelligence' in plan.sources:
                tasks.extend(await self._create_news_tasks(client, plan.search_terms))
            
            # GitHub intelligence  
            if 'github_intelligence' in plan.sources:
                tasks.extend(await self._create_github_tasks(client, plan.entities))
            
            # Financial intelligence
            if 'financial_intelligence' in plan.sources:
                tasks.extend(await self._create_financial_tasks(client, plan.financial_symbols))

            # Business intelligence
            if 'business_intelligence' in plan.sources:
                tasks.extend(await self._create_business_intelligence_tasks(client, plan.entities))

            # Social media intelligence
            if 'social_media' in plan.sources:
                tasks.extend(await self._create_social_media_tasks(client, plan.search_terms))

            # Community intelligence
            if 'community_intelligence' in plan.sources:
                tasks.extend(await self._create_community_tasks(client, plan.search_terms))

            # Startup intelligence
            if 'startup_intelligence' in plan.sources:
                tasks.extend(await self._create_startup_tasks(client, plan.entities))

            # Security intelligence
            if 'security_intelligence' in plan.sources:
                tasks.extend(await self._create_security_tasks(client, plan.search_terms, plan.entities))
            
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

    async def _create_search_tasks(self, client: httpx.AsyncClient, search_terms: List[str]) -> List:
        """Create search discovery tasks"""
        tasks = []
        serp_key = self.config.get('keys', {}).get('serpapi')
        
        if serp_key:
            for term in search_terms[:3]:  # Limit to prevent rate limiting
                tasks.append({
                    'type': 'search_discovery',
                    'source': 'serpapi',
                    'query': term,
                    'coro': serpapi.serp_search(client, serp_key, term)
                })
        
        return tasks

    async def _create_news_tasks(self, client: httpx.AsyncClient, search_terms: List[str]) -> List:
        """Create news intelligence tasks"""
        tasks = []
        
        # NewsAPI
        newsapi_key = self.config.get('keys', {}).get('newsapi')
        if newsapi_key:
            for term in search_terms[:3]:
                tasks.append({
                    'type': 'news_intelligence', 
                    'source': 'newsapi',
                    'query': term,
                    'coro': newsapi.search_newsapi(client, newsapi_key, term)
                })
        
        # GNews
        gnews_key = self.config.get('keys', {}).get('gnews')
        if gnews_key:
            for term in search_terms[:2]:
                tasks.append({
                    'type': 'news_intelligence',
                    'source': 'gnews', 
                    'query': term,
                    'coro': news_sources.fetch_gnews(client, gnews_key, term)
                })

        # Mediastack
        mediastack_key = self.config.get('keys', {}).get('mediastack')
        if mediastack_key:
            for term in search_terms[:2]:
                tasks.append({
                    'type': 'news_intelligence',
                    'source': 'mediastack',
                    'query': term,
                    'coro': news_sources.fetch_mediastack(client, mediastack_key, term)
                })

        # Currents
        currents_key = self.config.get('keys', {}).get('currents')
        if currents_key:
            for term in search_terms[:2]:
                tasks.append({
                    'type': 'news_intelligence',
                    'source': 'currents',
                    'query': term,
                    'coro': news_sources.fetch_currents_api(client, currents_key, term)
                })
        
        return tasks

    async def _create_github_tasks(self, client: httpx.AsyncClient, entities: List[str]) -> List:
        """Create GitHub intelligence tasks"""
        tasks = []
        gh_key = self.config.get('keys', {}).get('github_personal_access_token')
        
        if gh_key:
            # Map entities to likely GitHub orgs
            org_mapping = {
                'NVIDIA': 'nvidia',
                'OPENAI': 'openai', 
                'MICROSOFT': 'microsoft',
                'GOOGLE': 'google',
                'VERCEL': 'vercel',
                'STRIPE': 'stripe'
            }
            
            orgs = []
            for entity in entities:
                if entity in org_mapping:
                    orgs.append(org_mapping[entity])
            
            # Add default orgs if none found
            if not orgs:
                orgs = ['openai', 'vercel', 'stripe', 'aws']
            
            for org in orgs[:4]:  # Limit API calls
                tasks.append({
                    'type': 'github_intelligence',
                    'source': 'github',
                    'query': org,
                    'coro': github.fetch_org_repos(client, gh_key, org)
                })
        
        return tasks

    async def _create_financial_tasks(self, client: httpx.AsyncClient, symbols: List[str]) -> List:
        """Create financial intelligence tasks"""
        tasks = []
        
        # Alpha Vantage
        av_key = self.config.get('keys', {}).get('alpha_vantage')
        if av_key:
            # Company overview for each symbol
            for symbol in symbols[:3]:
                tasks.append({
                    'type': 'financial_intelligence',
                    'source': 'alpha_vantage',
                    'query': symbol,
                    'coro': financial_apis.fetch_alpha_vantage_company_overview(client, av_key, symbol)
                })
            
            # News for symbols
            if symbols:
                tasks.append({
                    'type': 'financial_intelligence',
                    'source': 'alpha_vantage_news',
                    'query': ','.join(symbols[:3]),
                    'coro': financial_apis.fetch_company_news_alpha_vantage(client, av_key, ','.join(symbols[:3]))
                })

        # Massive.com Market Data
        massive_key = self.config.get('keys', {}).get('massive')
        if massive_key and symbols:
            tasks.append({
                'type': 'financial_intelligence',
                'source': 'massive',
                'query': ','.join(symbols[:3]),
                'coro': financial_apis.fetch_massive_dividends(client, massive_key, symbols[:3])
            })

        # Finnhub
        finnhub_key = self.config.get('keys', {}).get('finnhub')
        if finnhub_key:
            for symbol in symbols[:2]:
                tasks.append({
                    'type': 'financial_intelligence',
                    'source': 'finnhub',
                    'query': symbol,
                    'coro': financial_apis.fetch_finnhub_news(client, finnhub_key, symbol)
                })

        # Quandl
        quandl_key = self.config.get('keys', {}).get('quandl')
        if quandl_key:
            for symbol in symbols[:1]:  # Limit Quandl calls
                tasks.append({
                    'type': 'financial_intelligence',
                    'source': 'quandl',
                    'query': f"WIKI/{symbol}",
                    'coro': financial_apis.fetch_quandl_data(client, quandl_key, f"WIKI/{symbol}")
                })
        
        return tasks

    async def _create_business_intelligence_tasks(self, client: httpx.AsyncClient, entities: List[str]) -> List:
        """Create business intelligence tasks"""
        tasks = []
        
        # Crunchbase
        crunchbase_key = self.config.get('keys', {}).get('crunchbase')
        if crunchbase_key:
            for entity in entities[:2]:
                tasks.append({
                    'type': 'business_intelligence',
                    'source': 'crunchbase',
                    'query': entity,
                    'coro': business_intelligence.fetch_crunchbase_organizations(client, crunchbase_key, entity)
                })

        # Clearbit
        clearbit_key = self.config.get('keys', {}).get('clearbit')
        if clearbit_key:
            for entity in entities[:2]:
                # Assume entity might be a domain
                domain = f"{entity.lower()}.com" if '.' not in entity else entity
                tasks.append({
                    'type': 'business_intelligence',
                    'source': 'clearbit',
                    'query': domain,
                    'coro': business_intelligence.fetch_clearbit_company(client, clearbit_key, domain)
                })

        # Apollo
        apollo_key = self.config.get('keys', {}).get('apollo')
        if apollo_key:
            for entity in entities[:1]:  # Limit Apollo calls
                domain = f"{entity.lower()}.com" if '.' not in entity else entity
                tasks.append({
                    'type': 'business_intelligence',
                    'source': 'apollo',
                    'query': domain,
                    'coro': business_intelligence.fetch_apollo_contacts(client, apollo_key, domain)
                })

        # BuiltWith
        builtwith_key = self.config.get('keys', {}).get('builtwith')
        if builtwith_key:
            for entity in entities[:2]:
                domain = f"{entity.lower()}.com" if '.' not in entity else entity
                tasks.append({
                    'type': 'business_intelligence',
                    'source': 'builtwith',
                    'query': domain,
                    'coro': business_intelligence.fetch_builtwith_domain(client, builtwith_key, domain)
                })

        return tasks

    async def _create_social_media_tasks(self, client: httpx.AsyncClient, search_terms: List[str]) -> List:
        """Create social media tasks"""
        tasks = []

        # Twitter/X
        twitter_key = self.config.get('keys', {}).get('twitter') or self.config.get('keys', {}).get('x')
        if twitter_key:
            for term in search_terms[:2]:
                tasks.append({
                    'type': 'social_media',
                    'source': 'twitter',
                    'query': term,
                    'coro': social_media.fetch_twitter_tweets(client, twitter_key, term)
                })

        # LinkedIn
        linkedin_key = self.config.get('keys', {}).get('linkedin')
        if linkedin_key:
            for term in search_terms[:1]:  # LinkedIn has strict rate limits
                tasks.append({
                    'type': 'social_media',
                    'source': 'linkedin',
                    'query': term,
                    'coro': social_media.search_linkedin_companies(client, linkedin_key, term)
                })

        return tasks

    async def _create_community_tasks(self, client: httpx.AsyncClient, search_terms: List[str]) -> List:
        """Create community intelligence tasks"""
        tasks = []

        # Reddit (scraping - no API key needed)
        for term in search_terms[:2]:
            for subreddit in ['technology', 'startups', 'entrepreneur', 'business']:
                tasks.append({
                    'type': 'community_intelligence',
                    'source': 'reddit',
                    'query': f"{subreddit}:{term}",
                    'coro': community_sources.scrape_reddit_posts(client, subreddit)
                })

        # Hacker News search
        for term in search_terms[:3]:
            tasks.append({
                'type': 'community_intelligence',
                'source': 'hackernews',
                'query': term,
                'coro': community_sources.scrape_hackernews_search(client, term)
            })

        # Product Hunt
        product_hunt_key = self.config.get('keys', {}).get('product_hunt')
        if product_hunt_key:
            tasks.append({
                'type': 'community_intelligence',
                'source': 'product_hunt',
                'query': 'latest',
                'coro': community_sources.fetch_product_hunt_posts(client, product_hunt_key)
            })

        # Indie Hackers (scraping)
        for term in search_terms[:1]:
            tasks.append({
                'type': 'community_intelligence',
                'source': 'indie_hackers',
                'query': term,
                'coro': community_sources.fetch_indie_hackers_posts(client, term)
            })

        return tasks

    async def _create_startup_tasks(self, client: httpx.AsyncClient, entities: List[str]) -> List:
        """Create startup intelligence tasks"""
        tasks = []

        # Custom startup tracker
        startup_tracker_key = self.config.get('keys', {}).get('startup_tracker')
        if startup_tracker_key:
            for entity in entities[:2]:
                tasks.append({
                    'type': 'startup_intelligence',
                    'source': 'startup_tracker',
                    'query': entity,
                    'coro': startup_tracker.fetch_startup_tracker_companies(client, startup_tracker_key, entity)
                })

        # BetaList (scraping)
        tasks.append({
            'type': 'startup_intelligence',
            'source': 'betalist',
            'query': 'latest',
            'coro': community_sources.fetch_betalist_startups(client)
        })

        # TechCrunch RSS
        for entity in entities[:1]:
            tasks.append({
                'type': 'startup_intelligence',
                'source': 'techcrunch',
                'query': entity,
                'coro': startup_tracker.fetch_techcrunch_startups(client, 'startups')
            })

        return tasks

    async def _create_security_tasks(self, client: httpx.AsyncClient, search_terms: List[str], entities: List[str]) -> List:
        """Create security intelligence tasks"""
        tasks = []

        # Shodan security intelligence
        shodan_key = self.config.get('keys', {}).get('shodan')
        if shodan_key:
            # Search for technologies/services mentioned in query
            for term in search_terms[:2]:
                # Look for exposed services related to the search terms
                shodan_query = f"product:{term}"
                tasks.append({
                    'type': 'security_intelligence',
                    'source': 'shodan',
                    'query': shodan_query,
                    'coro': shodan.search_shodan(client, shodan_key, shodan_query, limit=10)
                })

            # Search for company entities in Shodan
            for entity in entities[:2]:
                # Look for infrastructure owned by the entity
                shodan_query = f"org:\"{entity}\""
                tasks.append({
                    'type': 'security_intelligence',
                    'source': 'shodan_org',
                    'query': shodan_query,
                    'coro': shodan.search_shodan(client, shodan_key, shodan_query, limit=5)
                })

        return tasks

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