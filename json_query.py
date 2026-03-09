#!/usr/bin/env python3
"""
Quick JSON query tool - Get raw JSON results from semantic search
"""

import asyncio
import json
import sys
from app.simple_semantic_search import SimpleSemanticSearch

async def main():
    if len(sys.argv) < 2:
        print("Usage: python json_query.py 'your search query'")
        print("Returns raw JSON results from semantic search")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    
    engine = SimpleSemanticSearch() 
    results = await engine.comprehensive_search(query)
    
    # Print just the JSON
    print(json.dumps(results, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())