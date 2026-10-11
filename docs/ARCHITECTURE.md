# FinRAG System Architecture

FinRAG is an enterprise-grade financial filing intelligence engine designed to extract, index, analyze, and query corporate disclosure documents (annual reports, 10-Ks, quarterly filings, and earnings transcripts). It combines dense vector retrieval (FAISS) with structured relational analysis (SQL/PostgreSQL) and LLM-powered synthesis to deliver cited, hallucination-resistant financial answers.

---

## 1. High-Level Architecture Overview

```mermaid
graph TD
    User([Financial Analyst / User]) --> Frontend[Next.js + TypeScript Web Client]
    Frontend -->|REST API Requests| Gateway[FastAPI Backend Gateway]
    
    subgraph Ingestion Pipeline
        Gateway --> Extractor[PyMuPDF Page-Aware Extractor]
        Extractor --> Chunker[Overlapping Window Chunker]
        Chunker --> Embedder[Sentence-Transformers Embedder]
        Embedder --> FAISSIndex[(FAISS Vector Index)]
        Chunker --> RDBMS[(PostgreSQL / SQLite Database)]
    end

    subgraph Query & Analytics Engine
        Gateway --> Orchestrator[RAG Orchestrator]
        Orchestrator --> Classifier{Query Classifier}
        Classifier -->|Qualitative| VectorService[FAISS Retrieval Service]
        Classifier -->|Numerical / YoY| SQLService[Financial Analysis Service]
        Classifier -->|Combined| MultiSource[Parallel Retrieval & SQL]
        
        VectorService --> FAISSIndex
        VectorService --> RDBMS
        SQLService --> RDBMS
        
        MultiSource --> LLMClient[Multi-Provider LLM Client]
        VectorService --> LLMClient
        SQLService --> LLMClient
    end

    subgraph Evaluation Harness
        Gateway --> EvalEngine[RAG Evaluation Engine]
        EvalEngine --> TestDataset[Standard Financial Eval Dataset]
        EvalEngine --> MetricsCalc[Recall@K, MRR, Faithfulness, Citation Acc]
    end

    LLMClient -->|Answer + Verifiable Citations| Frontend
```

---

## 2. Key Components

### 2.1 Backend Core (FastAPI)
- **Application Lifespan**: Initializes the database schema, ensures the persistence directory for FAISS and uploads exists, loads embedding models lazily or on startup, and releases resources on shutdown.
- **Dependency Injection**: Provides thread-safe database sessions (`get_db`) and service handles to route handlers.
- **Config & Settings**: Managed through `pydantic-settings` with `.env` precedence and automatic type validation.

### 2.2 Storage Layer
- **Relational Storage (PostgreSQL / SQLite)**:
  - `companies`: Ticker, name, sector, currency, reporting standards.
  - `documents`: File metadata, SHA-256 deduplication hash, page count, processing state.
  - `document_chunks`: Extracted text, token metrics, character offsets, source page reference, and foreign FAISS integer ID.
  - `financial_metrics`: Structured metrics (Revenue, Net Income, Operating Margin, EPS, Debt, etc.) for direct SQL aggregation.
  - `ingestion_jobs`: Real-time ingestion logs, status transitions (`pending` -> `processing` -> `indexed` / `failed`).
  - `evaluation_runs` & `evaluation_results`: Precision/Recall, MRR, and citation metrics history.
- **Vector Storage (FAISS)**:
  - `IndexFlatIP` (Inner Product on L2-normalized embeddings) providing exact cosine similarity search.
  - Accompanied by a sidecar metadata mapping (`index_metadata.json`) correlating sequential internal integer vectors with relational UUID chunk IDs.
  - Rebuilding strategy for item deletion preserving index integrity.

### 2.3 Retrieval & Hybrid Orchestration
- **Dense Embedding**: `sentence-transformers/all-MiniLM-L6-v2` produces 384-dimensional dense vectors with low latency on commodity CPUs.
- **Pre-filtering**: Vector queries can be scoped by `company_id` and `fiscal_year` using indexed foreign keys before ranking.
- **Query Classification**:
  - **Numerical Queries** (e.g., "Compare 2024 vs 2023 operating income for TechVision"): Routed to the Financial Analysis Service for deterministic, exact SQL calculations.
  - **Qualitative Queries** (e.g., "What are the primary supply chain risk factors disclosed?"): Routed to FAISS for semantic similarity search.
  - **Combined Queries** (e.g., "Why did revenue increase by 14.8% and how does management explain customer expansion?"): Executes both paths and merges the structured SQL metrics table with retrieved semantic passages into the LLM synthesis context.

### 2.4 LLM Gateway & Evidence Synthesis
- Multi-provider client abstraction supporting OpenAI (`gpt-4o-mini`), Anthropic (`claude-3-haiku`), Google Gemini (`gemini-1.5-flash`), local HuggingFace (`microsoft/phi-2`), or `none`.
- **Zero-Hallucination Fallback**: When `LLM_PROVIDER=none` or when API keys are absent, the engine falls back to an evidence-only summary displaying exact chunk quotes, source document titles, and verified page numbers without speculative generation.

---

## 3. Security & Safety Design
- **SQL Injection Prevention**: No freeform or LLM-generated raw SQL is executed against the database. All queries use SQLAlchemy Core/ORM with parameterized inputs and pre-vetted metric names.
- **File Validation**: Strict MIME-type checking, file extension whitelist (`.pdf`, `.txt`), file size bounds (max 100MB), and SHA-256 collision/deduplication checks.
- **Local Isolation**: Uploaded files and FAISS indices are scoped to dedicated project data directories outside public web roots.
