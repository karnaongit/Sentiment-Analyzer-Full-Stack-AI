# Project Context

## 1. Project Overview
The Sentiment Analyzer is a full-stack, Agentic AI application that analyzes customer-service conversation transcripts. Users upload a UTF-8 `.txt` file containing a conversation. The workflow is orchestrated by **LangGraph**, which splits transcripts into sentences, executes a preloaded Hugging Face RoBERTa transformer pipeline, deterministically derives KPIs, executes conditional insight routing, validates mathematical and structural consistency, and persists all data to a **PostgreSQL** database via **SQLAlchemy**. A **React (Vite)** dashboard visualizes the sentiment mix, KPIs, agent insights, sentence classifications, and historical analyses.

## 2. Business / Assignment Goal
To transform raw customer-service conversations into actionable intelligence by pairing automated sentiment classification with agentic workflow orchestration (LangGraph), deep customer-friction analysis, and durable storage (PostgreSQL).

## 3. Tech Stack
- **Frontend**: React 19, Vite, Recharts (SVG data visualization), Axios, Custom Vanilla CSS.
- **Backend**: FastAPI, Uvicorn, SQLAlchemy 2.0, Psycopg2-binary, Python-dotenv.
- **Agent Orchestrator**: LangGraph (StateGraph, conditional routing, state persistence).
- **AI / ML**: Hugging Face `transformers` pipeline, PyTorch (`cardiffnlp/twitter-roberta-base-sentiment-latest`).
- **Database**: PostgreSQL 16 (running via Docker Compose on port 5433).

## 4. Repository Structure
```text
Sentiment_Analyzer/
├── backend/
│   ├── database.py             # SQLAlchemy models, connection pool, and init
│   ├── graph.py                # LangGraph StateGraph, nodes, and conditional edges
│   ├── main.py                 # FastAPI service and API routes
│   └── requirements.txt        # Python backend dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # React components (Login, Upload, Dashboard, History)
│   │   ├── main.jsx            # React root mount
│   │   └── styles.css          # Design system, layout, and responsive styles
│   └── package.json            # Frontend dependencies and Vite configuration
├── docker-compose.yml          # PostgreSQL 16 Alpine container configuration
├── .env                        # Active environment configuration
├── .env.example                # Template for database credentials
├── package.json                # Root package for concurrently multi-process runner
├── sample_conversation.txt     # Standard customer service transcript for testing
├── run.bat                     # Legacy Windows batch launcher
├── PROJECT_CONTEXT.md          # Single source of truth documentation
├── AGENTS.md                   # Agent operating guidelines
└── README.md                   # User setup and quick start documentation
```

## 5. End-to-End Architecture
```text
User
  ↓
React Frontend (Vite, Port 5173)
  ↓ [multipart/form-data POST /analyze]
FastAPI Backend (Uvicorn, Port 8000)
  ↓
LangGraph Orchestrator
┌─────────────────────────────────────────────────────────────┐
│ 1. Transcript Processing Node (sentence extraction)         │
│ 2. Sentiment Analysis Node (sentence-level inference)       │
│ 3. KPI Calculation Node (deterministic metrics derivation)  │
│ 4. Conditional Insight Router (friction threshold check)    │
│    ├── Elevated Friction / Negative -> negative_insight_node│
│    └── Normal / Positive Flow      -> standard_insight_node│
│ 5. Validation Node (integrity & math consistency checks)   │
│    ├── Invalid -> Abort persistence & return 422 error      │
│    └── Valid   -> persistence_node                          │
│ 6. Persistence Node (commit to PostgreSQL)                  │
└─────────────────────────────────────────────────────────────┘
  ↓
PostgreSQL 16 (Port 5433)
  ↓
FastAPI JSON Response
  ↓
React Dashboard / Analysis History
```

## 6. LangGraph Workflow & Agentic Routing

### Graph State (`AgentState`)
Passed across all nodes during workflow execution:
- `conversation_id`: str (UUID)
- `filename`: str
- `raw_text`: str
- `sentences`: list[str]
- `sentiment_results`: list[dict[str, Any]] (`text`, `sentiment`, `confidence`)
- `kpis`: dict[str, Any] (counts, percentages, average confidence, dominant sentiment)
- `summary`: str (extractive conversation summary)
- `insights`: dict[str, Any] (friction analysis, risk score, recommended action)
- `validation_status`: str (`"valid"` | `"invalid"`)
- `errors`: list[str]

### Nodes
1. **`transcript_node`**: Normalizes whitespace and splits raw transcript text into sentence analysis units via regex `(?<=[.!?])\s+|\n+`.
2. **`sentiment_node`**: Executes sentence-by-sentence batch inference on the preloaded transformer pipeline. Normalizes labels to Positive, Negative, or Neutral with a `0.72` confidence threshold.
3. **`kpi_node`**: Computes deterministic numbers: total sentences, positive/negative/neutral counts, percentages, average confidence, and dominant sentiment.
4. **`negative_insight_node`**: Triggered on high-friction conversations. Focuses extractive weighting on customer complaints, outage reports, and billing grievances. Generates churn risk and escalation recommendations.
5. **`standard_insight_node`**: Triggered on constructive or normal conversations. Focuses extractive weighting on polite milestones and resolution indicators.
6. **`validation_node`**: Enforces strict mathematical rules before committing to the database:
   - `len(sentences) == len(sentiment_results)`
   - `positive + negative + neutral == total_sentences`
   - `0.0 <= average_confidence <= 1.0`
7. **`persistence_node`**: Persists records into PostgreSQL across `conversations`, `sentence_analysis`, and `conversation_kpis`.

### Conditional Edge Routing
- **Insight Branching (`route_insight_path`)**:
  - If `dominant_sentiment == "Negative"` OR `negative_percentage >= 35.0`: branches to `negative_insight_node`.
  - Otherwise: branches to `standard_insight_node`.
- **Persistence Gate (`route_persistence`)**:
  - If `validation_status == "valid"`: transitions to `persistence_node`.
  - If `validation_status == "invalid"`: immediately terminates to `END` without modifying the database.

## 7. AI / ML Architecture
- **Pretrained Model**: `cardiffnlp/twitter-roberta-base-sentiment-latest`
- **Engine**: Hugging Face `transformers.pipeline("sentiment-analysis")` with PyTorch.
- **Lifecycle**: Loaded once during FastAPI application `lifespan` startup.
- **Classification Thresholding**: A threshold of `0.72` is enforced. Any polar prediction below `0.72` confidence is mapped to `Neutral`.
- **Insights & Summary**: Structured insights and extractive summaries are produced deterministically without requiring external API tokens, ensuring resilience and zero ongoing API costs.

## 8. PostgreSQL Schema & Data Storage

All data is persistently stored in PostgreSQL (database: `sentiment_db`):

| Data Type | Target Table | Columns |
| :--- | :--- | :--- |
| **Transcript** | `conversations` | `raw_text`, `filename`, `uploaded_at`, `status` |
| **Overall Sentiment** | `conversations` | `overall_sentiment` |
| **Summary & Insights** | `conversations` | `summary` (Text), `insights` (JSON) |
| **Sentence Classifications** | `sentence_analysis` | `conversation_id` (FK), `sentence`, `sentiment`, `confidence`, `sentence_order` |
| **Calculated KPIs** | `conversation_kpis` | `conversation_id` (FK), `total_sentences`, `positive_count`, `negative_count`, `neutral_count`, `positive_percentage`, `negative_percentage`, `neutral_percentage`, `average_confidence`, `dominant_sentiment` |

Foreign keys enforce cascade deletion (`ondelete="CASCADE"`).

## 9. API Documentation

### `GET /health`
Returns service and component readiness.
- **Response**: `{"status": "ok", "model_loaded": true, "database_connected": true, "model_error": null}`

### `POST /analyze`
Upload a customer service `.txt` transcript file for agentic processing and database storage.
- **Request**: `multipart/form-data` with field `file` (`.txt`, UTF-8).
- **Response**: Full analysis payload containing `conversation_id`, `filename`, `overall_sentiment`, `summary`, `insights`, `kpis`, and `sentences`.
- **Errors**: HTTP 400 (empty/invalid file), HTTP 422 (validation failed), HTTP 503 (model/database unavailable).

### `GET /conversations`
Retrieves past analyses stored in PostgreSQL, sorted by most recent first.
- **Response**: List of summary objects including `id`, `filename`, `uploaded_at`, `status`, `overall_sentiment`, `kpis`.

### `GET /conversations/{id}`
Retrieves complete stored conversation details matching the `/analyze` format.
- **Response**: Full conversation object with sentence breakdown and KPIs.
- **Errors**: HTTP 404 (conversation not found), HTTP 503 (database error).

## 10. Frontend Architecture
- **`App`**: Manages view routing (`upload`, `history`, `dashboard`) and navigation bar.
- **`Login`**: Demo gate using `admin` / `admin123`.
- **`UploadPanel`**: File drop zone with progress indicator and quick link to history.
- **`HistoryView`**: Table of stored conversations fetched from PostgreSQL with "View Details" actions.
- **`Dashboard`**: Displays hero sentiment card, KPI grid, Recharts donut pie chart, Call Insights, LangGraph Agent Insights, Extractive Summary, and the sentence analysis table.

## 11. Environment Variables
Stored in `.env` (configured from `.env.example`):
```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=sentiment_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/sentiment_db
```

## 12. How to Run

### 1. Start PostgreSQL Database
```bash
docker compose up -d
```

### 2. Start Application (Unified Launcher)
```bash
npm install
npm run dev
```
Starts both the FastAPI backend (port 8000) and Vite React frontend (port 5173).

## 13. Testing
Automated and verified:
- PostgreSQL Docker container startup and healthcheck (`5433:5432`).
- Sentence splitting and RoBERTa classification inference.
- LangGraph conditional insight routing for both positive/neutral and negative-dominant transcripts.
- Mathematical consistency validation in `validation_node`.
- Relational storage across `conversations`, `sentence_analysis`, and `conversation_kpis`.
- Historical lookup via `GET /conversations` and `GET /conversations/{id}`.
- Full UI browser execution via browser subagent (Login -> History -> Details -> Dashboard -> New Analysis).

## 14. Known Limitations
- **Demo Auth**: Login is a frontend credential gate; the API does not issue JWT session tokens.
- **Batch Processing**: All sentence inference runs synchronously within the request lifecycle. Extremely large files (>10,000 lines) could cause request latency.
- **Regex Sentence Boundary**: Abbreviations (e.g., "Dr.", "Inc.") can occasionally cause sentence splits.
