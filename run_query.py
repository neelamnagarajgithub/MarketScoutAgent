#!/usr/bin/env python3
"""
Simple Query Runner with Automatic JSON Saving
Usage: python run_query.py "your query here"
"""

import asyncio
import sys
import os
from datetime import datetime
from app.simple_semantic_search import search

async def main():
    if len(sys.argv) < 2:
        print("Usage: python run_query.py 'your search query'")
        print("\nExample:")
        print("  python run_query.py 'NVIDIA AI business strategy'")
        print("  python run_query.py 'OpenAI competitors analysis'")
        print("  python run_query.py 'SaaS market trends 2026'")
        return
    
    query = " ".join(sys.argv[1:])
    
    print(f"🔍 Executing Query: {query}")
    print("⏳ Gathering data and saving JSON...")
    print("=" * 60)
    
    # Execute search with JSON saving enabled
    results = await search(query, save_json=True)
    
    # Print summary
    status = results.get("status", "unknown")
    confidence = results.get("confidence_score", 0.0)
    sources = results.get("summary", {}).get("successful_sources", 0)
    docs = results.get("summary", {}).get("total_documents", 0)
    json_file = results.get("json_file_saved", "Not saved")
    
    print(f"\n📊 Results Summary:")
    print(f"  Status: {'✅ Success' if status == 'success' else '❌ Failed'}")
    print(f"  Confidence: {confidence:.2f}")
    print(f"  Data Sources: {sources}")
    print(f"  Documents Retrieved: {docs}")
    print(f"  JSON File: {json_file}")
    
    # Show insights
    insights = results.get("insights", [])
    if insights:
        print(f"\n💡 Key Insights:")
        for i, insight in enumerate(insights[:3], 1):
            print(f"  {i}. {insight}")
    
    # Show recommendations
    recommendations = results.get("recommendations", [])
    if recommendations:
        print(f"\n🎯 Recommendations:")
        for i, rec in enumerate(recommendations[:2], 1):
            print(f"  {i}. {rec}")
    
    print("\n" + "=" * 60)
    
    if status == "success":
        print("✅ Query completed successfully!")
        if json_file != "Not saved":
            print(f"📁 Full JSON results saved to: {json_file}")
    else:
        error = results.get("error", "Unknown error")
        print(f"❌ Query failed: {error}")

if __name__ == "__main__":
    asyncio.run(main())