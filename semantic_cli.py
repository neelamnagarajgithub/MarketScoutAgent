#!/usr/bin/env python3
"""
Enhanced Semantic Search CLI with Better Error Handling
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any
import argparse
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the app directory to the path
sys.path.insert(0, '/home/naagaraj/marketscoutagent/market-aggregator')

class EnhancedSemanticCLI:
    def __init__(self):
        self.engine = None
        self.session_queries = []

    async def initialize(self):
        """Initialize the semantic search engine with validation"""
        try:
            print("🚀 Initializing Enhanced Semantic Search Engine...")
            
            # Check for required environment variables
            required_env = ['GOOGLE_API_KEY']
            missing_env = [env for env in required_env if not os.getenv(env)]
            
            if missing_env:
                print(f"❌ Missing environment variables: {', '.join(missing_env)}")
                print("Please set the required environment variables:")
                for env in missing_env:
                    print(f"  export {env}='your_key_here'")
                return False
            
            # Import and initialize
            from app.simple_semantic_search import SimpleSemanticSearch
            self.engine = SimpleSemanticSearch()
            
            # Validate APIs
            if await self.engine.validate_apis():
                print("✅ Engine ready with validated APIs")
                return True
            else:
                print("⚠️  Engine initialized but some APIs may be invalid")
                return True  # Continue anyway
                
        except ImportError as e:
            print(f"❌ Import error: {e}")
            print("Please ensure all dependencies are installed:")
            print("  pip install -r requirements.txt")
            return False
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            return False

    async def execute_search(self, query: str, format_type: str = "summary") -> Dict[str, Any]:
        """Execute semantic search with specified output format"""
        if not self.engine:
            if not await self.initialize():
                return {"error": "Engine initialization failed"}
        
        print(f"\n🔍 Query: {query}")
        print("⏳ Gathering intelligence from multiple sources...")
        
        try:
            start_time = datetime.now()
            results = await self.engine.comprehensive_search(query)
            duration = (datetime.now() - start_time).total_seconds()
            
            # Track query
            self.session_queries.append({
                "query": query,
                "status": results.get("status"),
                "duration": duration,
                "timestamp": start_time
            })
            
            # Display results based on format
            if format_type == "summary":
                self._display_summary(results)
            elif format_type == "detailed":
                self._display_detailed(results)
            elif format_type == "json":
                print(json.dumps(results, indent=2, default=str))
            
            return results
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return {"error": str(e), "query": query}

    def _display_summary(self, results: Dict[str, Any]):
        """Display concise summary"""
        print("\n" + "="*70)
        print("📊 MARKET INTELLIGENCE RESULTS")
        print("="*70)
        
        # Basic info
        query = results.get("query", "Unknown")
        query_type = results.get("query_type", "unknown")
        status = results.get("status", "unknown")
        
        print(f"Query: {query}")
        print(f"Type: {query_type}")
        print(f"Status: {'✅' if status == 'success' else '❌'} {status}")
        
        # Summary stats
        summary = results.get("summary", {})
        print(f"Confidence: {summary.get('confidence_score', 0.90):.2f}")
        
        print(f"\n📈 Collection Summary:")
        print(f"  Sources Queried: {summary.get('total_sources_queried', 0)}")
        print(f"  Successful Sources: {summary.get('successful_sources', 0)}")
        print(f"  Documents Retrieved: {summary.get('total_documents', 0)}")
        print(f"  Search Terms Used: {summary.get('search_terms_used', 0)}")
        
        # Key insights
        insights = results.get("insights", [])
        if insights:
            print(f"\n💡 Key Insights:")
            for i, insight in enumerate(insights, 1):
                print(f"  {i}. {insight}")
        
        # Recommendations
        recommendations = results.get("recommendations", [])
        if recommendations:
            print(f"\n🎯 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
        # Data sources breakdown
        raw_data = results.get("raw_data", {})
        if raw_data:
            print(f"\n📡 Data Sources:")
            for source_type, source_data in raw_data.items():
                if source_type.startswith('_'):
                    continue
                if source_data:
                    count = sum(len(query_results) for query_results in source_data.values() if isinstance(query_results, dict))
                    print(f"  ✅ {source_type.replace('_', ' ').title()}: {count} items")
                else:
                    print(f"  ❌ {source_type.replace('_', ' ').title()}: failed")
        
        print("="*70)

    def _display_detailed(self, results: Dict[str, Any]):
        """Display detailed results"""
        print("\n" + "="*80)
        print("📊 DETAILED SEMANTIC SEARCH REPORT")
        print("="*80)
        
        # Full JSON output with formatting
        formatted_json = json.dumps(results, indent=2, default=str)
        print(formatted_json)
        print("="*80)

    async def interactive_mode(self):
        """Interactive search session"""
        if not await self.initialize():
            return
        
        print("\n🤖 Enhanced Semantic Market Intelligence - Interactive Mode")
        print("Natural language queries for comprehensive market research")
        print("\nCommands:")
        print("  help     - Show available commands")
        print("  history  - Show query history") 
        print("  format <type> - Set output format (summary/detailed/json)")
        print("  save <file> - Save last results")
        print("  validate - Re-validate API keys")
        print("  exit/quit - Exit session")
        
        print("\nExample Queries:")
        print("  • 'Latest AI startup funding rounds and market trends'")
        print("  • 'NVIDIA competitive position in AI chip market'")
        print("  • 'Emerging fintech companies in Europe 2024'")
        print("  • 'SaaS productivity tools market analysis'")
        print("\n" + "="*70)
        
        format_type = "summary"
        last_results = None
        
        while True:
            try:
                query = input("\n🔍 Query: ").strip()
                
                if not query:
                    continue
                
                # Handle commands
                if query in ['exit', 'quit', 'q']:
                    print("👋 Session ended!")
                    break
                elif query == 'help':
                    print("Available commands: help, history, format, save, validate, exit")
                    continue
                elif query == 'history':
                    self._display_history()
                    continue
                elif query == 'validate':
                    if self.engine:
                        await self.engine.validate_apis()
                    continue
                elif query.startswith('format'):
                    parts = query.split()
                    if len(parts) > 1 and parts[1] in ['summary', 'detailed', 'json']:
                        format_type = parts[1]
                        print(f"Output format set to: {format_type}")
                    else:
                        print("Valid formats: summary, detailed, json")
                    continue
                elif query.startswith('save'):
                    if last_results:
                        filename = query.split()[1] if len(query.split()) > 1 else f"search_{int(datetime.now().timestamp())}.json"
                        self._save_to_file(last_results, filename)
                    else:
                        print("No results to save. Run a query first.")
                    continue
                
                # Execute search
                last_results = await self.execute_search(query, format_type)
                
            except KeyboardInterrupt:
                print("\n👋 Session ended!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

    def _display_history(self):
        """Display query history"""
        if not self.session_queries:
            print("No queries in session history.")
            return
        
        print("\n📜 Query History:")
        print("-" * 60)
        for i, entry in enumerate(self.session_queries, 1):
            status_icon = "✅" if entry["status"] == "success" else "⚠️"
            duration = f"{entry['duration']:.1f}s"
            print(f"{i}. [{entry['timestamp'].strftime('%H:%M')}] {status_icon} {duration}")
            print(f"   {entry['query'][:60]}...")
        print("-" * 60)

    def _save_to_file(self, results: Dict[str, Any], filename: str):
        """Save results to file"""
        try:
            # Ensure search_results directory exists
            os.makedirs('search_results', exist_ok=True)
            filepath = os.path.join('search_results', filename)
            
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"✅ Results saved to: {filepath}")
        except Exception as e:
            print(f"❌ Save failed: {e}")

async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="Enhanced Semantic Market Intelligence Search")
    parser.add_argument('query', nargs='*', help='Search query')
    parser.add_argument('--format', choices=['summary', 'detailed', 'json'], default='summary')
    parser.add_argument('--save', help='Save results to file')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    
    args = parser.parse_args()
    cli = EnhancedSemanticCLI()
    
    if args.interactive or not args.query:
        # Interactive mode
        await cli.interactive_mode()
    else:
        # Direct query mode
        query = " ".join(args.query)
        results = await cli.execute_search(query, args.format)
        
        # Save if requested
        if args.save:
            cli._save_to_file(results, args.save)

if __name__ == "__main__":
    asyncio.run(main())