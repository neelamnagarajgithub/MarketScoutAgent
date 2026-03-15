import json
import os
import uuid
import yaml
import tempfile
from datetime import datetime
from typing import Any, Dict, Optional
import logging

from app.db import Database
from app.simple_semantic_search import SimpleSemanticSearch
from app.pipeline.analyzer import AnalyzerAgent
from app.pipeline.llm_judge import LLMJudge
from app.pipeline.reporting import ReportGenerator

logger = logging.getLogger(__name__)


class IntelligenceOrchestrator:
    """Sequential orchestrator: retrieve -> judge -> analyze -> report -> store."""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r") as fh:
            self.config = yaml.safe_load(fh)
        self.db = Database(self.config)
        self.search_engine = SimpleSemanticSearch(config_path=config_path)
        self.reporter = ReportGenerator()

        keys = self.config.get("keys", {}) if isinstance(self.config, dict) else {}
        gkey = (
            os.getenv("GOOGLE_API_KEY", "")
            or os.getenv("GEMINI_API_KEY", "")
            or str(keys.get("GOOGLE_API_KEY", "") or "").strip()
            or str(keys.get("google_api_key", "") or "").strip()
            or str(keys.get("gemini_api_key", "") or "").strip()
            or str(keys.get("google_genai_api_key", "") or "").strip()
        )
        if not gkey:
            logger.warning("No Gemini/Google API key configured; analyzer and judge will run in heuristic/fallback mode")

        self.judge = LLMJudge(gkey)
        self.analyzer = AnalyzerAgent(gkey)

    async def run(self, query: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        raw = await self.search_engine.comprehensive_search(query)
        judged = await self.judge.judge(query, raw)
        analyzed = await self.analyzer.analyze(judged)

        pdf_url = None
        with tempfile.TemporaryDirectory(prefix="scoutai_report_") as temp_dir:
            pdf_local = self.reporter.render_pdf(query, judged, analyzed, out_dir=temp_dir)
            await self.db.init_models()
            uploaded = await self.db.upload_pdf_report(pdf_local, bucket="reports")
            # Local PDF fallback is intentionally disabled once Supabase storage is active.
            if uploaded and uploaded != pdf_local:
                pdf_url = uploaded

        report_payload = {
            "summary": analyzed.summary,
            "key_findings": analyzed.key_findings,
            "risks": analyzed.risks,
            "recommendations": analyzed.recommendations,
            "confidence_score": analyzed.confidence_score,
            "sections": analyzed.sections,
        }

        guardrail_summary = analyzed.sections.get("guardrail_summary", {}) if isinstance(analyzed.sections, dict) else {}
        judge_notes = guardrail_summary.get("judge_notes", []) if isinstance(guardrail_summary, dict) else []
        fallback_note = next((n for n in judge_notes if isinstance(n, str) and n.startswith("analyzer_fallback_reason=")), None)
        analysis_mode = "fallback" if fallback_note else "llm"

        response = {
            "status": "success",
            "query": query,
            "pdf_link": pdf_url,   # keep frontend compatibility
            "report": report_payload,
            "analysis_mode": analysis_mode,
            "fallback_reason": fallback_note,
            "sources_count": len((analyzed.sections.get("source_breakdown", {}) or {}).get("source_counts", {})),
            "documents_count": raw.get("summary", {}).get("total_documents", 0),
        }

        report_id = await self.db.save_analysis_report(
            query=query,
            report_payload=response,
            pdf_url=pdf_url,
            user_id=user_id,
        )
        response["report_id"] = report_id

        return {
            "query": query,
            "status": "success",
            "response": response,
            "pdf_url": pdf_url,
            "report_id": report_id,
            "timestamp": datetime.utcnow().isoformat(),
        }