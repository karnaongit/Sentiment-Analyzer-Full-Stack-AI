"""Database configuration and SQLAlchemy models for Sentiment Analyzer."""

from datetime import datetime
import os
from pathlib import Path
from typing import Generator
import uuid

from dotenv import load_dotenv
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, create_engine, text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# Load environment variables from project root .env
root_dir = Path(__file__).resolve().parent.parent
load_dotenv(root_dir / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5433/sentiment_db",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Conversation(Base):
    """Stores the conversation-level record and metadata."""

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), default="completed", nullable=False)
    overall_sentiment = Column(String(50), nullable=False)
    summary = Column(Text, nullable=False)
    insights = Column(JSON, nullable=True)

    sentences = relationship(
        "SentenceAnalysis",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="SentenceAnalysis.sentence_order",
    )
    kpis = relationship(
        "ConversationKPI",
        back_populates="conversation",
        uselist=False,
        cascade="all, delete-orphan",
    )


class SentenceAnalysis(Base):
    """Stores sentence-level sentiment classification and confidence."""

    __tablename__ = "sentence_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sentence = Column(Text, nullable=False)
    sentiment = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    sentence_order = Column(Integer, nullable=False)

    conversation = relationship("Conversation", back_populates="sentences")


class ConversationKPI(Base):
    """Stores deterministic conversation-level sentiment metrics."""

    __tablename__ = "conversation_kpis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    total_sentences = Column(Integer, nullable=False)
    positive_count = Column(Integer, nullable=False)
    negative_count = Column(Integer, nullable=False)
    neutral_count = Column(Integer, nullable=False)
    positive_percentage = Column(Float, nullable=False)
    negative_percentage = Column(Float, nullable=False)
    neutral_percentage = Column(Float, nullable=False)
    average_confidence = Column(Float, nullable=False)
    dominant_sentiment = Column(String(50), nullable=False)

    conversation = relationship("Conversation", back_populates="kpis")


def init_db() -> None:
    """Create database tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def check_db_connection() -> bool:
    """Check whether PostgreSQL is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_db() -> Generator:
    """Yield a database session for FastAPI dependencies."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
