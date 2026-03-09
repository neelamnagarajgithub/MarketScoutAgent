# app/db.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Index, Float, Boolean
import datetime
import sqlalchemy as sa
import uuid
import asyncio
import asyncpg
import logging
from typing import Dict, List, Any, Optional
import json
import hashlib

logger = logging.getLogger(__name__)

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(255), nullable=False, index=True)   # e.g., github, newsapi, serpapi, rss
    provider = Column(String(255), index=True)  # specific API provider
    title = Column(String(1000))
    url = Column(String(2000), unique=True, nullable=False)
    content = Column(Text)
    published_at = Column(DateTime, nullable=True, index=True)
    doc_metadata = Column(JSON, default={})  # Renamed to avoid SQLAlchemy reserved keyword
    content_hash = Column(String(64), index=True)
    inserted_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    
    # Additional fields for better analytics
    sentiment_score = Column(Float, nullable=True)
    relevance_score = Column(Float, nullable=True)
    is_processed = Column(Boolean, default=False, index=True)
    processing_status = Column(String(50), default='pending', index=True)
    
    # Company/product identification
    company_mentions = Column(JSON, default=[])  # List of mentioned companies
    product_mentions = Column(JSON, default=[])  # List of mentioned products
    topic_categories = Column(JSON, default=[])  # AI, SaaS, etc.

# Create compound indexes for better query performance
Index("ix_documents_source_published", Document.source, Document.published_at)
Index("ix_documents_provider_inserted", Document.provider, Document.inserted_at)
Index("ix_documents_processing", Document.is_processed, Document.processing_status)

class Database:
    def __init__(self, config: Dict):
        self.config = config
        self.pool = None
        
    async def init_pool(self):
        """Initialize connection pool with better error handling"""
        if self.pool:
            return
            
        try:
            # Get database config with defaults
            db_config = self.config.get('database', {})
            
            # Use SQLite as fallback if PostgreSQL fails
            if not db_config or not all(k in db_config for k in ['host', 'port', 'database', 'user', 'password']):
                logger.warning("PostgreSQL config incomplete, using SQLite fallback")
                await self.init_sqlite_fallback()
                return
                
            # Try PostgreSQL connection
            try:
                self.pool = await asyncpg.create_pool(
                    host=db_config['host'],
                    port=db_config['port'],
                    database=db_config['database'],
                    user=db_config['user'],
                    password=db_config['password'],
                    min_size=1,
                    max_size=10,
                    timeout=5
                )
                logger.info("✅ PostgreSQL connection established")
                
            except Exception as e:
                logger.warning(f"PostgreSQL connection failed: {e}, using SQLite fallback")
                await self.init_sqlite_fallback()
                
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            await self.init_sqlite_fallback()
    
    async def init_sqlite_fallback(self):
        """Initialize SQLite as fallback database"""
        import aiosqlite
        import os
        
        try:
            os.makedirs('data', exist_ok=True)
            self.sqlite_db = 'data/market_intelligence.db'
            
            # Create tables
            async with aiosqlite.connect(self.sqlite_db) as db:
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source TEXT NOT NULL,
                        title TEXT,
                        url TEXT UNIQUE,
                        content TEXT,
                        published_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT,
                        content_hash TEXT UNIQUE
                    )
                ''')
                
                await db.execute('''
                    CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source);
                ''')
                
                await db.execute('''
                    CREATE INDEX IF NOT EXISTS idx_documents_published_at ON documents(published_at);
                ''')
                
                await db.commit()
            
            self.use_sqlite = True
            logger.info("✅ SQLite fallback database initialized")
            
        except Exception as e:
            logger.error(f"SQLite fallback failed: {e}")
            self.use_sqlite = False

    async def save_document(self, doc: Dict[str, Any]):
        """Save document with fallback handling"""
        try:
            if hasattr(self, 'use_sqlite') and self.use_sqlite:
                await self.save_document_sqlite(doc)
            else:
                await self.save_document_postgres(doc)
        except Exception as e:
            logger.error(f"Failed to save document: {e}")
    
    async def save_document_sqlite(self, doc: Dict[str, Any]):
        """Save document to SQLite"""
        import aiosqlite
        
        try:
            async with aiosqlite.connect(self.sqlite_db) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO documents 
                    (source, title, url, content, published_at, metadata, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    doc.get('source'),
                    doc.get('title'),
                    doc.get('url'),
                    doc.get('content'),
                    doc.get('published_at'),
                    json.dumps(doc.get('metadata', {})),
                    doc.get('content_hash')
                ))
                await db.commit()
                
        except Exception as e:
            logger.error(f"SQLite save failed: {e}")
    
    async def save_document_postgres(self, doc: Dict[str, Any]):
        """Save document to PostgreSQL"""
        if not self.pool:
            await self.init_pool()
            
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO documents 
                    (source, title, url, content, published_at, metadata, content_hash)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (content_hash) DO UPDATE SET
                    updated_at = CURRENT_TIMESTAMP
                ''', 
                doc.get('source'),
                doc.get('title'), 
                doc.get('url'),
                doc.get('content'),
                doc.get('published_at'),
                json.dumps(doc.get('metadata', {})),
                doc.get('content_hash')
                )
        except Exception as e:
            logger.error(f"PostgreSQL save failed: {e}")

    async def get_recent_documents(self, source: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get recent documents with fallback"""
        try:
            if hasattr(self, 'use_sqlite') and self.use_sqlite:
                return await self.get_recent_documents_sqlite(source, limit)
            else:
                return await self.get_recent_documents_postgres(source, limit)
        except Exception as e:
            logger.error(f"Failed to get documents: {e}")
            return []
    
    async def get_recent_documents_sqlite(self, source: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get recent documents from SQLite"""
        import aiosqlite
        
        try:
            async with aiosqlite.connect(self.sqlite_db) as db:
                if source:
                    cursor = await db.execute('''
                        SELECT * FROM documents 
                        WHERE source = ? 
                        ORDER BY published_at DESC 
                        LIMIT ?
                    ''', (source, limit))
                else:
                    cursor = await db.execute('''
                        SELECT * FROM documents 
                        ORDER BY published_at DESC 
                        LIMIT ?
                    ''', (limit,))
                
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                return [dict(zip(columns, row)) for row in rows]
                
        except Exception as e:
            logger.error(f"SQLite query failed: {e}")
            return []

    async def init_models(self):
        """Initialize database models (compatibility method)"""
        await self.init_pool()