# app/semantic_agent.py
import asyncio
import httpx
import json
import os
import uuid
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

# LangChain imports (assumes compatible versions installed)
from langchain.agents import create_agent as create_react_agent
# from langchain.agents import AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import Tool
from langchain.messages import HumanMessage

# Embeddings + Pinecone
from sentence_transformers import SentenceTransformer
import pinecone

# Local imports (your existing modules)
import yaml
from app.fetchers import (
    serpapi, newsapi, github, npm_pypi, rss,
    news_sources, search_apis, business_intelligence,
    community_sources, financial_apis
)
from app.normalizer import normalize_item
from app.db import Database

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueryPlanner:
    """Simple query planner that asks the LLM (or falls back to rules)."""

    def __init__(self, llm):
        self.llm = llm

    async def plan_query(self, user_query: str) -> Dict[str, Any]:
        planning_prompt = f"""
Analyze this user query and return a JSON plan for which sources to query.

User Query: "{user_query}"

Available data sources:
1. search_discovery
2. news_intelligence
3. tech_product_intelligence
4. community_intelligence
5. financial_intelligence
6. rss_intelligence

Return a JSON object like:
{{
  "original_query": "{user_query}",
  "primary_sources": ["search_discovery", "news_intelligence"],
  "secondary_sources": [],
  "search_terms": ["term1", "term2"],
  "financial_symbols": [],
  "focus_areas": [],
  "query_type": "company_analysis|market_trend|product_research|competitive_intelligence"
}}
"""
        try:
            # ChatGoogleGenerativeAI returns an object; adapt if your library differs.
            resp = self.llm.invoke([HumanMessage(content=planning_prompt)])
            text = getattr(resp, "content", str(resp))
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                plan = json.loads(match.group())
                # ensure minimal fields
                plan.setdefault("original_query", user_query)
                plan.setdefault("search_terms", [user_query])
                plan.setdefault("primary_sources", ["search_discovery", "news_intelligence"])
                plan.setdefault("secondary_sources", [])
                plan.setdefault("financial_symbols", [])
                plan.setdefault("focus_areas", [])
                plan.setdefault("query_type", "general_research")
                return plan
        except Exception as e:
            logger.debug("LLM planning failed, falling back to rules: %s", e)

        # fallback rules-based plan
        return self._create_fallback_plan(user_query)

    def _create_fallback_plan(self, query: str) -> Dict[str, Any]:
        q = query.lower()
        plan = {
            "original_query": query,
            "primary_sources": ["search_discovery", "news_intelligence"],
            "secondary_sources": [],
            "search_terms": [query],
            "financial_symbols": [],
            "focus_areas": ["general"],
            "query_type": "general_research",
        }
        if any(k in q for k in ["company", "startup", "inc", "corp", "llc"]):
            plan["query_type"] = "company_analysis"
            plan["primary_sources"].extend(["tech_product_intelligence", "financial_intelligence"])
        if any(k in q for k in ["product", "launch", "release", "feature"]):
            plan["query_type"] = "product_research"
            plan["primary_sources"].extend(["tech_product_intelligence", "community_intelligence"])
        if any(k in q for k in ["trend", "market", "industry", "sector"]):
            plan["query_type"] = "market_trend"
            plan["primary_sources"].extend(["community_intelligence", "rss_intelligence"])
        if any(k in q for k in ["ai", "artificial intelligence", "ml", "machine learning"]):
            plan["focus_areas"] = ["artificial_intelligence", "machine_learning"]
            plan["financial_symbols"] = ["GOOGL", "MSFT", "NVDA"]
        symbols = re.findall(r"\b[A-Z]{2,5}\b", query)
        if symbols:
            plan["financial_symbols"].extend(symbols)
        return plan


class SemanticMarketAgent:
    """Market intelligence agent with semantic search using Pinecone."""

    def __init__(self, config_path="config.yaml"):
        # load config
        with open(config_path, "r") as fh:
            self.config = yaml.safe_load(fh)

        # LLM (Gemini)
        gemini_api_key = os.getenv("GOOGLE_API_KEY")
        if not gemini_api_key:
            raise ValueError("GOOGLE_API_KEY is required in env")
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=gemini_api_key,
            temperature=0.1,
            max_output_tokens=4096,
        )

        # DB + planner
        self.db = Database(self.config)
        self.query_planner = QueryPlanner(self.llm)

        # Embedding model (local SBERT) and Pinecone init
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        pine_api_key = os.getenv("PINECONE_API_KEY")
        pine_env = os.getenv("PINECONE_ENV")
        if not pine_api_key or not pine_env:
            logger.warning(
                "PINECONE_API_KEY or PINECONE_ENV not set — semantic storage will be disabled until configured."
            )
            self.pine_enabled = False
            self.pine_index = None
        else:
            self.pine_enabled = True
            pinecone.init(api_key=pine_api_key, environment=pine_env)
            index_name = self.config.get("pinecone_index", "market-intel")
            # create index if missing
            emb_dim = len(self.embedding_model.encode("test", show_progress_bar=False))
            if index_name not in pinecone.list_indexes():
                pinecone.create_index(index_name, dimension=emb_dim, metric="cosine")
            self.pine_index = pinecone.Index(index_name)

        # create tools and agent
        self.tools = self._create_tools()
        self.agent = self._create_agent()

    # ----------------------
    # Embedding + Pinecone utilities
    # ----------------------
    def embed_text(self, text: str) -> List[float]:
        return self.embedding_model.encode(text, show_progress_bar=False).tolist()

    def upsert_documents_to_pinecone(self, docs: List[Dict[str, Any]]):
        """
        docs: list of { 'id': str, 'text': str, 'metadata': {...} }
        """
        if not self.pine_enabled or not self.pine_index:
            logger.debug("Pinecone not configured; skipping upsert")
            return
        vectors = []
        for d in docs:
            vec = self.embed_text(d["text"])
            vec_id = d.get("id") or str(uuid.uuid4())
            vectors.append((vec_id, vec, d.get("metadata", {})))
        self.pine_index.upsert(vectors=vectors)

    def semantic_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.pine_enabled or not self.pine_index:
            return []
        qvec = self.embed_text(query)
        resp = self.pine_index.query(vector=qvec, top_k=top_k, include_metadata=True)
        matches = []
        for m in resp["matches"]:
            matches.append({"id": m["id"], "score": m["score"], "metadata": m.get("metadata")})
        return matches

    # ----------------------
    # Tools (async)
    # ----------------------
    def _create_tools(self) -> List[Tool]:
        # Each tool is an async def and returns JSON string
        async def intelligent_search_discovery(query_plan: str) -> str:
            try:
                plan = json.loads(query_plan)
            except Exception:
                plan = {"search_terms": [query_plan], "original_query": query_plan}
            search_terms = plan.get("search_terms", [plan.get("original_query", "")])[:3]
            results = {}
            async with httpx.AsyncClient(timeout=30) as client:
                serp_key = self.config.get("keys", {}).get("serpapi")
                bing_key = self.config.get("keys", {}).get("bing_search")
                for term in search_terms:
                    term_res = {}
                    if serp_key:
                        try:
                            serp = await serpapi.serp_search(client, serp_key, term, engine=self.config.get("keys", {}).get("serpapi_engine", "google"))
                            term_res["serpapi"] = serp[:5]
                        except Exception as e:
                            term_res["serpapi"] = {"error": str(e)}
                    if bing_key:
                        try:
                            bing = await search_apis.fetch_bing_search(client, bing_key, term)
                            term_res["bing"] = bing[:5]
                        except Exception as e:
                            term_res["bing"] = {"error": str(e)}
                    # semantic recall from Pinecone (optional)
                    sem = self.semantic_search(term, top_k=3)
                    term_res["semantic_matches"] = sem
                    results[term] = term_res
            return json.dumps(results, default=str, indent=2)

        async def intelligent_news_gathering(query_plan: str) -> str:
            try:
                plan = json.loads(query_plan)
            except Exception:
                plan = {"search_terms": [query_plan], "focus_areas": []}
            search_terms = plan.get("search_terms", [])[:3]
            focus_areas = plan.get("focus_areas", [])[:2]
            results = {}
            async with httpx.AsyncClient(timeout=30) as client:
                for term in search_terms:
                    term_res = {}
                    news_key = self.config.get("keys", {}).get("newsapi")
                    if news_key:
                        try:
                            nd = await newsapi.search_newsapi(client, news_key, term)
                            term_res["newsapi"] = nd[:6]
                        except Exception as e:
                            term_res["newsapi"] = {"error": str(e)}
                    gnews_key = self.config.get("keys", {}).get("gnews")
                    if gnews_key:
                        try:
                            gd = await news_sources.fetch_gnews(client, gnews_key, term)
                            term_res["gnews"] = gd[:6]
                        except Exception as e:
                            term_res["gnews"] = {"error": str(e)}
                    # combine focus areas
                    for fa in focus_areas:
                        enhanced = f"{term} {fa}"
                        try:
                            nd = await newsapi.search_newsapi(client, news_key, enhanced) if news_key else []
                            term_res.setdefault("enhanced_news", {})[enhanced] = (nd[:5] if nd else [])
                        except Exception as e:
                            term_res.setdefault("enhanced_news", {})[enhanced] = {"error": str(e)}
                    results[term] = term_res
            return json.dumps(results, default=str, indent=2)

        async def intelligent_tech_product_research(query_plan: str) -> str:
            try:
                plan = json.loads(query_plan)
            except Exception:
                plan = {"search_terms": [query_plan]}
            search_terms = plan.get("search_terms", [])[:3]
            results = {}
            async with httpx.AsyncClient(timeout=30) as client:
                gh_key = self.config.get("keys", {}).get("github")
                for term in search_terms:
                    term_res = {}
                    # Simple heuristic for packages
                    if any(t in term.lower() for t in ["react", "vue", "javascript", "frontend"]):
                        pkgs = ["react", "vue", "next"]
                    elif any(t in term.lower() for t in ["ai", "ml", "python", "transformer"]):
                        pkgs = ["transformers", "langchain", "torch"]
                    else:
                        pkgs = ["fastapi", "express", "django"]
                    # fetch npm/pypi info
                    npm_res = {}
                    for p in pkgs[:3]:
                        try:
                            npm_data = await npm_pypi.fetch_npm_package(client, p)
                            npm_res[p] = {
                                "name": npm_data.get("name"),
                                "description": (npm_data.get("description") or "")[:200],
                                "latest": (npm_data.get("dist-tags") or {}).get("latest"),
                                "homepage": npm_data.get("homepage"),
                            }
                        except Exception as e:
                            npm_res[p] = {"error": str(e)}
                    term_res["packages"] = npm_res
                    # GitHub
                    if gh_key:
                        try:
                            orgs = self.config.get("sources", {}).get("github_orgs", ["openai", "vercel"])
                            gh_summary = {}
                            for org in orgs[:3]:
                                try:
                                    repos = await github.fetch_org_repos(client, gh_key, org)
                                    gh_summary[org] = sorted(repos, key=lambda r: r.get("updated_at", ""), reverse=True)[:5] if isinstance(repos, list) else repos
                                except Exception as e:
                                    gh_summary[org] = {"error": str(e)}
                            term_res["github"] = gh_summary
                        except Exception as e:
                            term_res["github"] = {"error": str(e)}
                    results[term] = term_res
            return json.dumps(results, default=str, indent=2)

        async def intelligent_community_research(query_plan: str) -> str:
            try:
                plan = json.loads(query_plan)
            except Exception:
                plan = {"search_terms": [query_plan]}
            search_terms = plan.get("search_terms", [])[:3]
            results = {}
            async with httpx.AsyncClient(timeout=30) as client:
                try:
                    hn_top = await community_sources.fetch_hackernews_stories(client, "topstories", 20)
                    hn_new = await community_sources.fetch_hackernews_stories(client, "newstories", 20)
                except Exception as e:
                    hn_top, hn_new = [], []
                    logger.debug("HN fetch error: %s", e)
                # filter by relevance
                for idx, category in enumerate(["topstories", "newstories"]):
                    items = hn_top if category == "topstories" else hn_new
                    if not items:
                        results[category] = []
                        continue
                    filtered = []
                    for it in items:
                        title = (it.get("title") or "").lower()
                        if any(st.lower() in title for st in search_terms):
                            filtered.append(it)
                    results[category] = filtered[:10] if filtered else items[:5]
                # Reddit (optional)
                reddit_id = self.config.get("keys", {}).get("reddit_client_id")
                reddit_secret = self.config.get("keys", {}).get("reddit_client_secret")
                if reddit_id and reddit_secret:
                    reddit_results = {}
                    subs = ["startups", "entrepreneur"]
                    for sub in subs[:3]:
                        try:
                            posts = await community_sources.fetch_reddit_posts(client, reddit_id, reddit_secret, self.config.get("keys", {}).get("reddit_user_agent", "MarketScoutBot/1.0"), sub, 5)
                            reddit_results[sub] = posts
                        except Exception as e:
                            reddit_results[sub] = {"error": str(e)}
                    results["reddit"] = reddit_results
            return json.dumps(results, default=str, indent=2)

        async def intelligent_financial_research(query_plan: str) -> str:
            try:
                plan = json.loads(query_plan)
            except Exception:
                plan = {"search_terms": [query_plan], "financial_symbols": []}
            symbols = plan.get("financial_symbols", [])
            if not symbols:
                # try to extract from search terms
                for st in plan.get("search_terms", []):
                    symbols.extend(re.findall(r"\b[A-Z]{2,5}\b", st))
            if not symbols:
                if "artificial_intelligence" in plan.get("focus_areas", []):
                    symbols = ["GOOGL", "MSFT", "NVDA"]
                else:
                    symbols = ["AAPL", "MSFT", "GOOGL"]
            results = {}
            async with httpx.AsyncClient(timeout=30) as client:
                av_key = self.config.get("keys", {}).get("alpha_vantage")
                massive_key = self.config.get("keys", {}).get("massive")
                if av_key:
                    avr = {}
                    for s in symbols[:3]:
                        try:
                            ov = await financial_apis.fetch_alpha_vantage_company_overview(client, av_key, s)
                            avr[s] = ov
                        except Exception as e:
                            avr[s] = {"error": str(e)}
                    # news
                    try:
                        news = await financial_apis.fetch_company_news_alpha_vantage(client, av_key, ",".join(symbols[:3]))
                        avr["news"] = news[:5] if isinstance(news, list) else news
                    except Exception as e:
                        avr["news"] = {"error": str(e)}
                    results["alpha_vantage"] = avr
                if massive_key:
                    massive_data = {}
                    try:
                        dividends = await financial_apis.fetch_massive_dividends(client, massive_key, symbols[:3])
                        massive_data["dividends"] = dividends[:5] if isinstance(dividends, list) else dividends
                        market_data = await financial_apis.fetch_massive_market_data(client, massive_key, symbols[:3])
                        massive_data["market_data"] = market_data[:5] if isinstance(market_data, list) else market_data
                    except Exception as e:
                        massive_data["error"] = str(e)
                    results["massive"] = massive_data
            return json.dumps(results, default=str, indent=2)

        async def intelligent_rss_monitoring(query_plan: str) -> str:
            try:
                plan = json.loads(query_plan)
            except Exception:
                plan = {"focus_areas": []}
            focus_areas = plan.get("focus_areas", [])
            all_feeds = self.config.get("sources", {}).get("rss_feeds", [])
            selected = []
            if "artificial_intelligence" in focus_areas:
                selected.extend([f for f in all_feeds if any(x in f for x in ("openai", "google", "ai"))])
            selected.extend([f for f in all_feeds if any(x in f for x in ("github", "techcrunch"))])
            selected = list(dict.fromkeys(selected))[:4]
            if not selected:
                selected = all_feeds[:3]
            results = {}
            for feed in selected:
                try:
                    data = await asyncio.to_thread(rss.fetch_rss_feed, feed, 5)
                    name = feed.split("//")[1].split("/")[0].replace("blog.", "").replace("www.", "")
                    results[name] = data
                except Exception as e:
                    name = feed.split("//")[1].split("/")[0] if "//" in feed else feed
                    results[name] = {"error": str(e)}
            return json.dumps(results, default=str, indent=2)

        # Register tools (LangChain supports async callables in many recent releases)
        tools = [
            Tool(name="intelligent_search_discovery", description="Perform intelligent web search based on query plan", func=intelligent_search_discovery),
            Tool(name="intelligent_news_gathering", description="Gather targeted news based on query plan", func=intelligent_news_gathering),
            Tool(name="intelligent_tech_product_research", description="Tech/product research", func=intelligent_tech_product_research),
            Tool(name="intelligent_community_research", description="Community research (HN, Reddit)", func=intelligent_community_research),
            Tool(name="intelligent_financial_research", description="Financial research based on query plan", func=intelligent_financial_research),
            Tool(name="intelligent_rss_monitoring", description="Monitor RSS feeds", func=intelligent_rss_monitoring),
        ]
        return tools

    # ----------------------
    # Agent creation
    # ----------------------
    def _create_agent(self):
        prompt_template = PromptTemplate(
            input_variables=["tools", "tool_names", "input", "agent_scratchpad"],
            template="""
You are an intelligent market research agent with semantic query planning capabilities.

Available tools:
{tools}

Tool names: {tool_names}

Process:
1) Analyze user's query.
2) Create a JSON execution plan (use primary_sources, search_terms, financial_symbols, focus_areas).
3) Call the matching tools with the JSON plan as input.
4) Aggregate results and produce a structured JSON final answer.

Always follow format:
Thought: ...
Action: [tool_name]
Action Input: [JSON plan]
Observation: [tool output]
...
Final Answer: <single JSON object>

Final Answer schema:
{{
  "query": "original query",
  "plan": {{ ... }},
  "sources": {{ ... }},
  "insights": [ ... ],
  "recommendations": [ ... ],
  "metadata": {{
    "timestamp": "{timestamp}",
    "confidence_score": 0.0,
    "sources_count": 0
  }}
}}
"""
        )
        # create_react_agent returns an agent that will use provided tools
        return create_react_agent(llm=self.llm, tools=self.tools, prompt=prompt_template)

    # ----------------------
    # High-level orchestration
    # ----------------------
    async def comprehensive_intelligence_gathering(self, query: str = "AI startups and product launches") -> Dict[str, Any]:
        logger.info("Starting comprehensive intelligence for: %s", query)
        try:
            plan = await self.query_planner.plan_query(query)
            # ensure original_query present
            plan.setdefault("original_query", query)

            # For stability, call each primary source sequentially and collect results
            sources_output = {}
            for src in plan.get("primary_sources", []):
                tool_name = {
                    "search_discovery": "intelligent_search_discovery",
                    "news_intelligence": "intelligent_news_gathering",
                    "tech_product_intelligence": "intelligent_tech_product_research",
                    "community_intelligence": "intelligent_community_research",
                    "financial_intelligence": "intelligent_financial_research",
                    "rss_intelligence": "intelligent_rss_monitoring",
                }.get(src, src)
                # build JSON plan input
                tool_input = json.dumps(plan)
                # find tool
                tool = next((t for t in self.tools if t.name == tool_name), None)
                if not tool:
                    logger.debug("Tool %s not found; skipping", tool_name)
                    continue
                # call tool (async)
                try:
                    if asyncio.iscoroutinefunction(tool.func):
                        out = await tool.func(tool_input)
                    else:
                        # fallback sync call
                        out = tool.func(tool_input)
                    sources_output[tool_name] = json.loads(out) if isinstance(out, str) else out
                except Exception as e:
                    logger.error("Tool %s failed: %s", tool_name, e)
                    sources_output[tool_name] = {"error": str(e)}

            # optionally upsert some retrieved docs to Pinecone for later semantic recall
            # prepare small set of docs (title+snippet) for embedding/upsert
            docs_to_upsert = []
            for tool_name, payload in sources_output.items():
                # create a few docs from payload
                try:
                    snippet = json.dumps(payload)[:1000]
                    docs_to_upsert.append({"id": f"{tool_name}-{int(datetime.utcnow().timestamp())}", "text": snippet, "metadata": {"tool": tool_name}})
                except Exception:
                    continue
            if docs_to_upsert and self.pine_enabled:
                self.upsert_documents_to_pinecone(docs_to_upsert)

            # ask LLM to synthesize insights
            synth_prompt = f"""
Analyze the collected data and produce:
1) key insights (as a list)
2) top recommendations
3) a short summary (1-2 lines)

Query: {query}

Collected data (abridged):
{json.dumps(sources_output)[:20000]}

Respond JSON only with fields: summary, insights, recommendations, confidence_score
"""
            synth_resp = self.llm.invoke([HumanMessage(content=synth_prompt)])
            synth_text = getattr(synth_resp, "content", str(synth_resp))
            # try to extract JSON
            match = re.search(r"\{.*\}", synth_text, re.DOTALL)
            synth = {}
            if match:
                try:
                    synth = json.loads(match.group())
                except Exception:
                    synth = {"summary": synth_text[:4000], "insights": [], "recommendations": [], "confidence_score": 0.0}
            else:
                synth = {"summary": synth_text[:4000], "insights": [], "recommendations": [], "confidence_score": 0.0}

            final = {
                "query": query,
                "plan": plan,
                "sources": sources_output,
                "insights": synth.get("insights", []),
                "recommendations": synth.get("recommendations", []),
                "summary": synth.get("summary", ""),
                "metadata": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "confidence_score": float(synth.get("confidence_score", 0.0)),
                    "sources_count": len(sources_output),
                },
                "status": "success",
            }

            # save to DB (async)
            try:
                await self.db.init_models()
                await self.db.save_document({
                    "source": "semantic_market_agent",
                    "title": f"Market Intelligence - {query}",
                    "url": f"internal://report/{int(datetime.utcnow().timestamp())}",
                    "content": json.dumps(final, indent=2),
                    "published_at": datetime.utcnow(),
                    "metadata": {"query": query, "status": "success"},
                    "content_hash": str(hash(json.dumps(final, sort_keys=True)))[:64]
                })
            except Exception as e:
                logger.debug("DB save failed: %s", e)

            return final

        except Exception as e:
            logger.exception("comprehensive_intelligence_gathering failed")
            return {"error": str(e), "status": "failed", "timestamp": datetime.utcnow().isoformat()}


# convenience runner
async def run_example():
    agent = SemanticMarketAgent(config_path="config.yaml")
    out = await agent.comprehensive_intelligence_gathering("AI startup funding and product launches")
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(run_example())