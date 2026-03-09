#!/usr/bin/env python3
"""
Quick Test Script for Semantic Search System
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the app directory to path
sys.path.insert(0, '/home/naagaraj/marketscoutagent/market-aggregator')

async def quick_test():
    """Run a quick test of the semantic search system"""
    
    print("🧪 Quick Test: Semantic Search System")
    print("=" * 50)
    
    try:
        # Test 1: Import check
        print("📦 Testing imports...")
        from app.simple_semantic_search import SimpleSemanticSearch
        print("✅ Imports successful")
        
        # Test 2: Initialization
        print("🚀 Testing initialization...")
        engine = SimpleSemanticSearch()
        print("✅ Engine initialized")
        
        # Test 3: API validation
        print("🔐 Testing API validation...")
        valid_apis = await engine.validate_apis()
        print(f"✅ API validation completed: {valid_apis}")
        
        # Test 4: Simple search
        print("🔍 Testing simple search...")
        test_query = "NVIDIA AI strategy"
        results = await engine.comprehensive_search(test_query)
        
        # Check results
        if results.get("status") == "success":
            print("✅ Search completed successfully")
            summary = results.get("summary", {})
            print(f"📊 Retrieved {summary.get('total_documents', 0)} documents from {summary.get('successful_sources', 0)} sources")
        else:
            print(f"⚠️  Search completed with status: {results.get('status')}")
            if 'error' in results:
                print(f"Error: {results['error']}")
        
        print("\n" + "=" * 50)
        print("🎉 Quick test completed!")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please install requirements: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(quick_test())
    sys.exit(0 if success else 1)