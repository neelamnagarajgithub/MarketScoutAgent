#!/usr/bin/env python3
"""
Simplified Semantic Search System for Market Intelligence
No external vector DB dependencies - uses local similarity search
"""

import asyncio
import json
import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np
from sentence_transformers import SentenceTransformer
import httpx
import yaml
from dataclasses import dataclass

# Local imports
from app.fetchers import (
    serpapi, newsapi, github, npm_pypi, rss,
    news_sources, search_apis, business_intelligence,
    community_sources, financial_apis
)
from app.normalizer import normalize_item
from app.db import Database

# Import query optimizer
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from query_optimizer import QueryOptimizer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class QueryPlan:
    """Query execution plan"""
    query_type: str
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
        
        # In-memory document store for semantic search
        self.document_embeddings = []
        self.documents = []

    async def plan_query(self, user_query: str) -> QueryPlan:
        """Create a simple query plan with enhanced optimization"""
        query_lower = user_query.lower()
        
        # Determine query type
        if any(word in query_lower for word in ["company", "startup", "business", "organization"]):
            query_type = "company_analysis"
        elif any(word in query_lower for word in ["product", "launch", "release", "tool", "app"]):
            query_type = "product_research"
        elif any(word in query_lower for word in ["market", "trend", "industry", "sector"]):
            query_type = "market_trend" 
        elif any(word in query_lower for word in ["competitor", "competition", "vs", "compare"]):
            query_type = "competitor_analysis"
        elif any(word in query_lower for word in ["funding", "investment", "round", "series"]):
            query_type = "funding_intelligence"
        elif any(word in query_lower for word in ["news", "update", "announcement"]):
            query_type = "news_monitoring"
        else:
            query_type = "general_intelligence"
        
        # Extract entities (simple keyword extraction)
        entities = []
        keywords = user_query.split()
        
        # Use query optimizer for enhanced search terms and financial symbols
        optimized_search_terms = self.query_optimizer.optimize_search_terms(user_query)
        optimized_financial_symbols = self.query_optimizer.enhance_financial_symbols(user_query)
        
        # Select data sources based on query type
        if query_type == "company_analysis":
            sources = ["search_discovery", "news_intelligence", "financial_intelligence", "github_intelligence"]
        elif query_type == "product_research":
            sources = ["search_discovery", "tech_intelligence", "github_intelligence", "community_intelligence"]
        elif query_type == "market_trend":
            sources = ["search_discovery", "news_intelligence", "community_intelligence", "rss_intelligence"]
        elif query_type == "funding_intelligence":
            sources = ["search_discovery", "news_intelligence", "financial_intelligence"]
        else:
            sources = ["search_discovery", "news_intelligence"]
        
        return QueryPlan(
            query_type=query_type,
            entities=entities,
            keywords=keywords[:10],  # Limit keywords
            sources=sources,
            search_terms=optimized_search_terms,  # Use optimized terms
            financial_symbols=optimized_financial_symbols  # Use optimized symbols
        )

    async def execute_search_discovery(self, search_terms: List[str]) -> Dict[str, Any]:
        """Execute search across multiple search APIs with result filtering"""
        results = {}
        
        async with httpx.AsyncClient(timeout=30) as client:
            # SerpAPI
            serp_key = self.config.get('keys', {}).get('serpapi')
            if serp_key:
                serp_results = {}
                for term in search_terms[:3]:  # Limit API calls
                    try:
                        data = await serpapi.serp_search(client, serp_key, term)
                        # Apply result filtering for relevance
                        if isinstance(data, list):
                            filtered_data = self.query_optimizer.filter_search_results(data)
                            serp_results[term] = filtered_data
                        else:
                            serp_results[term] = data
                    except Exception as e:
                        serp_results[term] = {"error": str(e)}
                results["serpapi"] = serp_results
            
            # Bing Search  
            bing_key = self.config.get('keys', {}).get('bing_search')
            if bing_key:
                bing_results = {}
                for term in search_terms[:2]:
                    try:
                        data = await search_apis.fetch_bing_search(client, bing_key, term)
                        # Apply result filtering for relevance
                        if isinstance(data, list):
                            filtered_data = self.query_optimizer.filter_search_results(data)
                            bing_results[term] = filtered_data
                        else:
                            bing_results[term] = data
                    except Exception as e:
                        bing_results[term] = {"error": str(e)}
                results["bing"] = bing_results
        
        return results

    async def execute_news_intelligence(self, search_terms: List[str]) -> Dict[str, Any]:
        """Execute news gathering from multiple sources with relevance filtering"""
        results = {}
        
        async with httpx.AsyncClient(timeout=30) as client:
            # NewsAPI
            news_key = self.config.get('keys', {}).get('newsapi')
            if news_key:
                news_results = {}
                for term in search_terms[:3]:
                    try:
                        data = await newsapi.search_newsapi(client, news_key, term)
                        # Apply result filtering for relevance
                        if isinstance(data, list):
                            filtered_data = self.query_optimizer.filter_search_results(data)
                            news_results[term] = filtered_data
                        else:
                            news_results[term] = data
                    except Exception as e:
                        news_results[term] = {"error": str(e)}
                results["newsapi"] = news_results
            
            # GNews
            gnews_key = self.config.get('keys', {}).get('gnews')
            if gnews_key:
                gnews_results = {}
                for term in search_terms[:2]:
                    try:
                        data = await news_sources.fetch_gnews(client, gnews_key, term)
                        # Apply result filtering for relevance
                        if isinstance(data, list):
                            filtered_data = self.query_optimizer.filter_search_results(data)
                            gnews_results[term] = filtered_data
                        else:
                            gnews_results[term] = data
                    except Exception as e:
                        gnews_results[term] = {"error": str(e)}
                results["gnews"] = gnews_results
        
        return results

    async def execute_github_intelligence(self, search_terms: List[str]) -> Dict[str, Any]:
        """Execute GitHub organization and repository analysis"""
        results = {}
        
        async with httpx.AsyncClient(timeout=30) as client:
            gh_key = self.config.get('keys', {}).get('github')
            if not gh_key:
                return {"error": "GitHub API key not configured"}
            
            # Get popular organizations
            orgs = self.config.get('sources', {}).get('github_orgs', ['openai', 'vercel', 'microsoft', 'google'])
            
            org_results = {}
            for org in orgs[:4]:  # Limit to avoid rate limits
                try:
                    repos = await github.fetch_org_repos(client, gh_key, org)
                    # Sort by updated_at and take most recent
                    if isinstance(repos, list):
                        sorted_repos = sorted(repos, key=lambda x: x.get('updated_at', ''), reverse=True)
                        org_results[org] = sorted_repos[:5]
                    else:
                        org_results[org] = repos
                except Exception as e:
                    org_results[org] = {"error": str(e)}
            
            results["github_orgs"] = org_results
        
        return results

    async def execute_financial_intelligence(self, symbols: List[str], search_terms: List[str]) -> Dict[str, Any]:
        """Execute financial data gathering"""
        results = {}
        
        async with httpx.AsyncClient(timeout=30) as client:
            # Alpha Vantage
            av_key = self.config.get('keys', {}).get('alpha_vantage')
            if av_key:
                # Default symbols if none provided
                if not symbols:
                    symbols = ['MSFT', 'GOOGL', 'AAPL', 'NVDA']  # Default tech stocks
                
                av_results = {}
                for symbol in symbols[:3]:  # Limit API calls
                    try:
                        data = await financial_apis.fetch_alpha_vantage_company_overview(client, av_key, symbol)
                        av_results[symbol] = data
                    except Exception as e:
                        av_results[symbol] = {"error": str(e)}
                
                # Get financial news
                try:
                    news_data = await financial_apis.fetch_company_news_alpha_vantage(client, av_key, ",".join(symbols[:3]))
                    av_results["news"] = news_data[:5] if isinstance(news_data, list) else news_data
                except Exception as e:
                    av_results["news"] = {"error": str(e)}
                
                results["alpha_vantage"] = av_results
        
        return results

    async def execute_community_intelligence(self, search_terms: List[str]) -> Dict[str, Any]:
        """Execute community platform data gathering"""
        results = {}
        
        async with httpx.AsyncClient(timeout=30) as client:
            # Hacker News
            try:
                # Get top stories and new stories
                top_stories = await community_sources.fetch_hackernews_stories(client, "topstories", 20)
                new_stories = await community_sources.fetch_hackernews_stories(client, "newstories", 20)
                
                # Filter by relevance to search terms
                relevant_top = []
                relevant_new = []
                
                for story in top_stories if isinstance(top_stories, list) else []:
                    title = story.get('title', '').lower()
                    if any(term.lower() in title for term in search_terms):
                        relevant_top.append(story)
                
                for story in new_stories if isinstance(new_stories, list) else []:
                    title = story.get('title', '').lower()
                    if any(term.lower() in title for term in search_terms):
                        relevant_new.append(story)
                
                results["hackernews"] = {
                    "relevant_top": relevant_top[:10],
                    "relevant_new": relevant_new[:10],
                    "all_top": top_stories[:5] if isinstance(top_stories, list) else top_stories,
                    "all_new": new_stories[:5] if isinstance(new_stories, list) else new_stories
                }
                
            except Exception as e:
                results["hackernews"] = {"error": str(e)}
        
        return results

    async def execute_rss_intelligence(self, search_terms: List[str]) -> Dict[str, Any]:
        """Execute RSS feed monitoring"""
        results = {}
        
        # Get RSS feeds from config
        rss_feeds = self.config.get('sources', {}).get('rss_feeds', [])
        
        for feed_url in rss_feeds[:4]:  # Limit feeds
            try:
                feed_data = await asyncio.to_thread(rss.fetch_rss_feed, feed_url, 10)
                feed_name = feed_url.split('//')[1].split('/')[0] if '//' in feed_url else feed_url
                results[feed_name] = feed_data
            except Exception as e:
                feed_name = feed_url.split('//')[1].split('/')[0] if '//' in feed_url else "unknown_feed"
                results[feed_name] = {"error": str(e)}
        
        return results

    async def execute_tech_intelligence(self, search_terms: List[str]) -> Dict[str, Any]:
        """Execute technology and package analysis"""
        results = {}
        
        async with httpx.AsyncClient(timeout=30) as client:
            # NPM packages
            npm_results = {}
            # Simple heuristics for relevant packages
            if any(term in ' '.join(search_terms).lower() for term in ['react', 'javascript', 'frontend']):
                packages = ['react', 'vue', 'next', '@angular/core']
            elif any(term in ' '.join(search_terms).lower() for term in ['ai', 'ml', 'python']):
                packages = ['transformers', 'langchain', 'torch', 'tensorflow']
            else:
                packages = ['express', 'fastapi', 'django', 'flask']
            
            for package in packages[:4]:
                try:
                    data = await npm_pypi.fetch_npm_package(client, package)
                    npm_results[package] = {
                        "name": data.get("name"),
                        "description": (data.get("description", "") or "")[:200],
                        "version": data.get("dist-tags", {}).get("latest"),
                        "homepage": data.get("homepage"),
                        "weekly_downloads": data.get("downloads")
                    }
                except Exception as e:
                    npm_results[package] = {"error": str(e)}
            
            results["npm_packages"] = npm_results
        
        return results

    async def comprehensive_search(self, user_query: str, save_json: bool = True) -> Dict[str, Any]:
        """Execute comprehensive semantic search"""
        logger.info(f"Starting comprehensive search for: {user_query}")
        
        try:
            # Step 1: Plan the query
            plan = await self.plan_query(user_query)
            logger.info(f"Query plan: {plan.query_type}, Sources: {plan.sources}")
            
            # Step 2: Execute searches based on plan
            search_results = {}
            
            if "search_discovery" in plan.sources:
                search_results["search_discovery"] = await self.execute_search_discovery(plan.search_terms)
            
            if "news_intelligence" in plan.sources:
                search_results["news_intelligence"] = await self.execute_news_intelligence(plan.search_terms)
            
            if "github_intelligence" in plan.sources:
                search_results["github_intelligence"] = await self.execute_github_intelligence(plan.search_terms)
            
            if "financial_intelligence" in plan.sources:
                search_results["financial_intelligence"] = await self.execute_financial_intelligence(
                    plan.financial_symbols, plan.search_terms
                )
            
            if "community_intelligence" in plan.sources:
                search_results["community_intelligence"] = await self.execute_community_intelligence(plan.search_terms)
            
            if "rss_intelligence" in plan.sources:
                search_results["rss_intelligence"] = await self.execute_rss_intelligence(plan.search_terms)
            
            if "tech_intelligence" in plan.sources:
                search_results["tech_intelligence"] = await self.execute_tech_intelligence(plan.search_terms)
            
            # Step 3: Generate insights and structure results
            final_result = await self.generate_insights(user_query, plan, search_results)
            
            # Step 4: Save JSON to local file if requested
            if save_json:
                json_filename = await self.save_json_result(final_result)
                final_result["json_file_saved"] = json_filename
            
            # Step 5: Save to database (optional)
            await self.save_search_session(final_result)
            
            return final_result
            
        except Exception as e:
            logger.error(f"Comprehensive search failed: {e}")
            return {
                "query": user_query,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def generate_insights(self, query: str, plan: QueryPlan, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights from search results"""
        
        # Count total documents and successful sources
        total_docs = 0
        successful_sources = 0
        
        for source, data in results.items():
            if isinstance(data, dict) and "error" not in data:
                successful_sources += 1
                # Estimate document count
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, list):
                            total_docs += len(value)
                        elif isinstance(value, dict) and "error" not in value:
                            total_docs += 1
        
        # Extract key entities and topics (simple keyword analysis)
        all_text = []
        for source_data in results.values():
            if isinstance(source_data, dict):
                all_text.append(json.dumps(source_data)[:1000])
        
        # Simple keyword extraction
        combined_text = ' '.join(all_text).lower()
        keywords = plan.keywords + plan.entities
        
        # Generate insights
        insights = []
        if successful_sources > 2:
            insights.append(f"Successfully gathered data from {successful_sources} different sources")
        if total_docs > 10:
            insights.append(f"Retrieved {total_docs} documents for analysis")
        if plan.financial_symbols:
            insights.append(f"Financial analysis included symbols: {', '.join(plan.financial_symbols)}")
        
        # Generate recommendations based on query type
        recommendations = []
        if plan.query_type == "company_analysis":
            recommendations.append("Review financial metrics and recent news for comprehensive analysis")
            recommendations.append("Check competitor activity and market positioning")
        elif plan.query_type == "market_trend":
            recommendations.append("Monitor community discussions for emerging trends")   
            recommendations.append("Track RSS feeds for industry updates")
        elif plan.query_type == "product_research":
            recommendations.append("Analyze GitHub activity for technical developments")
            recommendations.append("Review package ecosystems for related tools")
        else:
            recommendations.append("Continue monitoring multiple data sources for updates")
            recommendations.append("Set up alerts for key entities and topics")
        
        return {
            "query": query,
            "query_type": plan.query_type,
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "plan": {
                "entities": plan.entities,
                "keywords": plan.keywords,
                "sources": plan.sources,
                "search_terms": plan.search_terms,
                "financial_symbols": plan.financial_symbols
            },
            "summary": {
                "total_sources_queried": len(plan.sources),
                "successful_sources": successful_sources,
                "total_documents": total_docs,
                "search_terms_used": len(plan.search_terms)
            },
            "insights": insights,
            "recommendations": recommendations,
            "raw_data": results,
            "confidence_score": min(0.9, 0.3 + (successful_sources * 0.15) + (total_docs * 0.01))
        }

    async def save_json_result(self, result: Dict[str, Any]) -> str:
        """Save search result as JSON file with intelligent naming"""
        try:
            import os
            import re
            
            # Create results directory if it doesn't exist
            results_dir = "search_results"
            os.makedirs(results_dir, exist_ok=True)
            
            # Generate intelligent filename
            query = result.get("query", "unknown_query")
            query_type = result.get("query_type", "general")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Clean query for filename (remove special chars, limit length)
            clean_query = re.sub(r'[^\w\s-]', '', query).strip()
            clean_query = re.sub(r'[-\s]+', '_', clean_query)
            clean_query = clean_query[:50]  # Limit length
            
            filename = f"{results_dir}/{timestamp}_{query_type}_{clean_query}.json"
            
            # Save the JSON file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, default=str, ensure_ascii=False)
            
            logger.info(f"JSON result saved to: {filename}")
            print(f"💾 JSON saved: {filename}")
            
            return filename
            
        except Exception as e:
            logger.error(f"Failed to save JSON result: {e}")
            return f"Error saving: {str(e)}"

    async def save_search_session(self, result: Dict[str, Any]):
        """Save search session to database"""
        try:
            await self.db.init_models()
            
            doc = {
                "source": "simple_semantic_search",
                "title": f"Market Search: {result.get('query', 'Unknown Query')}",
                "url": f"internal://search/{int(datetime.now().timestamp())}",
                "content": json.dumps(result, indent=2),
                "published_at": datetime.now(),
                "doc_metadata": {
                    "provider": "simple_semantic_search",
                    "query_type": result.get("query_type"),
                    "confidence_score": result.get("confidence_score", 0.0),
                    "sources_count": result.get("summary", {}).get("successful_sources", 0)
                },
                "content_hash": str(hash(json.dumps(result, sort_keys=True)))[:64]
            }
            
            await self.db.save_document(doc)
            logger.info("Search session saved to database")
            
        except Exception as e:
            logger.error(f"Failed to save search session: {e}")

# Convenience functions
async def search(query: str, config_path: str = "config.yaml", save_json: bool = True) -> Dict[str, Any]:
    """Simple interface for semantic search with automatic JSON saving"""
    engine = SimpleSemanticSearch(config_path)
    return await engine.comprehensive_search(query, save_json=save_json)

# CLI interface
async def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m app.simple_semantic_search 'your search query'")
        print("\nExample queries:")
        print("  python -m app.simple_semantic_search 'AI startups funding'")
        print("  python -m app.simple_semantic_search 'OpenAI competitors'")
        print("  python -m app.simple_semantic_search 'SaaS market trends'")
        return
    
    query = " ".join(sys.argv[1:])
    print(f"🔍 Semantic Market Search: {query}")
    print("=" * 60)
    
    results = await search(query)
    
    # Print summary
    print(f"\n📊 Search Results Summary")
    print(f"Query Type: {results.get('query_type')}")
    print(f"Status: {results.get('status')}")
    print(f"Sources: {results.get('summary', {}).get('successful_sources', 0)}")
    print(f"Documents: {results.get('summary', {}).get('total_documents', 0)}")
    print(f"Confidence: {results.get('confidence_score', 0):.2f}")
    
    # Print insights
    insights = results.get('insights', [])
    if insights:
        print(f"\n💡 Key Insights:")
        for i, insight in enumerate(insights[:5], 1):
            print(f"  {i}. {insight}")
    
    # Print recommendations  
    recommendations = results.get('recommendations', [])
    if recommendations:
        print(f"\n🎯 Recommendations:")
        for i, rec in enumerate(recommendations[:3], 1):
            print(f"  {i}. {rec}")
    
    # Print data sources with results
    raw_data = results.get('raw_data', {})
    if raw_data:
        print(f"\n📈 Data Sources:")
        for source, data in raw_data.items():
            if isinstance(data, dict) and "error" not in data:
                count = sum(len(v) if isinstance(v, list) else 1 for v in data.values() if not isinstance(v, dict) or "error" not in v)
                print(f"  ✅ {source}: {count} items")
            else:
                print(f"  ❌ {source}: error")
    
    print("\n" + "=" * 60)
    
    # Optionally save full results
    if "--save" in sys.argv:
        filename = f"search_results_{int(datetime.now().timestamp())}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"💾 Full results saved to: {filename}")

if __name__ == "__main__":
    asyncio.run(main())