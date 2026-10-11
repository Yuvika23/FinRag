"""
FinRAG — Document management API endpoints.
"""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.database import get_db
from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.ingestion_job import IngestionJob
from app.schemas.schemas import (
    DocumentDeleteResponse,
    DocumentRead,
    DocumentUploadResponse,
    IngestionJobRead,
)
from app.services.ingestion.ingestion_pipeline import (
    delete_document,
    ingest_document,
    reindex_document,
    validate_upload,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])
logger = get_logger(__name__)
settings = get_settings()


@router.get("", response_model=list[DocumentRead])
def list_documents(
    skip: int = 0,
    limit: int = 50,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
):
    """List all documents with optional status filter."""
    query = db.query(Document).filter(Document.status != DocumentStatus.DELETED)

    if status_filter:
        try:
            query = query.filter(Document.status == DocumentStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")

    documents = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
    return documents


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(default="other"),
    company_name: str | None = Form(default=None),
    ticker: str | None = Form(default=None),
    fiscal_year: str | None = Form(default=None),
    reporting_period: str | None = Form(default=None),
    is_synthetic: bool = Form(default=False),
    db: Session = Depends(get_db),
):
    """
    Upload and ingest a financial document (PDF or TXT).
    Validates file type and size before processing.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    original_filename = file.filename
    suffix = Path(original_filename).suffix.lower()
    safe_filename = f"{uuid.uuid4()}{suffix}"

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / safe_filename

    # Save file to disk
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    file_size = file_path.stat().st_size

    # Validate
    try:
        validate_upload(file_path, file_size)
    except ValueError as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e))

    # Parse document type
    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        doc_type = DocumentType.OTHER

    # Run ingestion
    try:
        document, job = ingest_document(
            db=db,
            file_path=file_path,
            original_filename=original_filename,
            document_type=doc_type,
            company_name=company_name,
            ticker=ticker,
            fiscal_year=fiscal_year,
            reporting_period=reporting_period,
            is_synthetic=is_synthetic,
        )
    except ValueError as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error("upload_failed", filename=original_filename, error=str(e))
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

    return DocumentUploadResponse(
        document_id=document.id,
        job_id=job.id,
        message=(
            f"Document ingested successfully: {document.chunk_count} chunks indexed."
            if document.status == "indexed"
            else "Document is being processed."
        ),
        filename=original_filename,
    )


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, db: Session = Depends(get_db)):
    """Get document details by ID."""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.status != DocumentStatus.DELETED,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
def delete_document_endpoint(document_id: str, db: Session = Depends(get_db)):
    """Delete a document and its vector index entries."""
    try:
        chunks_removed = delete_document(db, document_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("delete_failed", document_id=document_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Deletion failed: {e}")

    return DocumentDeleteResponse(
        message="Document and associated index entries deleted.",
        document_id=document_id,
        chunks_removed=chunks_removed,
    )


@router.post("/{document_id}/reindex", response_model=DocumentUploadResponse)
def reindex_document_endpoint(document_id: str, db: Session = Depends(get_db)):
    """Re-process and re-index an existing document."""
    try:
        document, job = reindex_document(db, document_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("reindex_failed", document_id=document_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Re-indexing failed: {e}")

    return DocumentUploadResponse(
        document_id=document.id,
        job_id=job.id,
        message=f"Document re-indexed: {document.chunk_count} chunks.",
        filename=document.original_filename,
    )


@router.get("/{document_id}/job", response_model=IngestionJobRead)
def get_ingestion_job(document_id: str, db: Session = Depends(get_db)):
    """Get the most recent ingestion job status for a document."""
    job = (
        db.query(IngestionJob)
        .filter(IngestionJob.document_id == document_id)
        .order_by(IngestionJob.created_at.desc())
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="No ingestion job found for this document.")
    return job
