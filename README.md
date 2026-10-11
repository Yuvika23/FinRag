# FinRAG — Financial Filing Intelligence Engine

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-teal.svg)](https://fastapi.tiangolo.com/)
[![FAISS](https://img.shields.io/badge/FAISS-Vector%20Search-orange.svg)](https://github.com/facebookresearch/faiss)
[![Next.js](https://img.shields.io/badge/Next.js-14%20App%20Router-black.svg)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**FinRAG** is a production-style Financial Filing Intelligence Engine designed to analyze annual reports (10-Ks), quarterly filings (10-Qs), and earnings call transcripts. It integrates **dense vector retrieval (FAISS)** with **structured relational SQL analytics (PostgreSQL/SQLite)** and **source-grounded LLM synthesis**, ensuring zero-hallucination numerical calculations, verifiable page citations, and quantitative evaluation benchmarks.

---

## Key Features

- **Document Ingestion Engine**: Page-aware extraction for `.pdf` (PyMuPDF) and `.txt` filings with SHA-256 deduplication and sliding-window chunking.
- **Dense Vector Search**: `sentence-transformers/all-MiniLM-L6-v2` dense embeddings stored in a thread-safe `faiss.IndexFlatIP` index with persistent metadata sidecars.
- **Structured SQL Financial Analytics**: Parameterized SQL analytics calculating YoY growth, revenue bridges, and operating margins without risky LLM-generated raw SQL.
- **Three-Path Hybrid Router**:
  - **Qualitative Route**: Semantic search over disclosures, management commentary, and risk factors.
  - **Numerical Route**: Direct relational SQL querying for deterministic financial numbers.
  - **Combined Route**: Merges structured SQL tables with qualitative passage evidence into the synthesis context.
- **Transparent LLM Synthesis**: Supports OpenAI, Anthropic, Google Gemini, local HuggingFace, or **graceful zero-hallucination fallback** (`LLM_PROVIDER=none`) displaying exact cited passages.
- **Quantitative RAG Evaluation Benchmark**: Automated evaluation measuring **Recall@K**, **Precision@K**, **MRR**, **Citation Accuracy**, and **Faithfulness** against ground-truth financial filings.
- **Modern Interactive Dashboard**: Next.js 14 frontend with interactive research chat, citation side-drawers, interactive financial trend charts, document management, and evaluation analytics.

---

## System Architecture

```
[ Financial Reports / Filings (.pdf, .txt) ]
                      │
                      ▼
        [ Ingestion Pipeline ]
  (PyMuPDF -> Sliding Window -> SHA-256)
             │                 │
             ▼                 ▼
   [ FAISS Vector Store ]  [ PostgreSQL / SQLite ]
  (Dense 384d Embeddings)  (Companies, Metrics, Jobs)
             │                 │
             └────────┬────────┘
                      ▼
            [ RAG Orchestrator ]
         (3-Way Intent Classifier)
                      │
                      ▼
     [ LLM Synthesis / Evidence Engine ]
                      │
                      ▼
         [ Next.js Web Interface ]
```

---

## Quickstart Guide

### 1. Prerequisites
- **Python**: 3.11+ (Python 3.13 supported)
- **Node.js**: v18+ (v22 recommended)
- **Git**

*(Optional: Docker & Docker Compose if running PostgreSQL via containers. SQLite is supported out of the box for lightweight local development without Docker).*

---

### 2. Clone and Setup Environment

```bash
git clone https://github.com/your-username/FinRAG.git
cd FinRAG
```

Copy the example environment configuration:

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux:**
```bash
cp .env.example .env
```

Configure your `.env` file as desired:
- To run with **SQLite** (no Docker required): keep `DATABASE_URL=sqlite:///./finrag.db`
- To run with **PostgreSQL**: start Docker (`docker compose up -d postgres`) and uncomment PostgreSQL host settings.
- To enable an LLM provider: set `LLM_PROVIDER=openai` (or `anthropic` / `google`) and provide your API key. Set `LLM_PROVIDER=none` to run in transparent evidence-only mode.

---

### 3. Backend Setup

**Windows (PowerShell):**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### 4. Initialize Database & Import Demo Data

Run the demo data import script to seed sample companies (TechVision Inc., GlobalBank Corp), structured financial metrics for FY2023 & FY2024, and ingest sample financial disclosures:

**Windows (PowerShell):**
```powershell
cd backend
python ..\scripts\import_demo_data.py
```

**macOS / Linux:**
```bash
cd backend
python ../scripts/import_demo_data.py
```

---

### 5. Launch the Backend Server

```powershell
# From the backend directory with venv activated:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- API Base: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

---

### 6. Frontend Setup & Launch

Open a separate terminal window:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

---

## Running the Benchmark Evaluation

FinRAG includes a financial QA benchmark dataset at `data/evaluation/eval_dataset.json`.

1. In the Web UI, navigate to the **Evaluation** tab (`/evaluation`).
2. Click **Run Benchmark**.
3. View real-time scores for **Recall@K**, **Precision@K**, **MRR**, **Citation Accuracy**, and **Faithfulness**.

Alternatively, trigger via API:
```bash
curl -X POST http://localhost:8000/api/evaluation/run \
  -H "Content-Type: application/json" \
  -d '{"name": "Local Test Run"}'
```

---

## Running Backend Tests

```powershell
cd backend
pytest tests/ -v
```

---

## Project Structure

```
FinRAG/
├── backend/
│   ├── app/
│   │   ├── api/                 # FastAPI router endpoints (chat, documents, analytics, eval)
│   │   ├── core/                # Config, logging, settings
│   │   ├── db/                  # SQLAlchemy database session & engine
│   │   ├── models/              # ORM models (company, document, chunk, metrics, eval)
│   │   ├── schemas/             # Pydantic request & response schemas
│   │   ├── services/
│   │   │   ├── embeddings/      # Sentence-transformers singleton
│   │   │   ├── evaluation/      # Recall, Precision, MRR, Faithfulness calculator
│   │   │   ├── financial_analysis/ # Structured SQL analytics & YoY math
│   │   │   ├── generation/      # LLM clients & hybrid RAG orchestrator
│   │   │   ├── ingestion/       # PDF/TXT extraction, chunking, deduplication
│   │   │   └── retrieval/       # FAISS vector store & metadata hydration
│   │   └── main.py              # Application entrypoint & lifespan
│   ├── tests/                   # Pytest test suite
│   ├── requirements.txt
│   └── pytest.ini
├── data/
│   ├── evaluation/              # eval_dataset.json benchmark
│   └── sample_documents/        # Labeled synthetic financial filings
├── docs/
│   ├── ARCHITECTURE.md          # Detailed architectural blueprint
│   ├── DATA_PIPELINE.md         # Ingestion, chunking, and embedding specs
│   ├── RAG_EVALUATION.md        # Retrieval & faithfulness metrics definitions
│   └── API.md                   # REST API documentation
├── frontend/                    # Next.js 14 web application
├── scripts/
│   ├── init_db.sql              # PostgreSQL DDL schema
│   └── import_demo_data.py      # Seed data script
├── docker-compose.yml           # PostgreSQL service container
├── .env.example
└── README.md
```

---

## License

MIT License. Designed and engineered for high-precision financial disclosure research.
