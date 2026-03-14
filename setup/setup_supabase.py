#!/usr/bin/env python3
"""
One-time Supabase table + storage setup.
Run: python setup/setup_supabase.py
"""

import asyncio
import sys
import os
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


DDL = """
-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id                BIGSERIAL PRIMARY KEY,
    source            VARCHAR(255) NOT NULL,
    provider          VARCHAR(255),
    title             VARCHAR(1000),
    url               VARCHAR(2000) UNIQUE NOT NULL,
    content           TEXT,
    published_at      TIMESTAMPTZ,
    inserted_at       TIMESTAMPTZ DEFAULT NOW(),
    metadata          JSONB        DEFAULT '{}',
    content_hash      VARCHAR(64),
    sentiment_score   FLOAT,
    relevance_score   FLOAT,
    is_processed      BOOLEAN DEFAULT FALSE,
    processing_status VARCHAR(50)  DEFAULT 'pending',
    company_mentions  JSONB        DEFAULT '[]',
    product_mentions  JSONB        DEFAULT '[]',
    topic_categories  JSONB        DEFAULT '[]'
);

-- Indexes
CREATE INDEX IF NOT EXISTS ix_doc_source   ON documents(source);
CREATE INDEX IF NOT EXISTS ix_doc_pub      ON documents(published_at DESC);
CREATE INDEX IF NOT EXISTS ix_doc_hash     ON documents(content_hash);
CREATE INDEX IF NOT EXISTS ix_doc_proc     ON documents(is_processed, processing_status);

-- Search sessions
CREATE TABLE IF NOT EXISTS search_sessions (
    id           BIGSERIAL PRIMARY KEY,
    query        TEXT NOT NULL,
    query_type   VARCHAR(100),
    status       VARCHAR(50),
    total_docs   INTEGER DEFAULT 0,
    sources_used JSONB DEFAULT '[]',
    insights     JSONB DEFAULT '[]',
    result_file  VARCHAR(500),
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ss_created ON search_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_ss_status  ON search_sessions(status);

-- Analysis reports
CREATE TABLE IF NOT EXISTS analysis_reports (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    query TEXT NOT NULL,
    response_json JSONB NOT NULL,
    pdf_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ar_created ON analysis_reports(created_at DESC);

-- Public storage bucket for generated PDFs
INSERT INTO storage.buckets (id, name, public)
VALUES ('reports', 'reports', true)
ON CONFLICT (id) DO NOTHING;

-- Enable Row Level Security (optional but recommended)
ALTER TABLE documents       ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_reports ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
DROP POLICY IF EXISTS "service_full_access_docs" ON documents;
CREATE POLICY "service_full_access_docs"
    ON documents FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "service_full_access_sessions" ON search_sessions;
CREATE POLICY "service_full_access_sessions"
    ON search_sessions FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "service_full_access_reports" ON analysis_reports;
CREATE POLICY "service_full_access_reports"
    ON analysis_reports FOR ALL USING (true) WITH CHECK (true);
"""


async def setup():
    print("🗄️  Setting up Supabase tables...")

    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)

    db_cfg = cfg.get("database", {})
    conn_url = (db_cfg.get("url", "") or "").replace("postgresql+asyncpg://", "postgresql://")

    if not conn_url:
        print("❌  No database.url in config.yaml")
        sys.exit(1)

    import asyncpg
    try:
        conn = await asyncpg.connect(conn_url, timeout=10)
        # Execute each statement separately to handle "IF NOT EXISTS" cleanly
        for stmt in [s.strip() for s in DDL.split(";") if s.strip()]:
            try:
                await conn.execute(stmt)
            except Exception as e:
                # Ignore "already exists" errors
                if "already exists" not in str(e).lower():
                    print(f"  ⚠️  {e}")
        await conn.close()
        bucket_ok = await asyncpg.connect(conn_url, timeout=10)
        exists = await bucket_ok.fetchval("SELECT EXISTS (SELECT 1 FROM storage.buckets WHERE id = 'reports')")
        await bucket_ok.close()
        print("✅  Tables created / verified in Supabase")
        print(f"✅  Storage bucket 'reports': {'ready' if exists else 'missing'}")
    except Exception as e:
        print(f"❌  Connection failed: {e}")
        print("    Check your database.url in config.yaml")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(setup())