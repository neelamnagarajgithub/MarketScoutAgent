# app/agent.py
import asyncio
import httpx
import json
import os
from typing import Dict, Any, List
from datetime import datetime
import logging

# LangChain imports - compatible versions
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import Tool

# Local imports
import yaml
from app.fetchers import (
    serpapi, newsapi, github, npm_pypi, rss,
    news_sources, search_apis, business_intelligence,
    community_sources, financial_apis
)
from app.normalizer import normalize_item
from app.db import Database

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketIntelligenceAgent:
    def __init__(self, config_path="config.yaml"):
        # Load configuration
        with open(config_path, "r") as fh:
            self.config = yaml.safe_load(fh)
        
        # Initialize Gemini LLM
        gemini_api_key = os.getenv("GOOGLE_API_KEY")
        if not gemini_api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=gemini_api_key,
            temperature=0.1,
            max_tokens=4096
        )
        
        # Initialize database
        self.db = Database(self.config)
        
        # Initialize tools
        self.tools = self._create_tools()
        
        # Create agent
        self.agent = self._create_agent()
    
    def _create_tools(self) -> List[Tool]:
        """Create LangChain tools for different data sources"""
        
        def search_discovery(query: str) -> str:
            """Search for market intelligence using various search APIs"""
            async def _search():
                results = {}
                async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                    # SerpAPI
                    serp_key = self.config['keys'].get('serpapi')
                    if serp_key:
                        try:
                            serp_results = await serpapi.serp_search(
                                client, serp_key, query,
                                engine=self.config['keys'].get('serpapi_engine', 'google')
                            )
                            results['serpapi'] = serp_results[:5]
                        except Exception as e:
                            results['serpapi'] = f"Error: {e}"
                    
                    # Bing Search
                    bing_key = self.config['keys'].get('bing_search')
                    if bing_key:
                        try:
                            bing_results = await search_apis.fetch_bing_search(client, bing_key, query)
                            results['bing'] = bing_results[:5]
                        except Exception as e:
                            results['bing'] = f"Error: {e}"
                return results
            
            try:
                results = asyncio.run(_search())
                return json.dumps(results, indent=2, default=str)
            except Exception as e:
                return json.dumps({"error": str(e)}, indent=2)
        
        def news_intelligence(query: str) -> str:
            """Gather news and market intelligence from multiple news APIs"""
            async def _news():
                results = {}
                async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                    # NewsAPI
                    news_key = self.config['keys'].get('newsapi')
                    if news_key:
                        try:
                            news_results = await newsapi.search_newsapi(client, news_key, query)
                            results['newsapi'] = news_results[:5]
                        except Exception as e:
                            results['newsapi'] = f"Error: {e}"
                    
                    # GNews
                    gnews_key = self.config['keys'].get('gnews')
                    if gnews_key:
                        try:
                            gnews_results = await news_sources.fetch_gnews(client, gnews_key, query)
                            results['gnews'] = gnews_results[:5]
                        except Exception as e:
                            results['gnews'] = f"Error: {e}"
                    
                    # Currents API
                    currents_key = self.config['keys'].get('currents')
                    if currents_key:
                        try:
                            currents_results = await news_sources.fetch_currents_api(client, currents_key, query)
                            results['currents'] = currents_results[:5]
                        except Exception as e:
                            results['currents'] = f"Error: {e}"
                return results
            
            try:
                results = asyncio.run(_news())
                return json.dumps(results, indent=2, default=str)
            except Exception as e:
                return json.dumps({"error": str(e)}, indent=2)
        
        def tech_product_intelligence(query: str) -> str:
            """Gather intelligence from GitHub, npm, PyPI"""
            async def _tech():
                results = {}
                async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                    # GitHub
                    gh_key = self.config['keys'].get('github')
                    if gh_key:
                        try:
                            github_results = {}
                            orgs = self.config.get('sources', {}).get('github_orgs', ['openai', 'vercel'])
                            for org in orgs[:2]:
                                org_repos = await github.fetch_org_repos(client, gh_key, org)
                                if isinstance(org_repos, list) and len(org_repos) > 0:
                                    sorted_repos = sorted(org_repos, key=lambda x: x.get('updated_at', ''), reverse=True)
                                    github_results[org] = sorted_repos[:3]
                                else:
                                    github_results[org] = org_repos
                            results['github'] = github_results
                        except Exception as e:
                            results['github'] = f"Error: {e}"
                    
                    # NPM packages
                    try:
                        npm_results = {}
                        popular_npm = ["react", "vue", "next"]
                        for pkg in popular_npm:
                            npm_data = await npm_pypi.fetch_npm_package(client, pkg)
                            if npm_data:
                                npm_results[pkg] = {
                                    "name": npm_data.get("name"),
                                    "description": npm_data.get("description", "")[:200],
                                    "latest_version": npm_data.get("dist-tags", {}).get("latest"),
                                    "homepage": npm_data.get("homepage")
                                }
                        results['npm'] = npm_results
                    except Exception as e:
                        results['npm'] = f"Error: {e}"
                return results
            
            try:
                results = asyncio.run(_tech())
                return json.dumps(results, indent=2, default=str)
            except Exception as e:
                return json.dumps({"error": str(e)}, indent=2)
        
        def community_intelligence(topic: str) -> str:
            """Gather intelligence from Hacker News and community sources"""
            async def _community():
                results = {}
                async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                    # Hacker News
                    try:
                        hn_top = await community_sources.fetch_hackernews_stories(client, "topstories", 5)
                        hn_new = await community_sources.fetch_hackernews_stories(client, "newstories", 5)
                        results['hackernews'] = {
                            'topstories': hn_top,
                            'newstories': hn_new
                        }
                    except Exception as e:
                        results['hackernews'] = f"Error: {e}"
                return results
            
            try:
                results = asyncio.run(_community())
                return json.dumps(results, indent=2, default=str)
            except Exception as e:
                return json.dumps({"error": str(e)}, indent=2)
        
        def financial_intelligence(symbols: str) -> str:
            """Gather financial intelligence and company data"""
            async def _financial():
                results = {}
                symbol_list = [s.strip().upper() for s in symbols.split(',') if s.strip()]
                
                async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                    # Alpha Vantage
                    av_key = self.config['keys'].get('alpha_vantage')
                    if av_key and symbol_list:
                        try:
                            av_results = {}
                            for symbol in symbol_list[:2]:
                                overview = await financial_apis.fetch_alpha_vantage_company_overview(
                                    client, av_key, symbol
                                )
                                if overview:
                                    av_results[symbol] = overview
                            
                            # Company news
                            news = await financial_apis.fetch_company_news_alpha_vantage(
                                client, av_key, ','.join(symbol_list[:2])
                            )
                            if isinstance(news, list) and news:
                                av_results['news'] = news[:3]
                            
                            results['alpha_vantage'] = av_results
                        except Exception as e:
                            results['alpha_vantage'] = f"Error: {e}"
                return results
            
            try:
                results = asyncio.run(_financial())
                return json.dumps(results, indent=2, default=str)
            except Exception as e:
                return json.dumps({"error": str(e)}, indent=2)
        
        def rss_intelligence(limit: str = "5") -> str:
            """Gather intelligence from RSS feeds of major tech companies"""
            async def _rss():
                results = {}
                try:
                    limit_num = int(limit) if limit.isdigit() else 5
                except:
                    limit_num = 5
                    
                rss_feeds = self.config.get('sources', {}).get('rss_feeds', [])
                
                for feed_url in rss_feeds[:3]:
                    try:
                        feed_name = feed_url.split('//')[1].split('/')[0].replace('blog.', '').replace('www.', '')
                        feed_data = await asyncio.to_thread(rss.fetch_rss_feed, feed_url, limit_num)
                        results[feed_name] = feed_data
                    except Exception as e:
                        feed_name = feed_url.split('//')[1].split('/')[0] if '//' in feed_url else feed_url
                        results[feed_name] = f"Error: {e}"
                return results
            
            try:
                results = asyncio.run(_rss())
                return json.dumps(results, indent=2, default=str)
            except Exception as e:
                return json.dumps({"error": str(e)}, indent=2)
        
        # Create LangChain Tool objects
        tools = [
            Tool(
                name="search_discovery",
                description="Search for market intelligence using SerpAPI, Bing Search. Input should be a search query string.",
                func=search_discovery
            ),
            Tool(
                name="news_intelligence", 
                description="Gather news and market intelligence from NewsAPI, GNews, Currents API. Input should be a search query string.",
                func=news_intelligence
            ),
            Tool(
                name="tech_product_intelligence",
                description="Gather intelligence from GitHub organizations, npm packages. Input should be a topic or company name.",
                func=tech_product_intelligence
            ),
            Tool(
                name="community_intelligence",
                description="Gather intelligence from Hacker News and community sources. Input should be a topic string.",
                func=community_intelligence
            ),
            Tool(
                name="financial_intelligence",
                description="Gather financial intelligence from Alpha Vantage. Input should be comma-separated stock symbols (e.g., 'MSFT,GOOGL').",
                func=financial_intelligence
            ),
            Tool(
                name="rss_intelligence",
                description="Gather intelligence from RSS feeds of tech companies. Input should be number of articles to fetch (e.g., '5').",
                func=rss_intelligence
            )
        ]
        
        return tools
    
    def _create_agent(self):
        """Create the ReAct agent with tools"""
        
        prompt_template = PromptTemplate(
            input_variables=["tools", "tool_names", "input", "agent_scratchpad"],
            template="""
        You are a comprehensive market intelligence agent with access to multiple data sources.

        Available tools:
        {tools}

        Tool names: {tool_names}

        Your task is to gather comprehensive market intelligence based on the user's query. 

        Always use the following format:

        Thought: I need to gather data from multiple sources to provide comprehensive market intelligence.
        Action: [tool_name]
        Action Input: [input for the tool]
        Observation: [result from the tool]
        ... (repeat Thought/Action/Action Input/Observation as needed)
        Thought: I now have enough information to provide a comprehensive response.
        Final Answer: [comprehensive JSON response with all gathered data]

        When providing the Final Answer, structure it as a JSON with the following format:
        {{
            "summary": "Brief summary of findings",
            "timestamp": "current timestamp",
            "sources": {{
                "search_discovery": {{}},
                "news_intelligence": {{}},
                "tech_product": {{}},
                "community": {{}},
                "financial": {{}},
                "rss_feeds": {{}}
            }},
            "key_insights": ["insight 1", "insight 2", "..."],
            "recommendations": ["recommendation 1", "recommendation 2", "..."]
        }}
        Human: {input}

        Agent Scratchpad: {agent_scratchpad}"""
        )
        
        return create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt_template
        )
    
    async def comprehensive_intelligence_gathering(self, query: str = "AI startups and product launches") -> Dict[str, Any]:
        """Gather comprehensive market intelligence from all sources"""
        logger.info(f"Starting comprehensive intelligence gathering for: {query}")
        
        try:
            # Initialize the agent executor
            agent_executor = AgentExecutor(
                agent=self.agent,
                tools=self.tools,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=15,
                max_execution_time=300
            )
            
            # Enhanced prompt for comprehensive data gathering
            enhanced_query = f"""
            Gather comprehensive market intelligence for: {query}
            
            Please collect data from ALL available sources:
            1. Use search_discovery to find recent mentions and trends
            2. Use news_intelligence to get latest news coverage  
            3. Use tech_product_intelligence to track development activity
            4. Use community_intelligence to see community discussions
            5. Use financial_intelligence with symbols like 'MSFT,GOOGL' for financial data
            6. Use rss_intelligence to get latest company blog updates (use limit '5')
            
            Provide a comprehensive JSON response with all gathered data.
            """
            
            # Execute the agent
            result = agent_executor.invoke({"input": enhanced_query})
            
            # Parse and structure the result
            final_response = self._structure_response(result.get("output", ""), query)
            
            # Save to database if enabled
            await self._save_intelligence_to_db(final_response)
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error in comprehensive intelligence gathering: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "status": "failed"
            }
    
    def _structure_response(self, agent_output: str, original_query: str) -> Dict[str, Any]:
        """Structure the agent output into a proper JSON response"""
        try:
            # Try to parse JSON from agent output
            if "{" in agent_output and "}" in agent_output:
                json_start = agent_output.find("{")
                json_end = agent_output.rfind("}") + 1
                json_str = agent_output[json_start:json_end]
                try:
                    parsed_data = json.loads(json_str)
                    
                    # Ensure required structure
                    structured_response = {
                        "summary": parsed_data.get("summary", "Market intelligence data gathered successfully"),
                        "timestamp": datetime.now().isoformat(),
                        "query": original_query,
                        "sources": parsed_data.get("sources", {}),
                        "key_insights": parsed_data.get("key_insights", []),
                        "recommendations": parsed_data.get("recommendations", []),
                        "status": "success",
                        "raw_agent_output": agent_output[:1000]  # Truncate for storage
                    }
                    
                    return structured_response
                except json.JSONDecodeError:
                    # If JSON parsing fails, fall through to raw output handling
                    pass
            
            # Fallback structure if JSON parsing fails
            return {
                "summary": "Intelligence gathering completed with partial results",
                "timestamp": datetime.now().isoformat(),
                "query": original_query,
                "sources": self._extract_partial_data(agent_output),
                "key_insights": self._extract_insights(agent_output),
                "recommendations": ["Review gathered data for market trends", "Monitor mentioned companies"],
                "status": "partial",
                "raw_agent_output": agent_output[:1000],
                "note": "Could not parse structured JSON from agent output"
            }
                
        except Exception as e:
            logger.error(f"Response structuring error: {e}")
            return {
                "error": f"Response parsing failed: {e}",
                "timestamp": datetime.now().isoformat(),
                "query": original_query,
                "status": "parsing_error",
                "raw_agent_output": agent_output[:1000] if agent_output else "No output"
            }
    
    def _extract_partial_data(self, output: str) -> Dict[str, Any]:
        """Extract partial structured data from raw output"""
        sources = {}
        
        # Simple pattern matching for different data sources
        if "serpapi" in output.lower():
            sources["search_discovery"] = {"serpapi": "Data found"}
        if "newsapi" in output.lower() or "news" in output.lower():
            sources["news_intelligence"] = {"newsapi": "News data found"}
        if "github" in output.lower():
            sources["tech_product"] = {"github": "GitHub data found"}
        if "hackernews" in output.lower():
            sources["community"] = {"hackernews": "Community data found"}
        if "alpha_vantage" in output.lower():
            sources["financial"] = {"alpha_vantage": "Financial data found"}
        
        return sources
    
    def _extract_insights(self, output: str) -> List[str]:
        """Extract insights from raw output"""
        insights = []
        
        # Simple keyword-based insight extraction
        if "ai" in output.lower() or "artificial intelligence" in output.lower():
            insights.append("AI-related activity detected")
        if "startup" in output.lower():
            insights.append("Startup ecosystem activity found")
        if "funding" in output.lower():
            insights.append("Funding announcements discovered")
        if "product" in output.lower() and ("launch" in output.lower() or "release" in output.lower()):
            insights.append("Product launches identified")
        
        return insights if insights else ["Market intelligence data collected successfully"]
    
    async def _save_intelligence_to_db(self, intelligence_data: Dict[str, Any]):
        """Save intelligence data to database"""
        try:
            await self.db.init_models()
            
            # Create a document entry for the intelligence report
            doc = {
                "source": "market_intelligence_agent",
                "title": f"Market Intelligence Report - {intelligence_data.get('query')}",
                "url": f"internal://intelligence_report_{int(datetime.now().timestamp())}",
                "content": json.dumps(intelligence_data, indent=2),
                "published_at": datetime.now(),
                "metadata": {
                    "provider": "gemini_langchain_agent",
                    "query": intelligence_data.get("query"),
                    "status": intelligence_data.get("status"),
                    "sources_count": len(intelligence_data.get("sources", {}))
                },
                "content_hash": str(hash(json.dumps(intelligence_data, sort_keys=True)))[:64]
            }
            
            await self.db.save_document(doc)
            logger.info("Intelligence report saved to database")
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")

# Convenience functions for common use cases
async def analyze_company(company_name: str, config_path: str = "config.yaml") -> Dict[str, Any]:
    """Analyze a specific company"""
    agent = MarketIntelligenceAgent(config_path)
    return await agent.comprehensive_intelligence_gathering(f"comprehensive analysis of {company_name}")

async def analyze_product(product_name: str, config_path: str = "config.yaml") -> Dict[str, Any]:
    """Analyze a specific product"""
    agent = MarketIntelligenceAgent(config_path)
    return await agent.comprehensive_intelligence_gathering(f"product analysis of {product_name}")

async def analyze_market_trend(trend: str, config_path: str = "config.yaml") -> Dict[str, Any]:
    """Analyze a market trend"""
    agent = MarketIntelligenceAgent(config_path)
    return await agent.comprehensive_intelligence_gathering(f"market trend analysis of {trend}")

async def comprehensive_market_scan(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Perform comprehensive market intelligence scan"""
    agent = MarketIntelligenceAgent(config_path)
    return await agent.comprehensive_intelligence_gathering(
        "comprehensive market intelligence scan for AI companies, startups, product launches, and emerging trends"
    )

# Main execution function
async def main():
    """Main execution function for testing"""
    try:
        logger.info("Starting Market Intelligence Agent")
        
        # Initialize agent
        agent = MarketIntelligenceAgent()
        
        # Run comprehensive intelligence gathering
        result = await agent.comprehensive_intelligence_gathering(
            "AI startups, product launches, and funding announcements in 2024"
        )
        
        # Print formatted results
        print("\n" + "="*80)
        print("COMPREHENSIVE MARKET INTELLIGENCE REPORT")
        print("="*80)
        print(json.dumps(result, indent=2, default=str))
        print("="*80)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    # Run the agent
    result = asyncio.run(main())