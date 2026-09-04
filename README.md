# Vercel Link: 
https://sentiment-analyzer-full-stack-ai-on.vercel.app/

# Sentiment Analyzer

A modern full-stack AI application for analyzing customer-service conversation transcripts. Upload a `.txt` transcript to classify sentence-by-sentence sentiment, compute conversation-level analytics, extract actionable call insights, and explore saved analysis history.

---

## Features

- **Sentence-Level Sentiment Analysis**: Automatically classifies every sentence in a conversation as Positive, Negative, or Neutral with confidence scores using a preloaded transformer model.
- **Visual Analytics Dashboard**: Interactive donut chart, dominant sentiment badge, and positive/negative ratio breakdowns.
- **Actionable Call Insights**: Automatically detects overall conversation tone, flags customer friction points, and evaluates churn and escalation risk.
- **Persistent Conversation History**: Stores all past transcripts and analyses so you can revisit and review previous calls at any time without re-uploading.
- **One-Command Local Startup**: Launch both the backend API and frontend dashboard concurrently with a single command.

---

## Architecture

```text
React Frontend (Vite, Port 5173)
        │
        ▼  POST /analyze (multipart .txt)
FastAPI Backend (Port 8000)
        │
        ▼
Orchestration Pipeline
 ├── 1. Transcript Processing  (Sentence extraction & normalization)
 ├── 2. Sentiment Analysis     (Transformer sentence classification)
 ├── 3. Metrics Derivation     (Deterministic ratios & counts)
 ├── 4. Call Insights Engine   (Tone detection & friction extraction)
 ├── 5. Integrity Verification (Data consistency check)
 └── 6. Data Persistence       (Saves conversation, sentences, and metrics)
        │
        ▼
PostgreSQL Database (Port 5433)
        │
        ▼
FastAPI JSON Response ──► React Dashboard
```

---

## Project Structure

```text
Sentiment_Analyzer/
├── backend/
│   ├── database.py             # Database models and connection pooling
│   ├── graph.py                # Analysis pipeline and routing workflow
│   ├── main.py                 # FastAPI service and API routes
│   └── requirements.txt        # Python backend dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # React dashboard and history components
│   │   ├── main.jsx            # Application entry point
│   │   └── styles.css          # Design system, layout, and styling
│   ├── package.json            # Frontend dependencies
│   └── vercel.json             # Vercel deployment configuration
├── docker-compose.yml          # Local database container configuration
├── package.json                # Unified launcher configuration
├── sample_conversation.txt     # Ready-to-use sample transcript
├── PROJECT_CONTEXT.md          # Comprehensive technical documentation
└── AGENTS.md                   # AI pair-programming instructions
```

---

## Quick Start (Local Setup)

### 1. Start the Database

```bash
docker compose up -d
```

### 2. Start the Application

From the project root directory:

```bash
npm install
npm run dev
```

This concurrently starts:
* **Frontend Web App**: `http://localhost:5173`
* **Backend API**: `http://localhost:8000`
* **API Documentation**: `http://localhost:8000/docs`

### Demo Login
* **Username**: `admin`
* **Password**: `admin123`

### Stopping the Application
Press `Ctrl+C` in your terminal to stop both servers together.

To stop the database:
```bash
docker compose down
```

---

## Manual Startup (Alternative)

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

## Deployment Guide

### Deploying the Frontend (Vercel)
1. Import this repository into [Vercel](https://vercel.com).
2. The included `vercel.json` automatically configures the build:
   * **Build Command**: `npm --prefix frontend run build`
   * **Output Directory**: `frontend/dist`
3. Under **Environment Variables**, add:
   * `VITE_API_URL`: The public HTTPS URL of your deployed backend API.
4. Click **Deploy**.

### Deploying the Backend & Database (e.g., Render / Railway)
1. Create a PostgreSQL database instance and copy its connection URL.
2. Deploy the `backend/` as a Python web service:
   * **Build Command**: `pip install -r backend/requirements.txt`
   * **Start Command**: `uvicorn main:app --app-dir backend --host 0.0.0.0 --port $PORT`
   * **Environment Variable**: `DATABASE_URL` set to your database connection string.

---

## API Reference

### `GET /health`
Returns service readiness:
```json
{
  "status": "ok",
  "model_loaded": true,
  "database_connected": true,
  "model_error": null
}
```

### `POST /analyze`
Uploads a `.txt` customer conversation transcript and returns the full analysis:
```bash
curl.exe -X POST -F "file=@sample_conversation.txt" http://localhost:8000/analyze
```

### `GET /conversations`
Retrieves past conversation analyses, sorted by most recent first.

### `GET /conversations/{id}`
Retrieves complete stored conversation details matching the `/analyze` format.

---

## Sample Output

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
