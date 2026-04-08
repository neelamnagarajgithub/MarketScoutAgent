# app/main.py
import asyncio
import os
from app.ingest import Ingestor
import argparse
from fastapi import FastAPI, HTTPException
from app.schemas import AnalyzeRequest, AnalyzeResponse
from app.orchestrator import IntelligenceOrchestrator
from app.prompt_safety import QuerySafetyError, assert_safe_query
from datetime import datetime

app = FastAPI(title="Market Intelligence API")
orchestrator = IntelligenceOrchestrator(config_path="config.yaml")


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    return {"status": "healthy"}


@app.post("/v1/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    try:
        safe_query = assert_safe_query(req.query)  # prompt safety check before orchestration
        out = await orchestrator.run(safe_query, req.user_id)

        # Normalize response envelope for schema safety
        normalized = {
            "query": out.get("query", req.query),
            "status": out.get("status", "success"),
            "response": out.get("response", out if isinstance(out, dict) else {}),
            "pdf_url": out.get("pdf_url"),
            "report_id": out.get("report_id"),
            "timestamp": out.get("timestamp", datetime.utcnow().isoformat()),
        }
        return AnalyzeResponse(**normalized)
    except QuerySafetyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def run_ingestion():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run ingestion once and exit")
    parser.add_argument("--interval", type=int, default=3600, help="Seconds between runs")
    args = parser.parse_args()

    ing = Ingestor()
    if args.once:
        await ing.init()
        await ing.run_once()
    else:
        await ing.run_periodic(interval_seconds=args.interval)

if __name__ == "__main__":
    import os
    import uvicorn
    
    # Check if running as API server (default for Cloud Run)
    if os.getenv("RUN_MODE") == "ingestion":
        asyncio.run(run_ingestion())
    else:
        # Start FastAPI server on 0.0.0.0:8080 for Cloud Run
        port = int(os.getenv("PORT", 8080))
        uvicorn.run(app, host="0.0.0.0", port=port)