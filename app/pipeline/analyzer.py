import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Tuple

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.pipeline.types import AnalysisReport, JudgedDataset, RetrievedItem


class AnalyzerAgent:
    """Detailed strategic analyzer with stats + structured narrative."""

    def __init__(self, google_api_key: str | None = None):
        key = google_api_key or os.getenv("GOOGLE_API_KEY")
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=key,
            temperature=0.2,
            max_output_tokens=7000,
        ) if key else None
        self.stop = {
            "the", "and", "for", "with", "this", "that", "from", "into", "their", "about",
            "have", "will", "market", "analysis", "including", "risks", "recommendations"
        }

    def _infer_query_lens(self, query: str) -> Dict[str, str]:
        query_lower = (query or "").lower()
        if any(k in query_lower for k in ["competitor", "competition", "landscape", "vs", "compare"]):
            return {
                "report_type": "competitive_intelligence",
                "primary_lens": "competitive_landscape",
                "product_focus": "differentiate against rival offerings and GTM moves",
            }
        if any(k in query_lower for k in ["funding", "investment", "capital", "round"]):
            return {
                "report_type": "funding_intelligence",
                "primary_lens": "financial_and_capital_signals",
                "product_focus": "align roadmap with investor and growth signals",
            }
        if any(k in query_lower for k in ["launch", "product", "feature", "release"]):
            return {
                "report_type": "product_intelligence",
                "primary_lens": "product_and_launch_signals",
                "product_focus": "prioritize features based on market evidence",
            }
        return {
            "report_type": "market_intelligence",
            "primary_lens": "market_and_strategy",
            "product_focus": "convert market signals into product and GTM actions",
        }

    def _tokenize(self, text: str) -> List[str]:
        return [
            token for token in re.findall(r"[A-Za-z][A-Za-z0-9_\-/]+", (text or "").lower())
            if len(token) > 3 and token not in {
                "this", "that", "with", "from", "have", "will", "into", "their", "about",
                "startup", "trends", "latest", "query", "report", "analysis", "market",
            }
        ]

    def _source_breakdown(self, items: List[RetrievedItem]) -> Dict[str, Any]:
        by_source = Counter(i.source for i in items)
        by_type = Counter(i.source_type for i in items)
        return {
            "total_items": len(items),
            "source_counts": dict(by_source.most_common()),
            "source_type_counts": dict(by_type.most_common()),
            "top_sources": [name for name, _ in by_source.most_common(5)],
        }

    def _theme_breakdown(self, items: List[RetrievedItem]) -> Dict[str, Any]:
        terms = Counter()
        for item in items:
            terms.update(self._tokenize(item.title))
            terms.update(self._tokenize(item.content[:500]))
        top_terms = [term for term, _ in terms.most_common(15)]
        return {
            "dominant_terms": top_terms,
            "term_frequencies": dict(terms.most_common(20)),
        }

    def _timeline_breakdown(self, items: List[RetrievedItem]) -> Dict[str, Any]:
        monthly = defaultdict(int)
        unknown = 0
        for item in items:
            if not item.published_at:
                unknown += 1
                continue
            try:
                dt = datetime.fromisoformat(str(item.published_at).replace("Z", "+00:00"))
                monthly[dt.strftime("%Y-%m")] += 1
            except Exception:
                unknown += 1
        ordered = dict(sorted(monthly.items()))
        return {
            "monthly_distribution": ordered,
            "undated_items": unknown,
            "latest_period": next(reversed(ordered.keys()), None) if ordered else None,
        }

    def _evidence_samples(self, items: List[RetrievedItem], limit: int = 12) -> List[Dict[str, Any]]:
        samples = []
        for item in items[:limit]:
            samples.append({
                "source_type": item.source_type,
                "source": item.source,
                "query_key": item.query_key,
                "title": item.title[:220],
                "url": item.url,
                "content": item.content[:500],
                "published_at": item.published_at,
            })
        return samples

    def _build_dataset_context(self, ds: JudgedDataset) -> Dict[str, Any]:
        lens = self._infer_query_lens(ds.query)
        return {
            "query": ds.query,
            "report_type": lens["report_type"],
            "primary_lens": lens["primary_lens"],
            "product_focus": lens["product_focus"],
            "item_count": len(ds.items),
            "guardrail_flags": ds.guardrail_flags,
            "judge_notes": ds.judge_notes,
            "source_breakdown": self._source_breakdown(ds.items),
            "theme_breakdown": self._theme_breakdown(ds.items),
            "timeline_breakdown": self._timeline_breakdown(ds.items),
            "evidence_samples": self._evidence_samples(ds.items),
        }

    def _coerce_list(self, value: Any, fallback: List[str]) -> List[str]:
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()][:12] or fallback
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return fallback

    def _normalize_sections(self, sections: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(sections, dict):
            sections = {}

        def _as_list(v, fallback):
            if isinstance(v, list) and v:
                return [str(x) for x in v]
            return fallback

        base = {
            "executive_overview": sections.get("executive_overview") or context["query"],
            "business_context": sections.get("business_context") or "Insufficient structured business context generated.",
            "market_landscape": sections.get("market_landscape") or "Insufficient structured market-landscape output from model.",
            "customer_and_user_signals": _as_list(sections.get("customer_and_user_signals"), []),
            "competitive_landscape": _as_list(sections.get("competitive_landscape"), []),
            "product_implications": _as_list(sections.get("product_implications"), []),
            "feature_recommendations": _as_list(sections.get("feature_recommendations"), []),
            "go_to_market_implications": _as_list(sections.get("go_to_market_implications"), []),
            "strategic_implications": _as_list(sections.get("strategic_implications"), []),
            "opportunities": _as_list(sections.get("opportunities"), []),
            "risks_and_constraints": _as_list(sections.get("risks_and_constraints"), []),
            "decision_ready_next_steps": _as_list(sections.get("decision_ready_next_steps"), []),
            "evidence_highlights": sections.get("evidence_highlights") or context["evidence_samples"][:10],
            "source_breakdown": sections.get("source_breakdown") or context["source_breakdown"],
            "theme_breakdown": sections.get("theme_breakdown") or context["theme_breakdown"],
            "timeline_breakdown": sections.get("timeline_breakdown") or context["timeline_breakdown"],
            "guardrail_summary": sections.get("guardrail_summary") or {
                "flags": context["guardrail_flags"],
                "judge_notes": context["judge_notes"],
            },
        }

        # enforce minimum density for key list sections
        for k in [
            "customer_and_user_signals", "competitive_landscape", "product_implications",
            "feature_recommendations", "go_to_market_implications", "strategic_implications",
            "opportunities", "risks_and_constraints", "decision_ready_next_steps",
        ]:
            if len(base[k]) < 6:
                base[k].extend([
                    "Expand this area with additional evidence-backed detail.",
                    "Tie this point to measurable business or product impact.",
                    "Clarify assumptions and validation path.",
                ])
        return base

    def _fallback(self, ds: JudgedDataset) -> AnalysisReport:
        context = self._build_dataset_context(ds)
        top_sources = context["source_breakdown"]["top_sources"]
        dominant_terms = context["theme_breakdown"]["dominant_terms"][:6]
        evidence_count = len(ds.items)
        diversity = len(context["source_breakdown"]["source_counts"])
        confidence = min(0.92, 0.35 + (min(evidence_count, 120) / 200) + (min(diversity, 8) / 20)) if evidence_count else 0.2

        return AnalysisReport(
            summary=(
                f"The analyzer reviewed {evidence_count} validated items for '{ds.query}'. "
                f"Coverage is strongest across {', '.join(top_sources[:3]) if top_sources else 'available sources'}, "
                f"with dominant discussion around {', '.join(dominant_terms[:4]) if dominant_terms else 'general market signals'}."
            ),
            key_findings=[
                f"Evidence spans {diversity} distinct sources." if diversity else "Evidence diversity is limited.",
                f"Most represented sources: {', '.join(top_sources[:5])}" if top_sources else "No dominant source distribution detected.",
                f"Dominant themes: {', '.join(dominant_terms[:6])}" if dominant_terms else "Theme extraction was limited.",
                f"Guardrail notes: {', '.join(ds.guardrail_flags)}" if ds.guardrail_flags else "No guardrail violations remained after filtering.",
            ],
            risks=[
                "Some retrieved evidence may reflect reporting lag or secondary-source amplification.",
                "Coverage quality depends on query specificity and source availability.",
                "Competitive conclusions should be validated against primary company disclosures.",
            ],
            recommendations=[
                "Validate the top claims against primary filings, product announcements, or official company statements.",
                "Track the same query over time to identify momentum shifts and narrative changes.",
                "Use the evidence highlights to build a deeper company-by-company comparison.",
            ],
            confidence_score=round(confidence, 2),
            sections={
                "executive_overview": f"Fallback analysis generated for query '{ds.query}'.",
                "business_context": (
                    f"This report is oriented toward product-team decision making and uses {evidence_count} validated external signals to summarize the business environment."
                ),
                "market_landscape": (
                    f"The available dataset suggests the discussion is concentrated around {', '.join(dominant_terms[:6]) or 'broad market topics'}."
                ),
                "customer_and_user_signals": [
                    "Repeated topics across community and news sources indicate where user attention is concentrated.",
                    "Source overlap can be used as a proxy for signal strength, though it does not prove demand magnitude.",
                ],
                "competitive_landscape": [item.title for item in ds.items[:8]],
                "product_implications": [
                    "Translate repeated external themes into product bets, messaging updates, and monitoring dashboards.",
                    "Use evidence clusters to decide whether roadmap investment should target differentiation, parity, or speed of execution.",
                ],
                "feature_recommendations": [
                    "Prioritize features that reduce friction in the most visible high-interest workflows.",
                    "Bundle instrumentation around new launches so the team can validate whether market signals convert into usage.",
                ],
                "go_to_market_implications": [
                    "Align product messaging with the strongest external themes appearing across trusted sources.",
                    "Prepare enablement material for sales or growth teams around the dominant market narrative.",
                ],
                "strategic_implications": [
                    "High-frequency themes indicate where the market narrative is concentrating.",
                    "Source diversity can be used as a proxy for breadth of market confirmation.",
                ],
                "opportunities": [
                    "Expand evidence collection with more direct company and investor sources.",
                    "Convert repeated themes into monitoring dashboards and alerts.",
                ],
                "risks_and_constraints": [
                    "Not all sources have equal reliability or recency.",
                    "Some evidence may be duplicated semantically even after URL/content dedupe.",
                ],
                "decision_ready_next_steps": [
                    "Turn the top opportunities into a product review with owners, timing, and expected impact.",
                    "Validate critical assumptions with direct customer interviews or product analytics before committing roadmap changes.",
                    "Re-run the same analysis periodically to detect whether signals are strengthening or fading.",
                ],
                "evidence_highlights": context["evidence_samples"],
                "source_breakdown": context["source_breakdown"],
                "theme_breakdown": context["theme_breakdown"],
                "timeline_breakdown": context["timeline_breakdown"],
                "guardrail_summary": {
                    "flags": ds.guardrail_flags,
                    "judge_notes": ds.judge_notes,
                    "dropped_count": ds.dropped_count,
                },
            },
        )

    def _build_prompt(self, context: Dict[str, Any]) -> str:
        return f"""
You are a principal-level market intelligence strategist producing a decision-grade report.
Return STRICT JSON only.

Objectives:
- Highly detailed, evidence-backed analysis for product + strategy + GTM leadership.
- Convert external signals into actionable, prioritized decisions.
- Separate facts from assumptions.
- Explicitly state uncertainty and blind spots.

Depth requirements (mandatory):
- summary: 1 dense paragraph (120-220 words).
- key_findings: 8-14 bullets.
- risks: 6-10 bullets.
- recommendations: 8-12 bullets (action-oriented, ownership-ready).
- sections must be deeply elaborated:
  - executive_overview: 180-300 words
  - business_context: 180-300 words
  - market_landscape: 220-380 words
  - customer_and_user_signals: 8-14 bullets
  - competitive_landscape: 8-14 bullets
  - product_implications: 8-14 bullets
  - feature_recommendations: 10-16 bullets
  - go_to_market_implications: 8-14 bullets
  - strategic_implications: 8-14 bullets
  - opportunities: 8-14 bullets
  - risks_and_constraints: 8-14 bullets
  - decision_ready_next_steps: 10-16 bullets with priority hints (now/next/later)
  - evidence_highlights: 10-16 items, each with "title", "source", "why_it_matters"

Confidence scoring:
- 0.85-1.0 only for broad, recent, cross-source consistency.
- 0.60-0.84 for useful but incomplete evidence.
- <0.60 for sparse/conflicting evidence.

Required schema:
{{
  "summary": "string",
  "key_findings": ["string"],
  "risks": ["string"],
  "recommendations": ["string"],
  "confidence_score": 0.0,
  "sections": {{
    "executive_overview": "string",
    "business_context": "string",
    "market_landscape": "string",
    "customer_and_user_signals": ["string"],
    "competitive_landscape": ["string"],
    "product_implications": ["string"],
    "feature_recommendations": ["string"],
    "go_to_market_implications": ["string"],
    "strategic_implications": ["string"],
    "opportunities": ["string"],
    "risks_and_constraints": ["string"],
    "decision_ready_next_steps": ["string"],
    "evidence_highlights": [{{"title":"string","source":"string","why_it_matters":"string"}}],
    "source_breakdown": {{}},
    "theme_breakdown": {{}},
    "timeline_breakdown": {{}},
    "guardrail_summary": {{}}
  }}
}}

Context:
{json.dumps(context, ensure_ascii=False)}
"""

    def _parse_llm_output(self, text: str) -> Dict[str, Any]:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start < 0 or end <= 0:
            raise ValueError("No JSON object found in LLM output")
        return json.loads(text[start:end])

    async def analyze(self, ds: JudgedDataset) -> AnalysisReport:
        if not ds.items or not self.llm:
            return self._fallback(ds)

        context = self._build_dataset_context(ds)
        prompt = self._build_prompt(context)

        try:
            resp = self.llm.invoke([HumanMessage(content=prompt)])
            txt = getattr(resp, "content", str(resp))
            obj = self._parse_llm_output(txt)
            sections = self._normalize_sections(obj.get("sections", {}), context)
            return AnalysisReport(
                summary=str(obj.get("summary", "") or self._fallback(ds).summary),
                key_findings=self._coerce_list(obj.get("key_findings"), self._fallback(ds).key_findings),
                risks=self._coerce_list(obj.get("risks"), self._fallback(ds).risks),
                recommendations=self._coerce_list(obj.get("recommendations"), self._fallback(ds).recommendations),
                confidence_score=max(0.0, min(1.0, float(obj.get("confidence_score", 0.0) or 0.0))),
                sections=sections,
            )
        except Exception:
            return self._fallback(ds)