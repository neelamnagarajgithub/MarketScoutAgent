#!/usr/bin/env python3
"""
Comprehensive Test Suite for Semantic Search
"""

import asyncio
import json
import sys
from datetime import datetime

sys.path.insert(0, '/home/naagaraj/marketscoutagent/market-aggregator')

from app.semantic_agent import SemanticSearchEngine

class SemanticSearchTester:
    def __init__(self):
        self.engine = None
        self.test_results = []

    async def initialize(self):
        """Initialize the search engine"""
        try:
            print("🚀 Initializing test environment...")
            self.engine = SemanticSearchEngine()
            print("✅ Test environment ready")
            return True
        except Exception as e:
            print(f"❌ Test initialization failed: {e}")
            return False

    async def run_test_query(self, query: str, expected_sources: int = 2) -> dict:
        """Run a single test query"""
        print(f"\n🧪 Testing: '{query}'")
        print("-" * 50)
        
        start_time = datetime.now()
        
        try:
            result = await self.engine.search(query, save_to_db=False)
            duration = (datetime.now() - start_time).total_seconds()
            
            # Analyze results
            status = result.get("status", "unknown")
            analysis = result.get("analysis", {})
            metadata = result.get("metadata", {})
            
            test_result = {
                "query": query,
                "status": status,
                "duration": round(duration, 2),
                "sources_used": len(metadata.get("sources_used", [])),
                "documents": metadata.get("documents_analyzed", 0),
                "confidence": analysis.get("confidence_score", 0.0),
                "success": status == "success" and len(metadata.get("sources_used", [])) >= expected_sources
            }
            
            # Display results
            status_icon = "✅" if test_result["success"] else "⚠️"
            print(f"{status_icon} Status: {status}")
            print(f"⏱️  Duration: {duration:.2f}s")
            print(f"📊 Sources: {test_result['sources_used']}")
            print(f"📄 Documents: {test_result['documents']}")
            print(f"🎯 Confidence: {test_result['confidence']:.2f}")
            
            if analysis.get("executive_summary"):
                print(f"📋 Summary: {analysis['executive_summary'][:100]}...")
            
            self.test_results.append(test_result)
            return test_result
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            test_result = {
                "query": query,
                "status": "error",
                "duration": (datetime.now() - start_time).total_seconds(),
                "error": str(e),
                "success": False
            }
            self.test_results.append(test_result)
            return test_result

    async def quick_test_suite(self):
        """Run quick test suite"""
        if not await self.initialize():
            return
        
        print("🏃‍♂️ Running Quick Test Suite")
        print("=" * 60)
        
        test_queries = [
            "OpenAI latest product announcements",
            "AI startup funding trends 2024", 
            "NVIDIA competitive analysis"
        ]
        
        for query in test_queries:
            await self.run_test_query(query)
        
        self._display_test_summary()

    async def comprehensive_test_suite(self):
        """Run comprehensive test suite"""
        if not await self.initialize():
            return
        
        print("🔬 Running Comprehensive Test Suite")  
        print("=" * 60)
        
        test_queries = [
            # Company Analysis
            "Tesla market position and competitors",
            "Microsoft AI strategy and partnerships",
            
            # Market Trends
            "SaaS market growth and opportunities",
            "Fintech innovations in 2024",
            
            # Product Research  
            "Developer tools trending in 2024",
            "Cloud infrastructure market leaders",
            
            # Funding Intelligence
            "Series A funding rounds in AI startups",
            "Venture capital trends in Europe",
            
            # Technology Stack
            "Popular JavaScript frameworks 2024",
            "Enterprise database technology trends"
        ]
        
        for query in test_queries:
            await self.run_test_query(query)
        
        self._display_test_summary()

    def _display_test_summary(self):
        """Display comprehensive test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r.get("success"))
        failed_tests = total_tests - successful_tests
        
        avg_duration = sum(r.get("duration", 0) for r in self.test_results) / total_tests if total_tests > 0 else 0
        avg_confidence = sum(r.get("confidence", 0) for r in self.test_results) / total_tests if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Successful: {successful_tests} ({successful_tests/total_tests*100:.1f}%)")
        print(f"❌ Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        print(f"⏱️  Average Duration: {avg_duration:.2f}s")
        print(f"🎯 Average Confidence: {avg_confidence:.2f}")
        
        print(f"\n📈 Performance Breakdown:")
        for result in self.test_results:
            status = "✅" if result.get("success") else "❌"
            print(f"{status} {result['query'][:40]}... ({result['duration']:.1f}s)")
        
        print("=" * 60)
        
        # Save detailed results
        filename = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "successful": successful_tests,
                    "failed": failed_tests,
                    "success_rate": successful_tests/total_tests if total_tests > 0 else 0,
                    "avg_duration": avg_duration,
                    "avg_confidence": avg_confidence
                },
                "detailed_results": self.test_results
            }, f, indent=2, default=str)
        
        print(f"💾 Detailed results saved to: {filename}")

async def main():
    """Main test runner"""
    tester = SemanticSearchTester()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "quick":
            await tester.quick_test_suite()
        elif command == "full":
            await tester.comprehensive_test_suite()
        elif command == "single":
            if len(sys.argv) > 2:
                query = " ".join(sys.argv[2:])
                await tester.initialize()
                await tester.run_test_query(query)
            else:
                print("Usage: python test_semantic.py single 'your query'")
        else:
            print("Usage:")
            print("  python test_semantic.py quick    # Quick 3-query test")
            print("  python test_semantic.py full     # Comprehensive test suite")  
            print("  python test_semantic.py single 'query'  # Test single query")
    else:
        # Default to quick test
        await tester.quick_test_suite()

if __name__ == "__main__":
    asyncio.run(main())