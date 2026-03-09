# app/main.py
import asyncio
from app.ingest import Ingestor
import argparse

async def main():
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
    asyncio.run(main())