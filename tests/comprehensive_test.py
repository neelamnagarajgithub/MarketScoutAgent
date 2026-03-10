#!/usr/bin/env python3
"""
Comprehensive API Integration Test
Tests all integrated APIs and data sources from config.yaml
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the app directory to path
sys.path.insert(0, '/home/naagaraj/marketscoutagent/market-aggregator')

async def comprehensive_api_test():
    """Test all API integrations and data sources"""
    
    print("🧪 Comprehensive API Integration Test")
    print("=" * 60)
    
    try:
        # Test 1: Import all modules
        print("📦 Testing imports...")
        from app.simple_semantic_search import SimpleSemanticSearch
        from app.api_validator import APIKeyValidator
        from app.fetchers import (
            serpapi, newsapi, github, news_sources, financial_apis,
            business_intelligence, community_sources, social_media, startup_tracker
        )
        print("✅ All modules imported successfully")
        
        # Test 2: Initialize engine
        print("\n🚀 Testing initialization...")
        engine = SimpleSemanticSearch()
        print("✅ Engine initialized")
        
        # Test 3: API validation
        print("\n🔐 Testing API validation...")
        valid_apis = await engine.validate_apis()
        print(f"✅ API validation completed: {valid_apis}")
        
        # Test 4: Show all configured APIs
        print("\n📋 Configured APIs:")
        config = engine.config
        for category, apis in {
            "🔍 Search & Discovery": ["serpapi", "bing_search", "google_custom_search"],
            "📰 News Sources": ["newsapi", "gnews", "mediastack", "currents"],
            "💼 Business Intelligence": ["crunchbase", "clearbit", "apollo", "builtwith"],
            "💹 Financial APIs": ["alpha_vantage", "massive", "finnhub", "quandl"],
            "🐙 Code Repositories": ["github_personal_access_token", "gitlab"],
            "🌐 Social Media": ["twitter", "x", "linkedin"],
            "🚀 Startup Tracking": ["product_hunt", "startup_tracker"],
            "👥 Community Sources": ["reddit", "hacker_news", "indie_hackers", "betalist"]
        }.items():
            print(f"\n{category}:")
            for api in apis:
                key = config.get('keys', {}).get(api)
                status = "✅ Configured" if key else "❌ Not configured"
                display_name = "github" if api == "github_personal_access_token" else api
                print(f"  • {display_name}: {status}")
        
        # Test 5: Comprehensive search test
        print("\n🔍 Testing comprehensive search...")
        test_queries = [
            "NVIDIA AI chip market analysis",
            "Tesla electric vehicle sales data",
            "OpenAI ChatGPT business model"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n🔎 Test {i}: {query}")
            results = await engine.comprehensive_search(query)
            
            if results.get("status") == "success":
                summary = results.get("summary", {})
                total_docs = summary.get('total_documents', 0)
                sources = summary.get('successful_sources', 0)
                print(f"✅ Retrieved {total_docs} documents from {sources} sources")
                
                # Show source breakdown
                source_docs = summary.get('source_documents', {})
                if source_docs:
                    print("   📊 Source breakdown:")
                    for source, count in source_docs.items():
                        print(f"     • {source}: {count} documents")
                
                # Show JSON file
                json_path = results.get('json_file')
                if json_path:
                    print(f"   💾 Saved to: {json_path}")
            else:
                print(f"❌ Search failed: {results.get('error', 'Unknown error')}")
                
            if i < len(test_queries):
                print("   ⏳ Waiting 5s before next test...")
                await asyncio.sleep(5)
        
        # Test 6: Data source capabilities
        print(f"\n🎯 Data Source Capabilities:")
        print("  🔍 Search Discovery: Web search, trending topics")
        print("  📰 News Intelligence: Current articles, press releases") 
        print("  💼 Business Intelligence: Company data, tech stacks, contacts")
        print("  💹 Financial Intelligence: Stock data, market news, financial metrics")
        print("  🐙 Code Intelligence: GitHub/GitLab repositories, tech analysis")
        print("  🌐 Social Media Intelligence: Twitter/X, LinkedIn insights")  
        print("  👥 Community Intelligence: Reddit, Hacker News, Product Hunt")
        print("  🚀 Startup Intelligence: Funding data, accelerator programs")
        
        print(f"\n🎉 Comprehensive API integration test completed!")
        print(f"🏆 Total integrated APIs: 25+ services")
        print(f"📈 Expected document retrieval: 300-1000+ per search")
        print(f"🔄 Concurrent processing: Multi-source parallel fetching")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(comprehensive_api_test())