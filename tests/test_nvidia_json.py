#!/usr/bin/env python3
"""
Quick test to show JSON output from your NVIDIA query with auto-save
"""

import asyncio
import json
from app.simple_semantic_search import SimpleSemanticSearch

async def test_nvidia_query():
    print("🔍 Testing NVIDIA query with JSON output and auto-save...")
    
    engine = SimpleSemanticSearch()
    results = await engine.comprehensive_search("NVIDIA AI business strategy and new product announcements", save_json=True)
    
    json_file_saved = results.get("json_file_saved", "Not saved")
    
    print("\n📄 FULL JSON RESPONSE:")
    print("=" * 80)
    print(json.dumps(results, indent=2, default=str))
    print("=" * 80)
    
    print(f"\n🎯 Summary:")
    print(f"Status: {results.get('status')}")
    print(f"Sources: {results.get('summary', {}).get('successful_sources', 0)}")
    print(f"Documents: {results.get('summary', {}).get('total_documents', 0)}")
    print(f"📁 JSON File Saved: {json_file_saved}")

if __name__ == "__main__":
    asyncio.run(test_nvidia_query())