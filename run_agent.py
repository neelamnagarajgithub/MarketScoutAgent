#!/usr/bin/env python3
"""
Market Intelligence Agent Runner
Provides a simple interface to run comprehensive market intelligence gathering
"""

import asyncio
import json
import os
from datetime import datetime
import sys

# Add the app directory to the path
sys.path.insert(0, '/home/naagaraj/marketscoutagent/market-aggregator')

from app.agent import MarketIntelligenceAgent, comprehensive_market_scan, analyze_company

async def run_comprehensive_scan():
    """Run comprehensive market intelligence scan"""
    print("🚀 Starting Comprehensive Market Intelligence Scan")
    print("=" * 80)
    
    try:
        # Set the Google API key
        if not os.getenv("GOOGLE_API_KEY"):
            print("❌ Error: GOOGLE_API_KEY environment variable not set")
            print("Please set your Gemini API key:")
            print("export GOOGLE_API_KEY='your_api_key_here'")
            return
        
        # Initialize and run the agent
        agent = MarketIntelligenceAgent(config_path="config.yaml")
        
        # Run comprehensive intelligence gathering
        result = await agent.comprehensive_intelligence_gathering(
            "AI and machine learning startups, new product launches, funding announcements, and market trends in 2024"
        )
        
        # Display results
        print("📊 COMPREHENSIVE MARKET INTELLIGENCE REPORT")
        print("=" * 80)
        
        # Pretty print results
        formatted_result = json.dumps(result, indent=2, default=str)
        print(formatted_result)
        
        # Save to file
        output_file = f"market_intelligence_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"📝 Report saved to: {output_file}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

async def run_company_analysis(company_name: str):
    """Analyze a specific company"""
    print(f"🏢 Analyzing Company: {company_name}")
    print("=" * 80)
    
    try:
        if not os.getenv("GOOGLE_API_KEY"):
            print("❌ Error: GOOGLE_API_KEY environment variable not set")
            return
            
        result = await analyze_company(company_name)
        
        print("📊 COMPANY ANALYSIS REPORT")
        print("=" * 80)
        
        formatted_result = json.dumps(result, indent=2, default=str)
        print(formatted_result)
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    """Main function to run the agent"""
    print("🤖 Market Intelligence Agent")
    print("=" * 40)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python run_agent.py scan                    # Comprehensive market scan")
        print("  python run_agent.py company 'OpenAI'        # Analyze specific company")
        print("  python run_agent.py trend 'AI automation'   # Analyze market trend")
        return
    
    command = sys.argv[1].lower()
    
    if command == "scan":
        asyncio.run(run_comprehensive_scan())
    elif command == "company" and len(sys.argv) > 2:
        company = sys.argv[2]
        asyncio.run(run_company_analysis(company))
    elif command == "trend" and len(sys.argv) > 2:
        trend = sys.argv[2]
        asyncio.run(run_comprehensive_scan())  # Use generic scan for trends
    else:
        print("❌ Invalid command or missing parameters")

if __name__ == "__main__":
    main()