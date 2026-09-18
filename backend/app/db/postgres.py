"""
Postgres + pgvector setup.

Tables:
  vendors        - structured vendor attributes used by the ML gate
  policy_chunks   - chunks of internal risk policy docs + embeddings
  vendor_chunks    - chunks of a vendor's uploaded docs + embeddings
  findings         - agent output: a risk finding grounded in a policy_chunk
                     and a vendor_chunk, with a verification flag

We use raw pgvector via SQLAlchemy's Vector type. Run this module directly to
create tables against DATABASE_URL (a stand-in for an Alembic migration, kept
simple on purpose for a portfolio project).
"""
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    create_engine,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    industry = Column(String(100), nullable=False)
    geography = Column(String(100), nullable=False)
    past_incidents = Column(Integer, default=0)
    contract_value_usd = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # cached outputs of the two-layer scoring pipeline
    ml_prior_risk_prob = Column(Float, nullable=True)
    final_risk_score = Column(Float, nullable=True)
    final_risk_tier = Column(String(20), nullable=True)  # low / medium / high

    findings = relationship("Finding", back_populates="vendor")


class PolicyChunk(Base):
    __tablename__ = "policy_chunks"

    id = Column(Integer, primary_key=True)
    policy_name = Column(String(255), nullable=False)
    section_label = Column(String(255), nullable=True)  # e.g. "Section 4.2 - Data Retention"
    text = Column(Text, nullable=False)
    embedding = Column(Vector(settings.embedding_dim))
    mongo_doc_id = Column(String(64), nullable=True)


class VendorChunk(Base):
    __tablename__ = "vendor_chunks"

    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    doc_name = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)
    embedding = Column(Vector(settings.embedding_dim))
    mongo_doc_id = Column(String(64), nullable=True)


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    vendor_chunk_id = Column(Integer, ForeignKey("vendor_chunks.id"), nullable=True)
    policy_chunk_id = Column(Integer, ForeignKey("policy_chunks.id"), nullable=True)

    severity = Column(String(20), nullable=False)  # low / medium / high
    summary = Column(Text, nullable=False)
    vendor_quote = Column(Text, nullable=True)      # short excerpt cited from vendor doc
    policy_quote = Column(Text, nullable=True)       # short excerpt cited from policy
    grounded = Column(Boolean, default=False)         # did the verification pass confirm this?
    created_at = Column(DateTime, default=datetime.utcnow)

    vendor = relationship("Vendor", back_populates="findings")


def init_db() -> None:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return SessionLocal()


if __name__ == "__main__":
    init_db()
    print("pgvector extension enabled and tables created.")
