"""
Dynamic Database Layer
Supports: Supabase (primary) → PostgreSQL (asyncpg) → SQLite (fallback)
"""

import asyncio
import asyncpg
import aiosqlite
import logging
import json
import os
import hashlib
import mimetypes
from typing import Dict, List, Any, Optional
from datetime import datetime

# SQLAlchemy for ORM (optional, used by ingest.py)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, Boolean, Index
import sqlalchemy as sa
import datetime as dt

logger = logging.getLogger(__name__)
Base = declarative_base()


# ─────────────────────────── ORM Model ────────────────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    id              = Column(Integer, primary_key=True, index=True)
    source          = Column(String(255), nullable=False, index=True)
    provider        = Column(String(255), index=True)
    title           = Column(String(1000))
    url             = Column(String(2000), unique=True, nullable=False)
    content         = Column(Text)
    published_at    = Column(DateTime, nullable=True, index=True)
    doc_metadata    = Column(JSON, default={})
    content_hash    = Column(String(64), index=True)
    inserted_at     = Column(DateTime, default=dt.datetime.utcnow, index=True)
    sentiment_score = Column(Float, nullable=True)
    relevance_score = Column(Float, nullable=True)
    is_processed    = Column(Boolean, default=False, index=True)
    processing_status = Column(String(50), default="pending", index=True)
    company_mentions  = Column(JSON, default=[])
    product_mentions  = Column(JSON, default=[])
    topic_categories  = Column(JSON, default=[])


Index("ix_documents_source_published",   Document.source,       Document.published_at)
Index("ix_documents_provider_inserted",  Document.provider,     Document.inserted_at)
Index("ix_documents_processing",         Document.is_processed, Document.processing_status)


# ─────────────────────────── DB Backend Enum ──────────────────────────────────
class DBBackend:
    SUPABASE   = "supabase"
    POSTGRESQL = "postgresql"
    SQLITE     = "sqlite"


# ─────────────────────────── Main Database Class ──────────────────────────────
class Database:
    """Dynamic DB layer: Supabase → asyncpg PostgreSQL → SQLite"""

    def __init__(self, config: Dict):
        self.config   = config
        self.pool     = None          # asyncpg pool (postgres / supabase)
        self.backend  = None          # active DBBackend value
        self.sqlite_path = config.get("database", {}).get(
            "sqlite_path", "data/market_intelligence.db"
        )
        # supabase python client (optional)
        self._supa_client = None

    # ── Initialisation ─────────────────────────────────────────────────────────
    async def init_pool(self):
        """Try Supabase → PostgreSQL → SQLite in order."""
        if self.backend:          # already initialised
            return

        db_cfg = self.config.get("database", {})
        provider = db_cfg.get("provider", "supabase").lower()

        if provider == DBBackend.SUPABASE:
            ok = await self._init_supabase(db_cfg)
            if ok:
                return

        # Try direct PostgreSQL via asyncpg
        ok = await self._init_postgres(db_cfg)
        if ok:
            return

        # Final fallback
        await self._init_sqlite()

    async def _init_supabase(self, db_cfg: Dict) -> bool:
        """
        Supabase has two interfaces:
          1. supabase-py client  (REST / Realtime)
          2. Direct asyncpg connection to the Supabase Postgres host
        We try asyncpg first (faster for bulk inserts); fall back to
        supabase-py REST client if the direct connection fails.
        """
        # ── 1. Direct asyncpg → Supabase Postgres ──────────────────────────
        conn_url = db_cfg.get("url", "")
        if conn_url:
            try:
                # Strip SQLAlchemy dialect prefix so asyncpg can parse the URL
                raw_url = conn_url.replace("postgresql+asyncpg://", "postgresql://")
                self.pool = await asyncpg.create_pool(
                    raw_url, min_size=1, max_size=10, timeout=10
                )
                await self._ensure_pg_tables()
                self.backend = DBBackend.SUPABASE
                logger.info("✅ Supabase PostgreSQL (asyncpg) connected")
                return True
            except Exception as e:
                logger.warning("Supabase asyncpg failed: %s", e)

        # ── 2. supabase-py REST client ──────────────────────────────────────
        supa_url = db_cfg.get("supabase_url", "")
        supa_key = db_cfg.get("supabase_service_key") or db_cfg.get("supabase_key", "")
        if supa_url and supa_key:
            try:
                from supabase import create_client, Client  # pip install supabase
                self._supa_client: Client = create_client(supa_url, supa_key)
                # Quick ping
                self._supa_client.table("documents").select("id").limit(1).execute()
                self.backend = DBBackend.SUPABASE
                logger.info("✅ Supabase REST client connected")
                return True
            except ImportError:
                logger.warning("supabase-py not installed; run: pip install supabase")
            except Exception as e:
                logger.warning("Supabase REST client failed: %s", e)

        return False

    async def _init_postgres(self, db_cfg: Dict) -> bool:
        """Direct asyncpg connection to any PostgreSQL instance."""
        conn_url = db_cfg.get("url", "")
        if not conn_url:
            # Try individual fields
            host = db_cfg.get("host")
            port = db_cfg.get("port", 5432)
            dbname = db_cfg.get("database", "marketdb")
            user = db_cfg.get("user", "postgres")
            password = db_cfg.get("password", "")
            if not host:
                return False
            conn_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        else:
            conn_url = conn_url.replace("postgresql+asyncpg://", "postgresql://")

        try:
            self.pool = await asyncpg.create_pool(
                conn_url, min_size=1, max_size=10, timeout=10
            )
            await self._ensure_pg_tables()
            self.backend = DBBackend.POSTGRESQL
            logger.info("✅ PostgreSQL (asyncpg) connected")
            return True
        except Exception as e:
            logger.warning("PostgreSQL failed: %s", e)
            return False

    async def _init_sqlite(self):
        """SQLite fallback – always succeeds."""
        os.makedirs(os.path.dirname(self.sqlite_path) or "data", exist_ok=True)
        async with aiosqlite.connect(self.sqlite_path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS documents (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    source        TEXT    NOT NULL,
                    provider      TEXT,
                    title         TEXT,
                    url           TEXT    UNIQUE,
                    content       TEXT,
                    published_at  TEXT,
                    inserted_at   TEXT    DEFAULT (datetime('now')),
                    metadata      TEXT,
                    content_hash  TEXT    UNIQUE,
                    sentiment_score REAL,
                    relevance_score REAL,
                    is_processed  INTEGER DEFAULT 0,
                    processing_status TEXT DEFAULT 'pending',
                    company_mentions  TEXT DEFAULT '[]',
                    product_mentions  TEXT DEFAULT '[]',
                    topic_categories  TEXT DEFAULT '[]'
                );
                CREATE INDEX IF NOT EXISTS idx_src   ON documents(source);
                CREATE INDEX IF NOT EXISTS idx_pub   ON documents(published_at);
                CREATE INDEX IF NOT EXISTS idx_proc  ON documents(is_processed);
                CREATE TABLE IF NOT EXISTS analysis_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    query TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    pdf_url TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
            """)
            await db.commit()
        self.backend = DBBackend.SQLITE
        logger.info("✅ SQLite fallback initialised at %s", self.sqlite_path)

    async def _ensure_pg_tables(self):
        """Create tables in Postgres/Supabase if they don't exist."""
        ddl = """
        CREATE TABLE IF NOT EXISTS documents (
            id               BIGSERIAL PRIMARY KEY,
            source           VARCHAR(255) NOT NULL,
            provider         VARCHAR(255),
            title            VARCHAR(1000),
            url              VARCHAR(2000) UNIQUE NOT NULL,
            content          TEXT,
            published_at     TIMESTAMPTZ,
            inserted_at      TIMESTAMPTZ DEFAULT NOW(),
            metadata         JSONB DEFAULT '{}',
            content_hash     VARCHAR(64),
            sentiment_score  FLOAT,
            relevance_score  FLOAT,
            is_processed     BOOLEAN DEFAULT FALSE,
            processing_status VARCHAR(50) DEFAULT 'pending',
            company_mentions  JSONB DEFAULT '[]',
            product_mentions  JSONB DEFAULT '[]',
            topic_categories  JSONB DEFAULT '[]'
        );
        CREATE INDEX IF NOT EXISTS ix_doc_source   ON documents(source);
        CREATE INDEX IF NOT EXISTS ix_doc_pub      ON documents(published_at);
        CREATE INDEX IF NOT EXISTS ix_doc_hash     ON documents(content_hash);
        CREATE INDEX IF NOT EXISTS ix_doc_proc     ON documents(is_processed, processing_status);
        CREATE TABLE IF NOT EXISTS analysis_reports (
            id BIGSERIAL PRIMARY KEY,
            user_id VARCHAR(255),
            query TEXT NOT NULL,
            response_json JSONB NOT NULL,
            pdf_url TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_ar_created ON analysis_reports(created_at DESC);
        """
        async with self.pool.acquire() as conn:
            await conn.execute(ddl)

    # ── Public API ─────────────────────────────────────────────────────────────
    async def save_document(self, doc: Dict[str, Any]):
        if not self.backend:
            await self.init_pool()
        try:
            if self.backend == DBBackend.SQLITE:
                await self._save_sqlite(doc)
            elif self._supa_client and not self.pool:
                await self._save_supabase_rest(doc)
            else:
                await self._save_postgres(doc)
        except Exception as e:
            logger.error("save_document failed [%s]: %s", self.backend, e)

    async def get_recent_documents(
        self, source: Optional[str] = None, limit: int = 100
    ) -> List[Dict]:
        if not self.backend:
            await self.init_pool()
        try:
            if self.backend == DBBackend.SQLITE:
                return await self._get_recent_sqlite(source, limit)
            elif self._supa_client and not self.pool:
                return await self._get_recent_supabase_rest(source, limit)
            else:
                return await self._get_recent_postgres(source, limit)
        except Exception as e:
            logger.error("get_recent_documents failed: %s", e)
            return []

    async def init_models(self):
        """Compatibility shim used by ingest.py / agent.py."""
        await self.init_pool()

    # ── SQLite helpers ─────────────────────────────────────────────────────────
    async def _save_sqlite(self, doc: Dict[str, Any]):
        published = doc.get("published_at")
        if isinstance(published, datetime):
            published = published.isoformat()

        async with aiosqlite.connect(self.sqlite_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO documents
                    (source, provider, title, url, content, published_at,
                     metadata, content_hash, sentiment_score, relevance_score,
                     company_mentions, product_mentions, topic_categories)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    doc.get("source"),
                    doc.get("provider"),
                    doc.get("title"),
                    doc.get("url") or f"internal://{hashlib.md5(str(doc).encode()).hexdigest()}",
                    doc.get("content"),
                    published,
                    json.dumps(doc.get("metadata") or doc.get("doc_metadata") or {}),
                    doc.get("content_hash"),
                    doc.get("sentiment_score"),
                    doc.get("relevance_score"),
                    json.dumps(doc.get("company_mentions", [])),
                    json.dumps(doc.get("product_mentions", [])),
                    json.dumps(doc.get("topic_categories", [])),
                ),
            )
            await db.commit()

    async def _get_recent_sqlite(self, source, limit):
        async with aiosqlite.connect(self.sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            if source:
                cur = await db.execute(
                    "SELECT * FROM documents WHERE source=? ORDER BY published_at DESC LIMIT ?",
                    (source, limit),
                )
            else:
                cur = await db.execute(
                    "SELECT * FROM documents ORDER BY published_at DESC LIMIT ?",
                    (limit,),
                )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    # ── PostgreSQL / Supabase asyncpg helpers ──────────────────────────────────
    async def _save_postgres(self, doc: Dict[str, Any]):
        published = doc.get("published_at")
        if isinstance(published, str):
            try:
                published = datetime.fromisoformat(published)
            except Exception:
                published = None

        url = doc.get("url") or f"internal://{hashlib.md5(str(doc).encode()).hexdigest()}"
        content_hash = doc.get("content_hash") or hashlib.sha256(url.encode()).hexdigest()[:64]

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO documents
                    (source, provider, title, url, content, published_at,
                     metadata, content_hash, sentiment_score, relevance_score,
                     company_mentions, product_mentions, topic_categories)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                ON CONFLICT (url) DO UPDATE SET
                    content        = EXCLUDED.content,
                    metadata       = EXCLUDED.metadata,
                    inserted_at    = NOW()
                """,
                doc.get("source"),
                doc.get("provider"),
                doc.get("title"),
                url,
                doc.get("content"),
                published,
                json.dumps(doc.get("metadata") or doc.get("doc_metadata") or {}),
                content_hash,
                doc.get("sentiment_score"),
                doc.get("relevance_score"),
                json.dumps(doc.get("company_mentions", [])),
                json.dumps(doc.get("product_mentions", [])),
                json.dumps(doc.get("topic_categories", [])),
            )

    async def _get_recent_postgres(self, source, limit):
        async with self.pool.acquire() as conn:
            if source:
                rows = await conn.fetch(
                    "SELECT * FROM documents WHERE source=$1 ORDER BY published_at DESC LIMIT $2",
                    source, limit,
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM documents ORDER BY published_at DESC LIMIT $1",
                    limit,
                )
            return [dict(r) for r in rows]

    # ── Supabase REST helpers (supabase-py) ────────────────────────────────────
    async def _save_supabase_rest(self, doc: Dict[str, Any]):
        """Use supabase-py upsert (runs in thread pool to not block event loop)."""
        loop = asyncio.get_event_loop()

        def _upsert():
            published = doc.get("published_at")
            if isinstance(published, datetime):
                published = published.isoformat()

            row = {
                "source":           doc.get("source"),
                "provider":         doc.get("provider"),
                "title":            doc.get("title"),
                "url":              doc.get("url") or f"internal://{hashlib.md5(str(doc).encode()).hexdigest()}",
                "content":          doc.get("content"),
                "published_at":     published,
                "metadata":         doc.get("metadata") or doc.get("doc_metadata") or {},
                "content_hash":     doc.get("content_hash"),
                "sentiment_score":  doc.get("sentiment_score"),
                "relevance_score":  doc.get("relevance_score"),
                "company_mentions": doc.get("company_mentions", []),
                "product_mentions": doc.get("product_mentions", []),
                "topic_categories": doc.get("topic_categories", []),
            }
            self._supa_client.table("documents").upsert(row, on_conflict="url").execute()

        await loop.run_in_executor(None, _upsert)

    async def _get_recent_supabase_rest(self, source, limit):
        loop = asyncio.get_event_loop()

        def _fetch():
            q = self._supa_client.table("documents").select("*").order(
                "published_at", desc=True
            ).limit(limit)
            if source:
                q = q.eq("source", source)
            result = q.execute()
            return result.data or []

        return await loop.run_in_executor(None, _fetch)

    async def upload_pdf_report(self, local_path: str, bucket: str = "reports") -> str:
        """Upload a generated PDF to Supabase Storage if the REST client is available."""
        if not local_path or not os.path.exists(local_path):
            return local_path

        if not self.backend:
            await self.init_pool()

        if not self._supa_client:
            db_cfg = self.config.get("database", {})
            supa_url = db_cfg.get("supabase_url", "")
            supa_key = db_cfg.get("supabase_service_key") or db_cfg.get("supabase_key", "")
            if supa_url and supa_key:
                try:
                    from supabase import create_client
                    self._supa_client = create_client(supa_url, supa_key)
                except Exception as e:
                    logger.warning("Supabase REST client init for storage failed: %s", e)
                    return local_path
            else:
                return local_path

        loop = asyncio.get_event_loop()
        filename = os.path.basename(local_path)
        content_type = mimetypes.guess_type(local_path)[0] or "application/pdf"

        def _upload():
            with open(local_path, "rb") as fh:
                data = fh.read()

            try:
                self._supa_client.storage.from_(bucket).upload(
                    path=filename,
                    file=data,
                    file_options={"content-type": content_type, "upsert": "true"},
                )
            except Exception:
                # If the object already exists or upload returns a non-fatal response, continue to public URL.
                pass

            public_url = self._supa_client.storage.from_(bucket).get_public_url(filename)
            if isinstance(public_url, dict):
                return public_url.get("publicUrl") or public_url.get("public_url") or local_path
            return str(public_url)

        try:
            return await loop.run_in_executor(None, _upload)
        except Exception as e:
            logger.warning("Supabase PDF upload failed: %s", e)
            return local_path

    # ── Status ─────────────────────────────────────────────────────────────────
    def status(self) -> Dict[str, Any]:
        return {
            "backend":      self.backend,
            "pool_active":  self.pool is not None,
            "supa_rest":    self._supa_client is not None,
            "sqlite_path":  self.sqlite_path,
        }