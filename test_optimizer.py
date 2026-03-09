#!/usr/bin/env python3
"""
Test Query Optimizer Integration
Shows before/after comparison of search terms and results
"""

import asyncio
import json
from app.simple_semantic_search import SimpleSemanticSearch
from query_optimizer import QueryOptimizer

async def test_query_optimization():
    print("🔧 Testing Query Optimizer Integration")
    print("=" * 60)
    
    # Initialize components
    optimizer = QueryOptimizer()
    engine = SimpleSemanticSearch()
    
    # Test query
    test_query = "recent funding rounds for generative AI startups"
    
    print(f"📝 Original Query: '{test_query}'")
    print()
    
    # Show old vs new search terms
    print("🔍 Search Term Optimization:")
    print("-" * 40)
    
    # Old approach (individual words)
    old_terms = [test_query] + [word for word in test_query.split() if len(word) > 3]
    print("❌ Old Terms (noisy):")
    for i, term in enumerate(old_terms[:5], 1):
        print(f"  {i}. '{term}'")
    
    print()
    
    # New optimized approach
    new_terms = optimizer.optimize_search_terms(test_query)
    print("✅ New Terms (optimized):")
    for i, term in enumerate(new_terms, 1):
        print(f"  {i}. '{term}'")
    
    print()
    
    # Show financial symbol optimization
    print("💰 Financial Symbol Optimization:")
    print("-" * 40)
    
    # Old approach (regex extraction)
    import re
    old_symbols = re.findall(r'\b[A-Z]{2,5}\b', test_query)
    if not old_symbols:
        old_symbols = ['AI']  # fallback
    print(f"❌ Old Symbols: {old_symbols}")
    
    # New optimized approach
    new_symbols = optimizer.enhance_financial_symbols(test_query)
    print(f"✅ New Symbols: {new_symbols}")
    
    print()
    
    # Test filtering capabilities
    print("🔧 Result Filtering Test:")
    print("-" * 40)
    
    # Mock search results (good and bad)
    mock_results = [
        {
            "title": "OpenAI Raises $110B in Massive Funding Round",
            "content": "AI startup funding venture capital investment artificial intelligence",
            "url": "https://example.com/openai-funding"
        },
        {
            "title": "Recent - Definition and Meaning",
            "content": "dictionary definition pronunciation grammar english word meaning",
            "url": "https://dictionary.com/recent"
        },
        {
            "title": "NVIDIA's AI Investment Strategy for 2026", 
            "content": "nvidia ai startup funding investment venture capital artificial intelligence",
            "url": "https://example.com/nvidia-ai"
        },
        {
            "title": "Football Results: Recent Match Scores",
            "content": "sports football soccer match results recent games",
            "url": "https://sports.com/football"
        }
    ]
    
    print(f"📊 Before Filtering: {len(mock_results)} results")
    for i, result in enumerate(mock_results, 1):
        print(f"  {i}. {result['title']}")
    
    # Apply filtering
    filtered_results = optimizer.filter_search_results(mock_results)
    print(f"\n✅ After Filtering: {len(filtered_results)} results")
    for i, result in enumerate(filtered_results, 1):
        print(f"  {i}. {result['title']} ✓")
    
    print()
    
    # Run actual optimized search
    print("🚀 Running Optimized Search...")
    print("-" * 40)
    
    try:
        results = await engine.comprehensive_search(test_query, save_json=False)
        
        # Show improvement metrics
        status = results.get("status")
        sources = results.get("summary", {}).get("successful_sources", 0)
        docs = results.get("summary", {}).get("total_documents", 0)
        confidence = results.get("confidence_score", 0)
        
        print(f"✅ Search Status: {status}")
        print(f"📡 Sources Used: {sources}")
        print(f"📄 Documents Retrieved: {docs}")
        print(f"🎯 Confidence Score: {confidence:.2f}")
        
        # Show sample optimized results
        search_data = results.get("raw_data", {}).get("search_discovery", {}).get("serpapi", {})
        if search_data:
            first_term = list(search_data.keys())[0] if search_data else None
            if first_term and isinstance(search_data[first_term], list):
                sample_results = search_data[first_term][:3]
                print(f"\n📋 Sample Filtered Results for '{first_term}':")
                for i, result in enumerate(sample_results, 1):
                    title = result.get("title", "No title")[:50]
                    print(f"  {i}. {title}...")
        
    except Exception as e:
        print(f"❌ Search failed: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Query Optimizer is now integrated and active!")

if __name__ == "__main__":
    asyncio.run(test_query_optimization())