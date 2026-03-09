#!/usr/bin/env python3
"""
Simple Semantic Search Runner
Usage: python simple_search.py "your search query here"
"""

import sys
import asyncio
import json
from app.simple_semantic_search import SimpleSemanticSearch

async def main():
    if len(sys.argv) < 2:
        print("Usage: python simple_search.py 'your search query'")
        print("Example: python simple_search.py 'NVIDIA AI strategy'")
        sys.exit(1)
    
    query = sys.argv[1]
    
    print(f"🔍 Searching: {query}")
    print("=" * 50)
    
    # Initialize search engine
    engine = SimpleSemanticSearch()
    
    # Run search
    results = await engine.comprehensive_search(query)
    
    # Display results
    if results.get("status") == "success":
        print("✅ Search completed successfully!")
        summary = results.get("summary", {})
        print(f"📊 Retrieved {summary.get('total_documents', 0)} documents from {summary.get('successful_sources', 0)} sources")
        
        # Show sources and document counts
        for source_name, docs in summary.get('source_documents', {}).items():
            print(f"  • {source_name}: {docs} documents")
        
        # Show JSON file location
        json_path = results.get('json_file')
        if json_path:
            print(f"💾 Results saved to: {json_path}")
        
    else:
        print(f"❌ Search failed: {results.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(main())