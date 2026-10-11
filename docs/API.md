# FinRAG REST API Reference

The FinRAG backend exposes a high-performance RESTful API documented automatically via OpenAPI / Swagger at `/docs` (and ReDoc at `/redoc`).

Base URL: `http://localhost:8000`

---

## 1. System Health

### `GET /api/health`
Checks backend responsiveness, database connection, FAISS index state, and active LLM provider.

**Response `200 OK`**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "faiss_total_vectors": 48,
  "llm_provider": "none"
}
```

---

## 2. Companies & Financials

### `GET /api/companies`
Lists all tracked companies.

### `POST /api/companies`
Registers a new company.
```json
{
  "name": "TechVision Inc.",
  "ticker": "TCVX",
  "sector": "Technology",
  "industry": "Enterprise Software",
  "currency": "USD"
}
```

### `GET /api/companies/{id}`
Returns details for a specific company along with its indexed documents and metric count.

---

## 3. Documents & Ingestion

### `GET /api/documents`
Lists documents with pagination and optional status filter (`indexed`, `processing`, `failed`).

### `POST /api/documents/upload`
Uploads and triggers ingestion for a PDF or TXT financial filing.
- **Content-Type**: `multipart/form-data`
- **Fields**:
  - `file`: Binary file (`.pdf` or `.txt`)
  - `company_name`: string (optional)
  - `ticker`: string (optional)
  - `fiscal_year`: string (e.g., `"FY2024"`)
  - `document_type`: string (`annual_report`, `quarterly_filing`, `earnings_transcript`, `other`)

### `GET /api/documents/{id}`
Returns document processing metadata, page count, chunk count, and parsing status.

### `DELETE /api/documents/{id}`
Deletes the document, cascades removal of its chunks in the database, and rebuilds the FAISS vector index.

### `POST /api/documents/{id}/reindex`
Re-runs extraction, chunking, and embedding for an existing document.

---

## 4. Query & Research Assistant

### `POST /api/chat`
The unified search and reasoning endpoint. Classifies the query and executes vector search, SQL analysis, or hybrid synthesis.

**Request**:
```json
{
  "query": "What was the operating margin for TechVision in FY2024 and what drove it?",
  "company_id": null,
  "fiscal_year": "FY2024",
  "top_k": 5
}
```

**Response `200 OK`**:
```json
{
  "query": "What was the operating margin for TechVision in FY2024 and what drove it?",
  "route_taken": "combined",
  "answer": "TechVision reported an operating margin of 21.6% in FY2024 compared to 19.5% in FY2023. Management attributed this expansion to enterprise cloud migration and cost efficiencies.",
  "citations": [
    {
      "source_document": "TechVision_Annual_Report_FY2024.txt",
      "page_number": 3,
      "chunk_id": "8a719d30-...",
      "snippet": "Operating margin expanded 210 basis points to 21.6% driven by enterprise cloud subscription growth..."
    }
  ],
  "sql_data": [
    {
      "company": "TechVision Inc.",
      "metric": "Operating Margin",
      "fiscal_year": "FY2024",
      "value": 21.6,
      "unit": "%"
    }
  ],
  "latency_ms": 142.5
}
```

---

## 5. Structured Analytics

### `GET /api/analytics/overview`
Aggregated counts: total indexed documents, companies, fiscal years covered, and total vectors.

### `GET /api/analytics/financials?company_id={id}&metric={name}`
Returns time-series metric data for chart rendering.

### `GET /api/analytics/yoy?company_id={id}&year1=FY2023&year2=FY2024`
Returns structured Year-over-Year comparison metrics with exact percentage and delta calculations.

---

## 6. Evaluation Benchmark

### `POST /api/evaluation/run`
Executes the evaluation dataset against the active retrieval index.

### `GET /api/evaluation/results`
Lists historical evaluation runs with aggregate metrics (Recall@K, MRR, Citation Accuracy, Faithfulness).
