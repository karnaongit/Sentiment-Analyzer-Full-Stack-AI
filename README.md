# Sentiment Analyzer

An Agentic AI full-stack application for customer-service conversation analysis. Upload a UTF-8 `.txt` transcript, execute an orchestrated **LangGraph** workflow with a pretrained Hugging Face RoBERTa model, calculate deterministic KPIs, extract friction insights, persist results to **PostgreSQL**, and review live insights and historical analyses in a modern **React** dashboard.

## Features

- **Agentic Workflow**: Multi-node orchestration powered by LangGraph with conditional insight routing based on conversation friction.
- **Durable PostgreSQL Persistence**: Complete storage of transcripts, sentence classifications, numeric KPIs, and AI insights.
- **Hugging Face Sentiment AI**: Sentence-level sentiment classification using `cardiffnlp/twitter-roberta-base-sentiment-latest` with confidence thresholding.
- **Deterministic Analytics**: Mathematically verified KPI calculations (positive, negative, neutral counts, percentages, and average confidence).
- **Interactive History**: View and load past analyses directly from PostgreSQL in the React dashboard.
- **One-Command Startup**: Root `npm run dev` concurrently launches both backend and frontend.

## Architecture

```text
React Frontend (Vite, Port 5173)
        │
        ▼  multipart/form-data POST /analyze
FastAPI Backend (Port 8000)
        │
        ▼
LangGraph Orchestrator
┌─────────────────────────────────────────────────────────────┐
│ 1. transcript_node       -> Split transcript into sentences │
│ 2. sentiment_node        -> Batch RoBERTa inference         │
│ 3. kpi_node              -> Deterministic KPI derivation    │
│ 4. Conditional Insight Router                               │
│    ├── High Friction     -> negative_insight_node           │
│    └── Standard Flow     -> standard_insight_node           │
│ 5. validation_node       -> Integrity & math verification   │
│ 6. persistence_node      -> Commit records to PostgreSQL    │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
PostgreSQL 16 Database (Port 5433)
        │
        ▼
FastAPI JSON Response -> React Dashboard
```

## PostgreSQL Persistence

PostgreSQL is the permanent source of truth:
- **`conversations`**: Stores conversation UUID, filename, uploaded timestamp, overall sentiment, summary, and structured insights JSON.
- **`sentence_analysis`**: Stores sentence text, sentiment label, confidence score, and sentence order with cascade deletion.
- **`conversation_kpis`**: Stores total sentence count, counts per sentiment, percentages, average confidence, and dominant sentiment.

## Project Structure

```text
Sentiment_Analyzer/
├── backend/
│   ├── database.py             # SQLAlchemy models and connection handling
│   ├── graph.py                # LangGraph StateGraph, nodes, and routing
│   ├── main.py                 # FastAPI service and endpoints
│   └── requirements.txt        # Python backend dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # React dashboard and history view
│   │   └── styles.css          # Design system and styling
│   └── package.json            # Frontend Vite dependencies
├── docker-compose.yml          # PostgreSQL 16 Alpine configuration
├── .env                        # Active environment configuration
├── .env.example                # Example environment template
├── package.json                # Unified process launcher (concurrently)
├── sample_conversation.txt     # Sample transcript
├── PROJECT_CONTEXT.md          # Technical documentation
└── AGENTS.md                   # AI agent operating instructions
```

## Quick Start

### 1. Database Setup

Start PostgreSQL via Docker Compose:

```bash
docker compose up -d
```

### 2. Install & Start Application

From the project root:

```bash
npm install
npm run dev
```

This concurrently starts:
- **FastAPI Backend**: `http://localhost:8000`
- **React Frontend**: `http://localhost:5173`
- **Interactive API Docs**: `http://localhost:8000/docs`

### Demo Login
- **Username**: `admin`
- **Password**: `admin123`

### Stopping the Application
Press `Ctrl+C` in the terminal to stop both the backend and frontend child processes together.

To stop the database container:
```bash
docker compose down
```

---

## Manual Startup (Fallback)

If you prefer running services in separate terminals:

**Terminal 1 — Backend**:
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend**:
```powershell
cd frontend
npm install
npm run dev
```

---

## Environment Variables

Configured in `.env`:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=sentiment_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/sentiment_db
```

---

## API Endpoints

### `GET /health`
Returns system health, transformer model status, and PostgreSQL connectivity:
```json
{
  "status": "ok",
  "model_loaded": true,
  "database_connected": true,
  "model_error": null
}
```

### `POST /analyze`
Uploads a `.txt` customer conversation, executes the LangGraph agentic workflow, persists results to PostgreSQL, and returns the analysis.

```bash
curl.exe -X POST -F "file=@sample_conversation.txt" http://localhost:8000/analyze
```

### `GET /conversations`
Retrieves past conversation analyses stored in PostgreSQL.

### `GET /conversations/{id}`
Retrieves the complete stored conversation analysis by UUID.

---

## Example Input

[`sample_conversation.txt`](sample_conversation.txt) demonstrates a customer service conversation about a temporary network outage:

```text
Agent: Hello, thank you for calling BrightTel support. How can I help today?
Customer: Hi, my internet has been dropping since yesterday evening and it has been really frustrating.
Agent: I am sorry you have had that experience. I can check the connection for you.
...
```

---

## Expected Output

```json
{
  "conversation_id": "9ea4c576-e17c-4db6-8df2-b0a61729dc07",
  "filename": "sample_conversation.txt",
  "overall_sentiment": "Neutral",
  "summary": "Agent: Hello, thank you for calling BrightTel support. Customer: Thank you, I appreciate that. Customer: Excellent service, thank you for sorting this out.",
  "insights": {
    "analysis_type": "Standard / Constructive Interaction",
    "overall_tone": "Balanced interaction with neutral leaning sentiment.",
    "key_positives": [
      "Customer: Thank you, I appreciate that.",
      "Customer: That is useful to know."
    ],
    "churn_risk": "Low",
    "recommended_action": "Standard quality assurance logging; positive customer relationship.",
    "resolution_signal": "Customer indicated satisfaction or standard communication completed."
  },
  "kpis": {
    "total_sentences": 16,
    "positive": 4,
    "negative": 3,
    "neutral": 9,
    "positive_percentage": 25.0,
    "negative_percentage": 18.8,
    "neutral_percentage": 56.2,
    "average_confidence": 0.8131,
    "dominant_sentiment": "Neutral"
  },
  "sentences": [
    {
      "text": "Customer: Thank you, I appreciate that.",
      "sentiment": "Positive",
      "confidence": 0.9559
    }
  ]
}
```

---

## Analysis History

The React frontend includes a built-in **History** view. Users can click any past conversation record to reload and review its KPIs, charts, and sentence analysis from PostgreSQL without re-uploading the file.

---

## Limitations

- **Authentication**: Frontend demo gate; no server-side JWT or cookie session issuance.
- **Single-request Batch Processing**: Transcripts are processed synchronously during the request.
- **Model Confidence**: Confidence thresholding maps polar predictions below 0.72 to Neutral.
# Sentiment-Analyzer-Full-Stack-AI 
