#!/usr/bin/env python3
"""
Simple Test Script for Market Intelligence Agent
Tests individual data fetchers before running the full agent
"""

import asyncio
import httpx
import yaml
import os
import sys
import json
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, '/home/naagaraj/marketscoutagent/market-aggregator')

from app.fetchers import serpapi, newsapi, github, npm_pypi, rss
from app.fetchers import news_sources, community_sources, financial_apis

async def test_data_sources():
    """Test each data source individually"""
    print("🧪 Testing Market Intelligence Data Sources")
    print("=" * 60)
    
    # Load configuration
    with open("config.yaml", "r") as fh:
        config = yaml.safe_load(fh)
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        results = {}
        
        # Test SerpAPI
        print("🔍 Testing SerpAPI...")
        serp_key = config['keys'].get('serpapi')
        if serp_key:
            try:
                serp_data = await serpapi.serp_search(client, serp_key, "AI startup launch", engine="google")
                results['serpapi'] = {"status": "success", "count": len(serp_data) if isinstance(serp_data, list) else 0}
                print(f"   ✅ SerpAPI: {len(serp_data) if isinstance(serp_data, list) else 0} results")
            except Exception as e:
                results['serpapi'] = {"status": "error", "message": str(e)}
                print(f"   ❌ SerpAPI: {e}")
        else:
            results['serpapi'] = {"status": "skip", "message": "No API key"}
            print("   ⚠️  SerpAPI: No API key configured")
        
        # Test NewsAPI
        print("📰 Testing NewsAPI...")
        news_key = config['keys'].get('newsapi')
        if news_key:
            try:
                news_data = await newsapi.search_newsapi(client, news_key, "startup funding")
                results['newsapi'] = {"status": "success", "count": len(news_data)}
                print(f"   ✅ NewsAPI: {len(news_data)} results")
            except Exception as e:
                results['newsapi'] = {"status": "error", "message": str(e)}
                print(f"   ❌ NewsAPI: {e}")
        else:
            results['newsapi'] = {"status": "skip", "message": "No API key"}
            print("   ⚠️  NewsAPI: No API key configured")
        
        # Test GNews
        print("📢 Testing GNews...")
        gnews_key = config['keys'].get('gnews')
        if gnews_key:
            try:
                gnews_data = await news_sources.fetch_gnews(client, gnews_key, "product launch")
                results['gnews'] = {"status": "success", "count": len(gnews_data)}
                print(f"   ✅ GNews: {len(gnews_data)} results")
            except Exception as e:
                results['gnews'] = {"status": "error", "message": str(e)}
                print(f"   ❌ GNews: {e}")
        else:
            results['gnews'] = {"status": "skip", "message": "No API key"}
            print("   ⚠️  GNews: No API key configured")
        
        # Test GitHub
        print("💻 Testing GitHub API...")
        gh_key = config['keys'].get('github')
        if gh_key:
            try:
                gh_data = await github.fetch_org_repos(client, gh_key, "openai")
                results['github'] = {"status": "success", "count": len(gh_data) if isinstance(gh_data, list) else 0}
                print(f"   ✅ GitHub: {len(gh_data) if isinstance(gh_data, list) else 0} results")
            except Exception as e:
                results['github'] = {"status": "error", "message": str(e)}
                print(f"   ❌ GitHub: {e}")
        else:
            results['github'] = {"status": "skip", "message": "No API key"}
            print("   ⚠️  GitHub: No API key configured")
        
        # Test Alpha Vantage
        print("💰 Testing Alpha Vantage...")
        av_key = config['keys'].get('alpha_vantage')
        if av_key:
            try:
                av_data = await financial_apis.fetch_alpha_vantage_company_overview(client, av_key, "MSFT")
                results['alpha_vantage'] = {"status": "success", "has_data": bool(av_data)}
                print(f"   ✅ Alpha Vantage: {'Data received' if av_data else 'No data'}")
            except Exception as e:
                results['alpha_vantage'] = {"status": "error", "message": str(e)}
                print(f"   ❌ Alpha Vantage: {e}")
        else:
            results['alpha_vantage'] = {"status": "skip", "message": "No API key"}
            print("   ⚠️  Alpha Vantage: No API key configured")
        
        # Test Hacker News (no API key needed)
        print("🗞️  Testing Hacker News...")
        try:
            hn_data = await community_sources.fetch_hackernews_stories(client, "topstories", 5)
            results['hackernews'] = {"status": "success", "count": len(hn_data)}
            print(f"   ✅ Hacker News: {len(hn_data)} results")
        except Exception as e:
            results['hackernews'] = {"status": "error", "message": str(e)}
            print(f"   ❌ Hacker News: {e}")
        
        # Test RSS Feeds
        print("📡 Testing RSS Feeds...")
        try:
            rss_feeds = config.get('sources', {}).get('rss_feeds', [])[:1]  # Test just one
            if rss_feeds:
                rss_data = await asyncio.to_thread(rss.fetch_rss_feed, rss_feeds[0], 3)
                results['rss'] = {"status": "success", "count": len(rss_data)}
                print(f"   ✅ RSS: {len(rss_data)} results from {rss_feeds[0]}")
            else:
                results['rss'] = {"status": "skip", "message": "No RSS feeds configured"}
                print("   ⚠️  RSS: No feeds configured")
        except Exception as e:
            results['rss'] = {"status": "error", "message": str(e)}
            print(f"   ❌ RSS: {e}")
    
    print("\\n" + "=" * 60)
    print("📊 Test Results Summary:")
    
    successful = sum(1 for r in results.values() if r["status"] == "success")
    failed = sum(1 for r in results.values() if r["status"] == "error")
    skipped = sum(1 for r in results.values() if r["status"] == "skip")
    
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   ⚠️  Skipped: {skipped}")
    
    # Save detailed results
    test_file = f"data_source_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(test_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\\n📝 Detailed results saved to: {test_file}")
    
    return results

async def test_agent():
    """Test the full LangChain agent"""
    print("\\n🤖 Testing LangChain Market Intelligence Agent")
    print("=" * 60)
    
    # Check for Google API key
    google_key = os.getenv("GOOGLE_API_KEY")
    if not google_key:
        print("❌ GOOGLE_API_KEY not set in environment")
        print("Please set your Gemini API key:")
        print("export GOOGLE_API_KEY='your_api_key_here'")
        return False
    
    try:
        from app.agent import MarketIntelligenceAgent
        
        # Initialize agent
        print("🔧 Initializing agent...")
        agent = MarketIntelligenceAgent()
        print("   ✅ Agent initialized successfully")
        
        # Test simple query
        print("🧠 Running intelligence gathering...")
        result = await agent.comprehensive_intelligence_gathering("AI startup news")
        
        if result and not result.get("error"):
            print("   ✅ Agent executed successfully")
            print(f"   📊 Query: {result.get('query', 'Unknown')}")
            print(f"   📈 Status: {result.get('status', 'Unknown')}")
            print(f"   🏷️  Sources: {len(result.get('sources', {}))}")
            return True
        else:
            print(f"   ❌ Agent failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🚀 Market Intelligence Agent Test Suite")
    print("=" * 80)
    
    # Run data source tests
    asyncio.run(test_data_sources())
    
    # Run agent test if requested
    if len(sys.argv) > 1 and sys.argv[1].lower() == "agent":
        agent_success = asyncio.run(test_agent())
        if agent_success:
            print("\\n🎉 All tests passed! Agent is ready for use.")
        else:
            print("\\n⚠️  Agent test failed. Check configuration and API keys.")

if __name__ == "__main__":
    main()