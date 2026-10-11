"""
FinRAG — Pydantic schemas for all API request/response models.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict


# =========================================================
# Company schemas
# =========================================================

class CompanyBase(BaseModel):
    name: str
    ticker: Optional[str] = None
    sector: Optional[str] = None
    description: Optional[str] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyRead(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    document_count: Optional[int] = 0


# =========================================================
# Document schemas
# =========================================================

class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    original_filename: str
    file_size: int
    document_type: str
    status: str
    company_name: Optional[str] = None
    ticker: Optional[str] = None
    fiscal_year: Optional[str] = None
    reporting_period: Optional[str] = None
    page_count: Optional[int] = None
    chunk_count: Optional[int] = None
    error_message: Optional[str] = None
    is_synthetic: bool = False
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    document_id: str
    job_id: str
    message: str
    filename: str


class DocumentDeleteResponse(BaseModel):
    message: str
    document_id: str
    chunks_removed: int


# =========================================================
# IngestionJob schemas
# =========================================================

class IngestionJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    status: str
    progress: float
    current_stage: Optional[str] = None
    error_message: Optional[str] = None
    pages_extracted: Optional[int] = None
    chunks_created: Optional[int] = None
    embeddings_generated: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


# =========================================================
# Chat / RAG schemas
# =========================================================

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    company_filter: Optional[str] = None
    fiscal_year_filter: Optional[str] = None
    top_k: int = Field(default=8, ge=1, le=20)
    include_sql: bool = True


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    company_name: Optional[str] = None
    fiscal_year: Optional[str] = None
    page_number: Optional[int] = None
    passage_preview: str
    similarity_score: Optional[float] = None


class SQLResult(BaseModel):
    query_description: str
    metric_name: str
    company: str
    values: dict[str, Any]
    calculation: Optional[str] = None
    warning: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = []
    sql_results: list[SQLResult] = []
    query_type: str  # "qualitative" | "numerical" | "combined"
    retrieved_passages: list[dict] = []
    warnings: list[str] = []
    insufficient_evidence: bool = False
    latency_ms: Optional[float] = None


# =========================================================
# Financial Analytics schemas
# =========================================================

class FinancialMetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    metric_name: str
    metric_category: Optional[str] = None
    value: Optional[float] = None
    currency: str
    unit: str
    fiscal_year: str
    reporting_period: Optional[str] = None
    source_page: Optional[int] = None
    is_derived: bool
    is_synthetic: bool


class OverviewStats(BaseModel):
    total_documents: int
    total_companies: int
    total_fiscal_years: int
    total_chunks: int
    total_metrics: int = 0
    faiss_total_vectors: int = 0
    llm_provider: str = "none"
    recent_jobs: list[IngestionJobRead] = []
    recent_queries: list[dict] = []


class FinancialSummary(BaseModel):
    company_id: str
    company_name: str
    ticker: Optional[str] = None
    fiscal_years: list[str]
    metrics: dict[str, list[dict]]


# =========================================================
# Evaluation schemas
# =========================================================

class EvaluationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    total_questions: int
    completed_questions: int
    avg_recall_at_k: Optional[float] = None
    avg_precision_at_k: Optional[float] = None
    avg_mrr: Optional[float] = None
    avg_citation_accuracy: Optional[float] = None
    avg_faithfulness: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    failed_queries: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class EvaluationResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    question: str
    expected_answer: Optional[str] = None
    generated_answer: Optional[str] = None
    recall_at_k: Optional[float] = None
    precision_at_k: Optional[float] = None
    mrr: Optional[float] = None
    citation_accuracy: Optional[float] = None
    faithfulness: Optional[float] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    created_at: datetime


class RunEvaluationRequest(BaseModel):
    name: str = Field(default="Evaluation Run")
    dataset_path: Optional[str] = None
    use_builtin_dataset: bool = True
    top_k: int = Field(default=5, ge=1, le=20)
