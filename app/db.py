# app/db.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Index, Float, Boolean
import datetime
import sqlalchemy as sa
import uuid

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
    def __init__(self, config):
        self.engine = create_async_engine(
            config['database']['url'], 
            future=True, 
            echo=False,
            pool_size=20,
            max_overflow=30
        )
        self.async_session = sessionmaker(
            self.engine, 
            expire_on_commit=False, 
            class_=AsyncSession
        )

    async def init_models(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def save_document(self, doc: dict):
        async with self.async_session() as session:
            try:
                # Enhanced deduplication by url and content_hash
                url = doc.get('url')
                content_hash = doc.get('content_hash')
                
                if not url:
                    return None
                
                # Check for existing document
                q = sa.select(Document).where(
                    sa.or_(
                        Document.url == url,
                        sa.and_(
                            Document.content_hash == content_hash,
                            Document.content_hash != '',
                            Document.content_hash.isnot(None)
                        )
                    )
                )
                res = await session.execute(q)
                existing = res.scalar_one_or_none()
                
                if existing:
                    # Update if we have newer information
                    if doc.get('published_at') and existing.published_at:
                        if doc['published_at'] > existing.published_at:
                            for key, value in doc.items():
                                if hasattr(existing, key) and value is not None:
                                    setattr(existing, key, value)
                            await session.commit()
                    return existing
                
                # Create new document
                new_doc = Document(
                    source=doc.get("source"),
                    provider=doc.get("doc_metadata", {}).get("provider"),
                    title=doc.get("title"),
                    url=url,
                    content=doc.get("content"),
                    published_at=doc.get("published_at"),
                    doc_metadata=doc.get("doc_metadata", {}),
                    content_hash=content_hash,
                    sentiment_score=doc.get("doc_metadata", {}).get("sentiment_score"),
                    relevance_score=doc.get("doc_metadata", {}).get("relevance_score"),
                    company_mentions=doc.get("doc_metadata", {}).get("company_mentions", []),
                    product_mentions=doc.get("doc_metadata", {}).get("product_mentions", []),
                    topic_categories=doc.get("doc_metadata", {}).get("topic_categories", [])
                )
                
                session.add(new_doc)
                await session.commit()
                await session.refresh(new_doc)
                return new_doc
                
            except Exception as e:
                await session.rollback()
                print(f"Database error: {e}")
                return None

    async def get_recent_documents(self, hours: int = 24, limit: int = 100):
        """Get recent documents for analysis"""
        async with self.async_session() as session:
            cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
            q = sa.select(Document).where(
                Document.inserted_at >= cutoff
            ).order_by(Document.published_at.desc()).limit(limit)
            
            res = await session.execute(q)
            return res.scalars().all()

    async def get_documents_by_source(self, source: str, limit: int = 50):
        """Get documents from specific source"""
        async with self.async_session() as session:
            q = sa.select(Document).where(
                Document.source == source
            ).order_by(Document.inserted_at.desc()).limit(limit)
            
            res = await session.execute(q)
            return res.scalars().all()