"""
FinRAG — Document ingestion pipeline.
Orchestrates extraction → chunking → embedding → FAISS indexing → DB persistence.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.ingestion_job import IngestionJob, JobStatus
from app.services.embeddings.embedding_service import embedding_service
from app.services.ingestion.chunker import chunk_pages
from app.services.ingestion.extractor import extract_document
from app.services.retrieval.vector_store import vector_store

logger = get_logger(__name__)
settings = get_settings()

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".text"}
ALLOWED_MIME_TYPES = {"application/pdf", "text/plain"}


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file for duplicate detection."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def validate_upload(
    file_path: Path,
    file_size: int,
) -> None:
    """
    Validate uploaded file before processing.
    Raises ValueError with a clear message on failure.
    """
    suffix = file_path.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: '{suffix}'. "
            f"Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    if file_size > settings.max_file_size_bytes:
        raise ValueError(
            f"File too large: {file_size / 1024 / 1024:.1f} MB. "
            f"Maximum allowed: {settings.max_file_size_mb} MB."
        )

    if not file_path.exists():
        raise ValueError(f"File not found at path: {file_path}")


def find_duplicate(db: Session, file_hash: str) -> Optional[Document]:
    """Check if a document with the same hash already exists."""
    return (
        db.query(Document)
        .filter(
            Document.file_hash == file_hash,
            Document.status != DocumentStatus.DELETED,
        )
        .first()
    )


def ingest_document(
    db: Session,
    file_path: Path,
    original_filename: str,
    document_type: DocumentType = DocumentType.OTHER,
    company_name: Optional[str] = None,
    ticker: Optional[str] = None,
    fiscal_year: Optional[str] = None,
    reporting_period: Optional[str] = None,
    is_synthetic: bool = False,
) -> tuple[Document, IngestionJob]:
    """
    Full ingestion pipeline for a single document.

    Returns (document, ingestion_job).
    The job status reflects success or failure.
    """
    file_size = file_path.stat().st_size
    file_hash = compute_file_hash(file_path)

    # Check for duplicate
    existing = find_duplicate(db, file_hash)
    if existing:
        logger.warning(
            "duplicate_document",
            filename=original_filename,
            existing_id=existing.id,
        )
        raise ValueError(
            f"A document with the same content already exists: '{existing.original_filename}' "
            f"(ID: {existing.id}). Use the re-index endpoint to re-process it."
        )

    # Create document record
    doc_id = str(uuid.uuid4())
    document = Document(
        id=doc_id,
        filename=file_path.name,
        original_filename=original_filename,
        file_path=str(file_path),
        file_size=file_size,
        file_hash=file_hash,
        document_type=document_type,
        status=DocumentStatus.PENDING,
        company_name=company_name,
        ticker=ticker,
        fiscal_year=fiscal_year,
        reporting_period=reporting_period,
        is_synthetic=is_synthetic,
    )
    db.add(document)

    # Create ingestion job
    job = IngestionJob(
        document_id=doc_id,
        status=JobStatus.RUNNING,
        progress=0.0,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(document)
    db.refresh(job)

    try:
        _run_pipeline(db, document, job)
    except Exception as e:
        logger.error("ingestion_failed", document_id=doc_id, error=str(e))
        document.status = DocumentStatus.FAILED
        document.error_message = str(e)
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise

    return document, job


def _run_pipeline(db: Session, document: Document, job: IngestionJob) -> None:
    """Execute the sequential ingestion stages."""
    doc_id = document.id

    # ── Stage 1: Text Extraction ──────────────────────────────────────
    _update_job(db, job, progress=0.1, stage="Extracting text")
    document.status = DocumentStatus.PROCESSING
    db.commit()

    file_path = Path(document.file_path)
    extraction_result = extract_document(file_path)

    document.page_count = extraction_result.total_pages
    job.pages_extracted = extraction_result.extracted_pages
    _update_job(db, job, progress=0.3, stage="Chunking text")

    # ── Stage 2: Chunking ─────────────────────────────────────────────
    non_empty_pages = [p for p in extraction_result.pages if not p.is_empty]

    if not non_empty_pages:
        raise ValueError(
            "No extractable text found in this document. "
            "If it's a scanned PDF, OCR processing is required."
        )

    chunks = chunk_pages(
        pages=non_empty_pages,
        document_id=doc_id,
        company_name=document.company_name,
        ticker=document.ticker,
        fiscal_year=document.fiscal_year,
        document_type=document.document_type.value if document.document_type else None,
        source_filename=document.original_filename,
    )

    job.chunks_created = len(chunks)
    _update_job(db, job, progress=0.5, stage="Generating embeddings")

    # ── Stage 3: Embeddings ───────────────────────────────────────────
    texts = [c.text for c in chunks]
    embeddings = embedding_service.embed_texts(texts, batch_size=32)
    job.embeddings_generated = len(embeddings)
    _update_job(db, job, progress=0.7, stage="Indexing in FAISS")

    # ── Stage 4: FAISS Indexing ───────────────────────────────────────
    # First persist chunks to DB to get their IDs
    db_chunks = []
    for chunk in chunks:
        db_chunk = DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            page_number=chunk.page_number,
            start_char=chunk.start_char,
            end_char=chunk.end_char,
            token_count=chunk.token_count,
            company_name=chunk.company_name,
            ticker=chunk.ticker,
            fiscal_year=chunk.fiscal_year,
            document_type=chunk.document_type,
            source_filename=chunk.source_filename,
        )
        db_chunks.append(db_chunk)

    db.bulk_save_objects(db_chunks)
    db.flush()

    # Add to FAISS
    chunk_ids = [c.id for c in db_chunks]
    faiss_ids = vector_store.add_embeddings(embeddings, chunk_ids)

    # Update chunks with their FAISS IDs
    for db_chunk, faiss_id in zip(db_chunks, faiss_ids):
        db_chunk.faiss_id = faiss_id

    _update_job(db, job, progress=0.9, stage="Saving metadata")

    # ── Stage 5: Finalize ─────────────────────────────────────────────
    document.chunk_count = len(chunks)
    document.status = DocumentStatus.INDEXED

    job.status = JobStatus.COMPLETED
    job.progress = 1.0
    job.current_stage = "Completed"
    job.completed_at = datetime.now(timezone.utc)

    db.commit()

    logger.info(
        "ingestion_complete",
        document_id=doc_id,
        chunks=len(chunks),
        pages=extraction_result.total_pages,
    )


def delete_document(db: Session, document_id: str) -> int:
    """
    Delete a document and all associated chunks from DB and FAISS index.
    Returns the number of chunks removed.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise ValueError(f"Document not found: {document_id}")

    # Get chunk IDs to remove from FAISS
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
    chunk_ids = {c.id for c in chunks}

    # Remove from FAISS index
    removed = vector_store.remove_by_chunk_ids(chunk_ids)

    # Cascading delete removes chunks from DB (cascade="all, delete-orphan")
    document.status = DocumentStatus.DELETED
    db.delete(document)
    db.commit()

    logger.info("document_deleted", document_id=document_id, chunks_removed=removed)
    return removed


def reindex_document(db: Session, document_id: str) -> tuple[Document, IngestionJob]:
    """
    Re-process an existing document: delete old index entries and re-ingest.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise ValueError(f"Document not found: {document_id}")

    # Remove existing chunks from FAISS
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
    chunk_ids = {c.id for c in chunks}
    if chunk_ids:
        vector_store.remove_by_chunk_ids(chunk_ids)

    # Delete existing chunks from DB
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()

    # Reset document status
    document.status = DocumentStatus.PENDING
    document.chunk_count = None
    document.error_message = None

    # Create new job
    job = IngestionJob(
        document_id=document_id,
        status=JobStatus.RUNNING,
        progress=0.0,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(document)
    db.refresh(job)

    try:
        _run_pipeline(db, document, job)
    except Exception as e:
        logger.error("reindex_failed", document_id=document_id, error=str(e))
        document.status = DocumentStatus.FAILED
        document.error_message = str(e)
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise

    return document, job


def _update_job(db: Session, job: IngestionJob, progress: float, stage: str) -> None:
    job.progress = progress
    job.current_stage = stage
    db.commit()
