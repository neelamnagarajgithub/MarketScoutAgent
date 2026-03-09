#!/usr/bin/env python3
"""
Interactive Semantic Search CLI
Easy-to-use interface for market intelligence queries
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Add the app directory to the path
sys.path.insert(0, '/home/naagaraj/marketscoutagent/market-aggregator')

from app.simple_semantic_search import SimpleSemanticSearch

class InteractiveSemanticCLI:
    def __init__(self):
        self.engine = None
        self.session_history = []

    async def initialize(self):
        """Initialize the search engine"""
        try:
            print("🚀 Initializing Market Intelligence Engine...")
            
            # Check for required environment variables
            required_keys = ["GOOGLE_API_KEY"]
            missing_keys = [key for key in required_keys if not os.getenv(key)]
            
            if missing_keys:
                print(f"⚠️  Warning: Missing API keys: {', '.join(missing_keys)}")
                print("Some features may be limited without proper API configuration.")
            
            self.engine = SimpleSemanticSearch()
            print("✅ Engine initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            return False

    async def search(self, query: str, save_results: bool = False, save_json_file: bool = True) -> Dict[str, Any]:
        """Execute semantic search"""
        if not self.engine:
            if not await self.initialize():
                return {"error": "Engine initialization failed"}
        
        print(f"\n🔍 Searching: {query}")
        print("⏳ Gathering intelligence from multiple sources...")
        
        try:
            results = await self.engine.comprehensive_search(query, save_json=save_json_file)
            
            # Store in session history
            self.session_history.append({
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "status": results.get("status"),
                "sources": results.get("summary", {}).get("successful_sources", 0),
                "documents": results.get("summary", {}).get("total_documents", 0)
            })
            
            self._print_results(results)
            
            if save_results:
                self._save_results_to_file(results)
            
            return results
            
        except Exception as e:
            print(f"❌ Search failed: {e}")
            return {"error": str(e), "query": query}

    def _print_results(self, results: Dict[str, Any]):
        """Print formatted search results"""
        print("\n" + "="*70)
        print("📊 MARKET INTELLIGENCE RESULTS")
        print("="*70)
        
        # Basic info
        query = results.get("query", "Unknown")
        status = results.get("status", "unknown")
        query_type = results.get("query_type", "unknown")
        confidence = results.get("confidence_score", 0.0)
        
        print(f"Query: {query}")
        print(f"Type: {query_type}")
        print(f"Status: {'✅' if status == 'success' else '❌'} {status}")
        print(f"Confidence: {confidence:.2f}")
        
        # Summary stats
        summary = results.get("summary", {})
        print(f"\n📈 Collection Summary:")
        print(f"  Sources Queried: {summary.get('total_sources_queried', 0)}")
        print(f"  Successful Sources: {summary.get('successful_sources', 0)}")
        print(f"  Documents Retrieved: {summary.get('total_documents', 0)}")
        print(f"  Search Terms Used: {summary.get('search_terms_used', 0)}")
        
        # Insights
        insights = results.get("insights", [])
        if insights:
            print(f"\n💡 Key Insights:")
            for i, insight in enumerate(insights[:5], 1):
                print(f"  {i}. {insight}")
        
        # Recommendations
        recommendations = results.get("recommendations", [])
        if recommendations:
            print(f"\n🎯 Recommendations:")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"  {i}. {rec}")
        
        # Data source breakdown
        raw_data = results.get("raw_data", {})
        if raw_data:
            print(f"\n📡 Data Sources:")
            for source, data in raw_data.items():
                source_name = source.replace("_", " ").title()
                if isinstance(data, dict) and "error" not in str(data):
                    # Count items in this source
                    item_count = 0
                    if isinstance(data, dict):
                        for key, value in data.items():
                            if isinstance(value, list):
                                item_count += len(value)
                            elif isinstance(value, dict) and "error" not in value:
                                item_count += 1
                    
                    print(f"  ✅ {source_name}: {item_count} items")
                else:
                    print(f"  ❌ {source_name}: failed")
        
        print("="*70)

    def _save_results_to_file(self, results: Dict[str, Any]):
        """Save results to JSON file"""
        try:
            timestamp = int(datetime.now().timestamp())
            filename = f"market_intelligence_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"💾 Results saved to: {filename}")
        except Exception as e:
            print(f"❌ Save failed: {e}")

    def _print_session_history(self):
        """Print session history"""
        if not self.session_history:
            print("No queries in session history.")
            return
        
        print("\n📜 Session History:")
        print("-" * 50)
        for i, entry in enumerate(self.session_history, 1):
            status_icon = "✅" if entry["status"] == "success" else "❌"
            timestamp = entry['timestamp'][:19]  # Remove microseconds
            print(f"{i}. [{timestamp}] {status_icon}")
            print(f"   Query: {entry['query']}")
            print(f"   Sources: {entry['sources']}, Docs: {entry['documents']}")
        print("-" * 50)

    async def interactive_mode(self):
        """Start interactive query session"""
        print("\n🤖 Market Intelligence - Interactive Mode")
        print("="*50)
        print("Type your market intelligence queries in natural language.")
        print("")
        print("Commands:")
        print("  help     - Show available commands")
        print("  history  - Show session history") 
        print("  examples - Show example queries")
        print("  save on/off - Toggle auto-save")
        print("  json on/off - Toggle raw JSON output")
        print("  jsonfile on/off - Toggle JSON file saving")
        print("  last     - Show last result as JSON")
        print("  clear    - Clear screen")
        print("  exit     - Exit interactive mode")
        print("")
        print("Ready for questions! 🚀")
        print("="*50)
        
        auto_save = False
        show_json = False
        save_json_file = True  # Default to saving JSON files
        last_results = None
        
        if not await self.initialize():
            return
        
        while True:
            try:
                query = input("\n🔍 Query: ").strip()
                
                if not query:
                    continue
                
                # Handle commands
                if query.lower() in ['exit', 'quit', 'q']:
                    print("👋 Goodbye! Hope the intelligence was useful.")
                    break
                elif query.lower() == 'help':
                    print("\nAvailable commands:")
                    print("  help, history, examples, save on/off, json on/off, jsonfile on/off, last, clear, exit")
                    print("Or just type natural language queries like:")
                    print("  'What are the latest AI startups?'")
                    continue
                elif query.lower() == 'history':
                    self._print_session_history()
                    continue
                elif query.lower() == 'examples':
                    print("\n💡 Example Queries:")
                    examples = [
                        "What are the latest AI startups getting funding?",
                        "OpenAI competitors and market analysis", 
                        "SaaS market trends and opportunities",
                        "Latest product launches in developer tools",
                        "Microsoft vs Google cloud services comparison",
                        "Cryptocurrency market trends 2026",
                        "Startup funding rounds in fintech"
                    ]
                    for i, ex in enumerate(examples, 1):
                        print(f"  {i}. {ex}")
                    continue
                elif query.lower().startswith('save'):
                    parts = query.split()
                    if len(parts) > 1 and parts[1].lower() in ['on', 'off']:
                        auto_save = parts[1].lower() == 'on'
                        print(f"Auto-save: {'ON' if auto_save else 'OFF'}")
                    else:
                        print(f"Current auto-save: {'ON' if auto_save else 'OFF'}")
                        print("Use 'save on' or 'save off' to toggle")
                    continue
                elif query.lower().startswith('json'):
                    parts = query.split()
                    if len(parts) > 1 and parts[1].lower() in ['on', 'off']:
                        show_json = parts[1].lower() == 'on'
                        print(f"JSON output: {'ON' if show_json else 'OFF'}")
                    else:
                        print(f"Current JSON output: {'ON' if show_json else 'OFF'}")
                        print("Use 'json on' or 'json off' to toggle")
                    continue
                elif query.lower().startswith('jsonfile'):
                    parts = query.split()
                    if len(parts) > 1 and parts[1].lower() in ['on', 'off']:
                        save_json_file = parts[1].lower() == 'on'
                        print(f"JSON file saving: {'ON' if save_json_file else 'OFF'}")
                    else:
                        print(f"Current JSON file saving: {'ON' if save_json_file else 'OFF'}")
                        print("Use 'jsonfile on' or 'jsonfile off' to toggle")
                    continue
                elif query.lower() == 'last':
                    if last_results:
                        print("\n📄 Last Search Results (JSON):")
                        print("=" * 50)
                        print(json.dumps(last_results, indent=2, default=str))
                        print("=" * 50)
                    else:
                        print("No previous results available. Run a search first.")
                    continue
                elif query.lower() == 'clear':
                    os.system('clear' if os.name == 'posix' else 'cls')
                    continue
                
                # Execute search query
                last_results = await self.search(query, auto_save, save_json_file)
                
                # Show JSON if enabled
                if show_json and last_results:
                    print("\n📄 Raw JSON Results:")
                    print("=" * 50)
                    print(json.dumps(last_results, indent=2, default=str))
                    print("=" * 50)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

async def main():
    """Main CLI interface"""
    cli = InteractiveSemanticCLI()
    
    if len(sys.argv) == 1:
        # Interactive mode
        await cli.interactive_mode()
    else:
        # Direct query mode
        query = " ".join(sys.argv[1:])
        
        # Check for flags
        save_results = "--save" in sys.argv or "-s" in sys.argv
        if save_results:
            query = query.replace("--save", "").replace("-s", "").strip()
        
        # Initialize and search
        if await cli.initialize():
            await cli.search(query, save_results)

if __name__ == "__main__":
    asyncio.run(main())