import json
import os
import uuid
import yaml
from datetime import datetime
from typing import Any, Dict, Optional

from app.db import Database
from app.simple_semantic_search import SimpleSemanticSearch
from app.pipeline.analyzer import AnalyzerAgent
from app.pipeline.llm_judge import LLMJudge
from app.pipeline.reporting import ReportGenerator


class IntelligenceOrchestrator:
    """Sequential orchestrator: retrieve -> judge -> analyze -> report -> store."""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r") as fh:
            self.config = yaml.safe_load(fh)
        self.db = Database(self.config)
        self.search_engine = SimpleSemanticSearch(config_path=config_path)
        self.reporter = ReportGenerator()

        gkey = os.getenv("GOOGLE_API_KEY", "")
        self.judge = LLMJudge()
        self.analyzer = AnalyzerAgent(gkey)

    async def run(self, query: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        raw = await self.search_engine.comprehensive_search(query)
        judged = await self.judge.judge(query, raw)
        analyzed = await self.analyzer.analyze(judged)

        pdf_local = self.reporter.render_pdf(query, judged, analyzed)
        await self.db.init_models()
        pdf_url = await self.db.upload_pdf_report(pdf_local, bucket="reports")

        report_payload = {
            "summary": analyzed.summary,
            "key_findings": analyzed.key_findings,
            "risks": analyzed.risks,
            "recommendations": analyzed.recommendations,
            "confidence_score": analyzed.confidence_score,
            "sections": analyzed.sections,
        }

        response = {
            "status": "success",
            "query": query,
            "pdf_link": pdf_url,   # keep frontend compatibility
            "report": report_payload,
            "sources_count": len((analyzed.sections.get("source_breakdown", {}) or {}).get("source_counts", {})),
            "documents_count": raw.get("summary", {}).get("total_documents", 0),
        }

        report_id = await self.db.save_analysis_report(
            query=query,
            response=response,
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