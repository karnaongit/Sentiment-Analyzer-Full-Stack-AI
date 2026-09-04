"""LangGraph agentic orchestrator for Sentiment Analyzer.

Workflow:
  START
    ↓
  Transcript Processing (transcript_node)
    ↓
  Sentiment Analysis (sentiment_node)
    ↓
  KPI Calculation (kpi_node)
    ↓
  [Conditional Routing: Is Negative Dominant / High Friction?]
   ├── YES → Negative Insights (negative_insight_node)
   └── NO  → Standard Insights (standard_insight_node)
    ↓
  Validation (validation_node)
    ↓
  [Conditional Routing: Is Validation Valid?]
   ├── YES → Persistence (persistence_node) → END
   └── NO  → END (Validation Failed)
"""

from datetime import datetime
import re
from statistics import mean
from typing import Any, Optional, TypedDict
import uuid

from langgraph.graph import END, START, StateGraph

from database import Conversation, ConversationKPI, SentenceAnalysis, SessionLocal

NEUTRAL_THRESHOLD = 0.72

# Global reference for the preloaded sentiment pipeline
_active_sentiment_pipeline: Any | None = None


def set_active_sentiment_pipeline(pipeline: Any | None) -> None:
    """Set the globally loaded Hugging Face pipeline instance."""
    global _active_sentiment_pipeline
    _active_sentiment_pipeline = pipeline


class AgentState(TypedDict):
    """Shared state dictionary passed across LangGraph nodes."""

    conversation_id: str
    filename: str
    raw_text: str
    sentences: list[str]
    sentiment_results: list[dict[str, Any]]
    kpis: dict[str, Any]
    summary: str
    insights: dict[str, Any]
    validation_status: str  # "valid" or "invalid"
    errors: list[str]


def normalise_sentiment(label: str, confidence: float) -> str:
    """Map model-specific labels to Positive, Negative, or Neutral."""
    value = label.upper()
    if "NEUTRAL" in value:
        return "Neutral"
    if confidence < NEUTRAL_THRESHOLD:
        return "Neutral"
    if "POS" in value or value in {"LABEL_2", "5 STARS", "4 STARS"}:
        return "Positive"
    if "NEG" in value or value in {"LABEL_0", "1 STAR", "2 STARS"}:
        return "Negative"
    return "Neutral"


# --- NODES ---


def transcript_node(state: AgentState) -> dict[str, Any]:
    """Split transcript text into clean, non-empty sentences."""
    raw_text = state.get("raw_text", "")
    normalised = re.sub(r"\s+", " ", raw_text).strip()
    sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+|\n+", normalised) if item.strip()]

    errors = list(state.get("errors", []))
    if not sentences:
        errors.append("No readable sentences were found in the transcript.")

    return {
        "sentences": sentences,
        "errors": errors,
    }


def sentiment_node(state: AgentState) -> dict[str, Any]:
    """Perform sentence-level inference using the preloaded transformer pipeline."""
    sentences = state.get("sentences", [])
    errors = list(state.get("errors", []))

    if not sentences or errors:
        return {"sentiment_results": []}

    pipeline = _active_sentiment_pipeline
    if pipeline is None:
        errors.append("Sentiment model pipeline is not initialized.")
        return {"sentiment_results": [], "errors": errors}

    try:
        predictions = pipeline(sentences, truncation=True, max_length=512)
    except Exception as exc:
        errors.append(f"Model inference failed: {str(exc)}")
        return {"sentiment_results": [], "errors": errors}

    results = []
    for sentence, pred in zip(sentences, predictions):
        confidence = round(float(pred["score"]), 4)
        results.append({
            "text": sentence,
            "sentiment": normalise_sentiment(pred["label"], confidence),
            "confidence": confidence,
        })

    return {"sentiment_results": results, "errors": errors}


def kpi_node(state: AgentState) -> dict[str, Any]:
    """Compute deterministic numeric KPIs from sentence-level classifications."""
    results = state.get("sentiment_results", [])
    if not results:
        return {"kpis": {}}

    counts = {
        label: sum(row["sentiment"] == label for row in results)
        for label in ("Positive", "Negative", "Neutral")
    }
    total = len(results)
    dominant = max(counts, key=counts.get)
    percentages = {label: round(count / total * 100, 1) for label, count in counts.items()}
    average_confidence = round(mean(row["confidence"] for row in results), 4)

    kpis = {
        "total_sentences": total,
        "positive": counts["Positive"],
        "negative": counts["Negative"],
        "neutral": counts["Neutral"],
        "positive_percentage": percentages["Positive"],
        "negative_percentage": percentages["Negative"],
        "neutral_percentage": percentages["Neutral"],
        "average_confidence": average_confidence,
        "dominant_sentiment": dominant,
    }
    return {"kpis": kpis}


def negative_insight_node(state: AgentState) -> dict[str, Any]:
    """Agentic node triggered when the conversation exhibits elevated negative sentiment.

    Focuses analysis on identifying customer friction points, complaints, and churn risk.
    """
    sentences = state.get("sentences", [])
    sentiment_results = state.get("sentiment_results", [])

    negative_moments = [
        item["text"] for item in sentiment_results if item["sentiment"] == "Negative"
    ]

    # Extractive summary weighted towards negative issues and resolution attempts
    keywords = ("problem", "issue", "frustrating", "broken", "disappointed", "refund", "outage", "error")
    scored = []
    for index, sentence in enumerate(sentences):
        lower = sentence.lower()
        is_neg = index < len(sentiment_results) and sentiment_results[index]["sentiment"] == "Negative"
        score = sum(keyword in lower for keyword in keywords) * 4 + (sentiment_results[index]["confidence"] if is_neg else 0)
        scored.append((score, index, sentence))

    selected = sorted(sorted(scored, reverse=True)[:3], key=lambda x: x[1])
    summary = " ".join(item[2] for item in selected) if selected else " ".join(sentences[:3])

    # Check for closing resolution or customer acknowledgment
    closing_text = " ".join(sentences[-3:]).lower()
    has_resolution = any(w in closing_text for w in ("thank", "appreciate", "fixed", "resolved", "sorted"))

    insights = {
        "analysis_type": "Elevated Friction / Negative Dominant",
        "overall_tone": "Customer reported critical service issues or dissatisfaction.",
        "friction_points": negative_moments[:4] if negative_moments else ["General dissatisfaction detected."],
        "churn_risk": "Moderate to High" if not has_resolution else "Mitigated via customer-service intervention",
        "recommended_action": "Review support ticket notes and monitor customer satisfaction follow-up.",
        "resolution_signal": "Issue appeared acknowledged or resolved by closing." if has_resolution else "No clear closing confirmation observed.",
    }

    return {"summary": summary, "insights": insights}


def standard_insight_node(state: AgentState) -> dict[str, Any]:
    """Agentic node triggered for normal or positive customer conversations.

    Focuses on standard flow, positive milestones, and constructive interactions.
    """
    sentences = state.get("sentences", [])
    sentiment_results = state.get("sentiment_results", [])
    kpis = state.get("kpis", {})

    positive_moments = [
        item["text"] for item in sentiment_results if item["sentiment"] == "Positive"
    ]

    keywords = ("happy", "great", "thank", "help", "resolved", "appreciate", "excellent", "glad")
    scored = []
    for index, sentence in enumerate(sentences):
        lower = sentence.lower()
        score = sum(keyword in lower for keyword in keywords) * 3 + min(len(sentence) / 120, 1)
        scored.append((score, index, sentence))

    selected = sorted(sorted(scored, reverse=True)[:3], key=lambda x: x[1])
    summary = " ".join(item[2] for item in selected) if selected else " ".join(sentences[:3])

    dominant = kpis.get("dominant_sentiment", "Neutral")
    insights = {
        "analysis_type": "Standard / Constructive Interaction",
        "overall_tone": f"Balanced interaction with {dominant.lower()} leaning sentiment.",
        "key_positives": positive_moments[:3] if positive_moments else ["Polite and standard customer inquiries."],
        "churn_risk": "Low",
        "recommended_action": "Standard quality assurance logging; positive customer relationship.",
        "resolution_signal": "Customer indicated satisfaction or standard communication completed.",
    }

    return {"summary": summary, "insights": insights}


def validation_node(state: AgentState) -> dict[str, Any]:
    """Validate all derived results and mathematical consistency before persistence."""
    errors = list(state.get("errors", []))
    results = state.get("sentiment_results", [])
    kpis = state.get("kpis", {})
    sentences = state.get("sentences", [])

    if not sentences:
        errors.append("Transcript contains no sentences.")
    if len(sentences) != len(results):
        errors.append(f"Sentence count mismatch: {len(sentences)} parsed vs {len(results)} analyzed.")

    total = kpis.get("total_sentences", 0)
    pos = kpis.get("positive", 0)
    neg = kpis.get("negative", 0)
    neu = kpis.get("neutral", 0)

    if pos + neg + neu != total:
        errors.append(f"Sentiment sum mismatch: {pos} + {neg} + {neu} != {total}.")

    avg_conf = kpis.get("average_confidence", 0.0)
    if not (0.0 <= avg_conf <= 1.0):
        errors.append(f"Average confidence {avg_conf} out of bounds [0.0, 1.0].")

    validation_status = "valid" if not errors else "invalid"
    return {"validation_status": validation_status, "errors": errors}


def persistence_node(state: AgentState) -> dict[str, Any]:
    """Persist the complete conversation analysis, sentences, and KPIs into PostgreSQL."""
    errors = list(state.get("errors", []))
    conv_id = state.get("conversation_id") or str(uuid.uuid4())
    filename = state.get("filename", "conversation.txt")
    raw_text = state.get("raw_text", "")
    kpis = state.get("kpis", {})
    results = state.get("sentiment_results", [])
    summary = state.get("summary", "")
    insights = state.get("insights", {})

    try:
        db = SessionLocal()
        try:
            # Create conversation record
            conversation = Conversation(
                id=conv_id,
                filename=filename,
                raw_text=raw_text,
                uploaded_at=datetime.utcnow(),
                status="completed",
                overall_sentiment=kpis.get("dominant_sentiment", "Neutral"),
                summary=summary,
                insights=insights,
            )
            db.add(conversation)

            # Create sentence analysis records
            for order, row in enumerate(results):
                sentence_record = SentenceAnalysis(
                    conversation_id=conv_id,
                    sentence=row["text"],
                    sentiment=row["sentiment"],
                    confidence=row["confidence"],
                    sentence_order=order,
                )
                db.add(sentence_record)

            # Create KPI record
            kpi_record = ConversationKPI(
                conversation_id=conv_id,
                total_sentences=kpis.get("total_sentences", 0),
                positive_count=kpis.get("positive", 0),
                negative_count=kpis.get("negative", 0),
                neutral_count=kpis.get("neutral", 0),
                positive_percentage=kpis.get("positive_percentage", 0.0),
                negative_percentage=kpis.get("negative_percentage", 0.0),
                neutral_percentage=kpis.get("neutral_percentage", 0.0),
                average_confidence=kpis.get("average_confidence", 0.0),
                dominant_sentiment=kpis.get("dominant_sentiment", "Neutral"),
            )
            db.add(kpi_record)

            db.commit()
        except Exception as exc:
            db.rollback()
            errors.append(f"Database persistence failed: {str(exc)}")
        finally:
            db.close()
    except Exception as exc:
        errors.append(f"Database connection failed: {str(exc)}")

    return {"conversation_id": conv_id, "errors": errors}


# --- CONDITIONAL ROUTERS ---


def route_insight_path(state: AgentState) -> str:
    """Conditional router based on whether negative friction dominates."""
    kpis = state.get("kpis", {})
    dominant = kpis.get("dominant_sentiment", "Neutral")
    neg_pct = kpis.get("negative_percentage", 0.0)

    # Meaningful branch: high friction triggers deep negative customer insight generation
    if dominant == "Negative" or neg_pct >= 35.0:
        return "negative_insight_node"
    return "standard_insight_node"


def route_persistence(state: AgentState) -> str:
    """Conditional router: only persist if validation passed."""
    if state.get("validation_status") == "valid":
        return "persistence_node"
    return END


# --- COMPOSE WORKFLOW ---


def create_sentiment_graph():
    """Build and compile the LangGraph workflow."""
    workflow = StateGraph(AgentState)

    workflow.add_node("transcript_node", transcript_node)
    workflow.add_node("sentiment_node", sentiment_node)
    workflow.add_node("kpi_node", kpi_node)
    workflow.add_node("negative_insight_node", negative_insight_node)
    workflow.add_node("standard_insight_node", standard_insight_node)
    workflow.add_node("validation_node", validation_node)
    workflow.add_node("persistence_node", persistence_node)

    # Edge from START to transcript processing
    workflow.add_edge(START, "transcript_node")
    workflow.add_edge("transcript_node", "sentiment_node")
    workflow.add_edge("sentiment_node", "kpi_node")

    # Conditional branching based on sentiment analysis
    workflow.add_conditional_edges(
        "kpi_node",
        route_insight_path,
        {
            "negative_insight_node": "negative_insight_node",
            "standard_insight_node": "standard_insight_node",
        },
    )

    # Both insight paths converge to validation
    workflow.add_edge("negative_insight_node", "validation_node")
    workflow.add_edge("standard_insight_node", "validation_node")

    # Conditional persistence based on validation status
    workflow.add_conditional_edges(
        "validation_node",
        route_persistence,
        {
            "persistence_node": "persistence_node",
            END: END,
        },
    )

    workflow.add_edge("persistence_node", END)

    return workflow.compile()


sentiment_graph = create_sentiment_graph()
