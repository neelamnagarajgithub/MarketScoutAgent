import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Tuple

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from app.pipeline.guardrails import GuardrailEngine
from app.pipeline.types import RetrievedItem, JudgedDataset


class LLMJudge:
    """LLM-based relevance judge with guardrails, dedupe, source diversity balancing."""

    def __init__(self, google_api_key: str = ""):
        self.guardrails = GuardrailEngine()

        key = google_api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=key,
            temperature=0.0,
            max_output_tokens=3500,
        ) if key else None

    def _normalize_string(self, value: Any) -> str:
        return str(value or "").strip()

    def _flatten_raw(self, raw_results: Dict[str, Any]) -> List[RetrievedItem]:
        items: List[RetrievedItem] = []
        raw_data = raw_results.get("raw_data", raw_results)

        for source_type, source_payload in (raw_data or {}).items():
            if not isinstance(source_payload, dict):
                continue
            for source_name, by_query in source_payload.items():
                if not isinstance(by_query, dict):
                    continue
                for query_key, docs in by_query.items():
                    if not isinstance(docs, list):
                        docs = [docs] if docs else []
                    for d in docs:
                        if not isinstance(d, dict):
                            continue

                        title = self._normalize_string(d.get("title", ""))
                        url = self._normalize_string(d.get("url", ""))
                        content = self._normalize_string(d.get("content", ""))

                        # drop skeletal dicts like {"content_hash": "..."}
                        if not (title or url or content):
                            continue

                        items.append(
                            RetrievedItem(
                                source_type=source_type,
                                source=source_name,
                                query_key=str(query_key),
                                title=title,
                                url=url,
                                content=content,
                                published_at=self._normalize_string(
                                    d.get("published_at") or d.get("publishedAt") or ""
                                ) or None,
                                metadata=d.get("metadata", {}) if isinstance(d.get("metadata", {}), dict) else {},
                            )
                        )
        return items

    def _source_weight(self, source: str, source_type: str) -> float:
        weighted_sources = {
            "serpapi": 0.82,
            "newsapi": 0.84,
            "gnews": 0.78,
            "guardian": 0.86,
            "github": 0.90,
            "alpha_vantage": 0.88,
            "massive": 0.88,
            "apollo": 0.72,
            "reddit": 0.58,
            "hackernews": 0.67,
            "mastodon": 0.52,
        }
        base = weighted_sources.get((source or "").lower(), 0.65)
        if source_type == "financial_intelligence":
            base += 0.08
        elif source_type == "business_intelligence":
            base += 0.03
        elif source_type == "community_intelligence":
            base -= 0.05
        return max(0.1, min(1.0, base))

    def _heuristic_score(self, query: str, item: RetrievedItem) -> float:
        q_terms = [w.lower() for w in re.findall(r"[a-zA-Z0-9]{3,}", query)]
        text = f"{item.title} {item.content}".lower()
        hits = sum(1 for t in set(q_terms) if t in text)
        source_bonus = 0.1 if item.source in {"newsapi", "gnews", "serpapi", "alpha_vantage_news", "github"} else 0.0
        recency_bonus = 0.0
        if item.published_at:
            try:
                dt = datetime.fromisoformat(str(item.published_at).replace("Z", "+00:00"))
                age_days = max(0, (datetime.utcnow().timestamp() - dt.timestamp()) / 86400)
                recency_bonus = max(0.0, 0.2 - min(0.2, age_days / 3650))
            except Exception:
                pass
        return min(1.0, (hits / 12.0) + source_bonus + recency_bonus)

    def _heuristic_rank(self, query: str, items: List[RetrievedItem]) -> List[tuple[float, RetrievedItem]]:
        kws = [w.lower() for w in query.split() if len(w) > 2]
        ranked = []
        for it in items:
            text = f"{it.title} {it.content}".lower()
            match_score = sum(1 for k in kws if k in text)
            title_bonus = 0.3 if any(k in (it.title or "").lower() for k in kws) else 0.0
            guardrails_meta = (it.metadata or {}).get("guardrails", {}) if isinstance(it.metadata, dict) else {}
            quality = float(guardrails_meta.get("quality_score", 0.5) or 0.5)
            source_weight = self._source_weight(it.source, it.source_type)
            length_bonus = min(len(it.content or "") / 600.0, 0.2)
            score = (match_score * 0.35) + title_bonus + (quality * 0.9) + (source_weight * 0.8) + length_bonus
            ranked.append((round(score, 4), it))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return ranked

    def _keyword_filter(self, query: str, items: List[RetrievedItem], top_k: int = 180) -> List[RetrievedItem]:
        ranked = self._heuristic_rank(query, items)
        filtered = [it for s, it in ranked if s > 0.7][:top_k]
        return filtered or [it for _, it in ranked[:top_k]]

    def _diversify(self, items: List[RetrievedItem], limit_per_source: int = 25, total_cap: int = 160) -> List[RetrievedItem]:
        counts = Counter()
        diversified: List[RetrievedItem] = []
        for item in items:
            if counts[item.source] >= limit_per_source:
                continue
            diversified.append(item)
            counts[item.source] += 1
            if len(diversified) >= total_cap:
                break
        return diversified

    def _diversity_select(self, scored_items: List[Tuple[float, RetrievedItem]], max_items: int = 220) -> List[RetrievedItem]:
        by_source: Dict[str, List[Tuple[float, RetrievedItem]]] = defaultdict(list)
        for score, item in sorted(scored_items, key=lambda x: x[0], reverse=True):
            by_source[item.source].append((score, item))

        selected: List[RetrievedItem] = []
        while len(selected) < max_items:
            progressed = False
            for source_name in list(by_source.keys()):
                if by_source[source_name]:
                    selected.append(by_source[source_name].pop(0)[1])
                    progressed = True
                    if len(selected) >= max_items:
                        break
            if not progressed:
                break
        return selected

    def _build_prompt(self, query: str, items: List[RetrievedItem]) -> str:
        payload = [
            {
                "i": i,
                "source_type": it.source_type,
                "source": it.source,
                "query_key": it.query_key,
                "title": it.title[:220],
                "url": it.url[:180],
                "content": it.content[:320],
                "published_at": it.published_at,
                "guardrails": (it.metadata or {}).get("guardrails", {}),
            }
            for i, it in enumerate(items)
        ]
        return f"""
You are the LLM-as-Judge stage in a market intelligence pipeline.
Your job is to select the best evidence for downstream analysis.

The downstream analyzer will create a product-team-ready business report.
So your selection must optimize for:
1. direct relevance to the query
2. business usefulness
3. evidence quality
4. diversity across source types
5. low duplication
6. recency when available

Reject items that are:
- generic and not query-relevant
- too thin to support analysis
- duplicate or near-duplicate
- mostly noise, markup, broken snippets, or off-topic

Favor items that:
- contain concrete market, product, business, funding, customer, or competitive signals
- come from stronger sources
- help the analyzer make recommendations for product teams

Return STRICT JSON ONLY with this schema:
{{
  "keep_indices": [0, 1],
  "priority_indices": [0, 1],
  "drop_indices": [2],
  "notes": ["string"],
  "coverage_assessment": "string"
}}

Query: {query}
Items:
{json.dumps(payload, ensure_ascii=False)}
"""

    def _llm_validate(self, query: str, items: List[RetrievedItem]) -> List[int]:
        if not self.llm or not items:
            return list(range(len(items)))

        payload = [
            {
                "i": i,
                "source_type": it.source_type,
                "source": it.source,
                "title": it.title[:220],
                "url": it.url[:220],
                "content": it.content[:350],
            }
            for i, it in enumerate(items[:280])
        ]
        prompt = f"""
You are a strict evidence judge for market intelligence.
Task:
1) Keep only items materially relevant to the query.
2) Prefer factual, source-backed, non-duplicative evidence.
3) Keep source diversity (news, search, financial, community, code when relevant).
4) Reject generic, low-signal, spammy, or off-topic items.

Query:
{query}

Return STRICT JSON only:
{{
  "keep_indices": [int],
  "notes": ["string"],
  "quality_summary": "string"
}}

Items:
{json.dumps(payload, ensure_ascii=False)}
"""
        try:
            resp = self.llm.invoke([HumanMessage(content=prompt)])
            txt = getattr(resp, "content", str(resp))
            s = txt.find("{")
            e = txt.rfind("}") + 1
            obj = json.loads(txt[s:e]) if s >= 0 and e > 0 else {}
            idx = obj.get("keep_indices", [])
            return [int(i) for i in idx if isinstance(i, int) and 0 <= i < len(items)]
        except Exception:
            return list(range(len(items)))

    async def judge(self, query: str, raw_results: Dict[str, Any]) -> JudgedDataset:
        items = self._flatten_raw(raw_results)

        items, dropped, flags = self.guardrails.enforce(items)

        scored = [(self._heuristic_score(query, it), it) for it in items]
        scored = [x for x in scored if x[0] >= 0.08]  # weak relevance cutoff

        diverse = self._diversity_select(scored, max_items=220)
        keep = self._llm_validate(query, diverse)
        judged = [diverse[i] for i in keep] if keep else diverse

        notes = [
            "llm_judge_applied" if self.llm else "heuristic_judge_applied",
            f"input_items={len(items)}",
            f"selected_items={len(judged)}",
            f"source_diversity={len(set(i.source for i in judged)) if judged else 0}",
        ]

        return JudgedDataset(
            query=query,
            items=judged,
            dropped_count=dropped + max(0, len(items) - len(diverse)),
            guardrail_flags=flags,
            judge_notes=notes,
        )