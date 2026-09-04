"""FastAPI service for transcript sentiment analysis with LangGraph & PostgreSQL."""

from contextlib import asynccontextmanager
from typing import Any
import uuid

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from transformers import pipeline

from database import Conversation, check_db_connection, get_db, init_db
from graph import sentiment_graph, set_active_sentiment_pipeline

MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"
sentiment_pipeline: Any | None = None
model_load_error: str | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Load classifier once and initialize database schema on startup."""
    global sentiment_pipeline, model_load_error
    try:
        sentiment_pipeline = pipeline("sentiment-analysis", model=MODEL_NAME)
        set_active_sentiment_pipeline(sentiment_pipeline)
        model_load_error = None
    except Exception as exc:
        sentiment_pipeline = None
        set_active_sentiment_pipeline(None)
        model_load_error = str(exc)

    try:
        init_db()
    except Exception as exc:
        # Keep API running even if database is temporarily starting up
        pass

    yield


app = FastAPI(
    title="Sentiment Analyzer API",
    version="2.0.0",
    description="Agentic sentiment analysis orchestrated with LangGraph and backed by PostgreSQL.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:4173", "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, Any]:
    """Report service health, ML pipeline readiness, and database connection status."""
    return {
        "status": "ok",
        "model_loaded": sentiment_pipeline is not None,
        "database_connected": check_db_connection(),
        "model_error": model_load_error,
    }


@app.post("/analyze")
async def analyze(file: UploadFile | None = File(default=None)) -> dict[str, Any]:
    """Execute LangGraph sentiment workflow and persist results to PostgreSQL."""
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="Please choose a .txt transcript file.")
    if not file.filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported.")

    raw = await file.read()
    if not raw.strip():
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    try:
        transcript = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="The file must be UTF-8 encoded text.") from exc

    if sentiment_pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="The sentiment model is unavailable. Check server connection and restart the API.",
        )

    conv_id = str(uuid.uuid4())
    initial_state = {
        "conversation_id": conv_id,
        "filename": file.filename,
        "raw_text": transcript,
        "sentences": [],
        "sentiment_results": [],
        "kpis": {},
        "summary": "",
        "insights": {},
        "validation_status": "",
        "errors": [],
    }

    try:
        final_state = sentiment_graph.invoke(initial_state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent workflow execution failed: {str(exc)}") from exc

    if final_state.get("validation_status") == "invalid":
        err_msg = "; ".join(final_state.get("errors", ["Validation failed"]))
        raise HTTPException(status_code=422, detail=f"Analysis validation error: {err_msg}")

    kpis = final_state.get("kpis", {})
    sentences = final_state.get("sentiment_results", [])
    summary = final_state.get("summary", "")
    insights = final_state.get("insights", {})

    return {
        "conversation_id": final_state.get("conversation_id", conv_id),
        "filename": file.filename,
        "overall_sentiment": kpis.get("dominant_sentiment", "Neutral"),
        "summary": summary,
        "insights": insights,
        "kpis": kpis,
        "sentences": sentences,
    }


@app.get("/conversations")
def list_conversations(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Return historical conversation analyses stored in PostgreSQL."""
    try:
        conversations = db.query(Conversation).order_by(Conversation.uploaded_at.desc()).all()
        history = []
        for conv in conversations:
            kpi_data = {}
            if conv.kpis:
                kpi_data = {
                    "total_sentences": conv.kpis.total_sentences,
                    "positive": conv.kpis.positive_count,
                    "negative": conv.kpis.negative_count,
                    "neutral": conv.kpis.neutral_count,
                    "positive_percentage": conv.kpis.positive_percentage,
                    "negative_percentage": conv.kpis.negative_percentage,
                    "neutral_percentage": conv.kpis.neutral_percentage,
                    "average_confidence": conv.kpis.average_confidence,
                    "dominant_sentiment": conv.kpis.dominant_sentiment,
                }
            history.append({
                "id": conv.id,
                "filename": conv.filename,
                "uploaded_at": conv.uploaded_at.isoformat() if conv.uploaded_at else "",
                "status": conv.status,
                "overall_sentiment": conv.overall_sentiment,
                "summary": conv.summary,
                "insights": conv.insights,
                "kpis": kpi_data,
            })
        return history
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to retrieve history from PostgreSQL database: {str(exc)}",
        ) from exc


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Retrieve full stored conversation analysis by ID from PostgreSQL."""
    try:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found.")

        kpi_data = {}
        if conv.kpis:
            kpi_data = {
                "total_sentences": conv.kpis.total_sentences,
                "positive": conv.kpis.positive_count,
                "negative": conv.kpis.negative_count,
                "neutral": conv.kpis.neutral_count,
                "positive_percentage": conv.kpis.positive_percentage,
                "negative_percentage": conv.kpis.negative_percentage,
                "neutral_percentage": conv.kpis.neutral_percentage,
                "average_confidence": conv.kpis.average_confidence,
                "dominant_sentiment": conv.kpis.dominant_sentiment,
            }

        sentences_data = [
            {
                "text": row.sentence,
                "sentiment": row.sentiment,
                "confidence": row.confidence,
            }
            for row in conv.sentences
        ]

        return {
            "conversation_id": conv.id,
            "filename": conv.filename,
            "uploaded_at": conv.uploaded_at.isoformat() if conv.uploaded_at else "",
            "status": conv.status,
            "overall_sentiment": conv.overall_sentiment,
            "summary": conv.summary,
            "insights": conv.insights,
            "kpis": kpi_data,
            "sentences": sentences_data,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to query conversation from PostgreSQL database: {str(exc)}",
        ) from exc
