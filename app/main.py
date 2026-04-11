# app/main.py
import asyncio
import os
from app.ingest import Ingestor
import argparse
from fastapi import FastAPI, HTTPException
from app.schemas import AnalyzeRequest, AnalyzeResponse
from app.orchestrator import IntelligenceOrchestrator
from app.prompt_safety import QuerySafetyError, assert_safe_query
from app.config_loader import ConfigLoader
from datetime import datetime

app = FastAPI(title="Market Intelligence API")

# Global orchestrator - lazy initialization
orchestrator = None

def get_orchestrator():
    """Get or initialize the orchestrator lazily on first request"""
    global orchestrator
    if orchestrator is None:
        try:
            config = ConfigLoader.load()
            from app.orchestrator import IntelligenceOrchestrator
            orchestrator = IntelligenceOrchestrator(config=config)
            print("✓ Orchestrator initialized successfully")
        except Exception as e:
            print(f"⚠ Warning: Could not initialize orchestrator: {e}")
            print("  Health checks will work, but /analyze will fail until configured")
            return None
    return orchestrator


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run / Render"""
    return {"status": "healthy", "version": "1.0"}


@app.post("/v1/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    try:
        orch = get_orchestrator()
        if orch is None:
            raise HTTPException(
                status_code=503,
                detail="Service not configured. Please check environment variables and configuration."
            )
        
        safe_query = assert_safe_query(req.query)  # prompt safety check before orchestration
        out = await orch.run(safe_query, req.user_id)

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
    
    print("=" * 60)
    print("🚀 Starting Market Intelligence API")
    print(f"   Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"   Port: {os.getenv('PORT', 8080)}")
    print("=" * 60)
    
    # Check if running as API server (default for Cloud Run)
    if os.getenv("RUN_MODE") == "ingestion":
        print("📥 Running in INGESTION mode")
        asyncio.run(run_ingestion())
    else:
        # Start FastAPI server on 0.0.0.0:8080 for Cloud Run
        port = int(os.getenv("PORT", 8080))
        print("🌐 Starting FastAPI server...")
        print(f"   Listening on http://0.0.0.0:{port}")
        print(f"   Health check: http://0.0.0.0:{port}/health")
        uvicorn.run(app, host="0.0.0.0", port=port)