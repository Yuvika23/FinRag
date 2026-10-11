"""
FinRAG — Retrieval service.
Handles query embedding, FAISS search, metadata filtering, and passage ranking.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.services.embeddings.embedding_service import embedding_service
from app.services.retrieval.vector_store import vector_store

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class RetrievedPassage:
    chunk_id: str
    document_id: str
    document_name: str
    company_name: Optional[str]
    ticker: Optional[str]
    fiscal_year: Optional[str]
    document_type: Optional[str]
    page_number: Optional[int]
    text: str
    similarity_score: float


def retrieve_passages(
    query: str,
    db: Session,
    top_k: Optional[int] = None,
    company_filter: Optional[str] = None,
    fiscal_year_filter: Optional[str] = None,
) -> list[RetrievedPassage]:
    """
    Retrieve the most relevant document passages for a query.

    Steps:
    1. Embed the query.
    2. Filter eligible chunk IDs from DB (company/year filters).
    3. Search FAISS with optional pre-filter.
    4. Fetch chunk metadata from DB.
    5. Return ranked passages with metadata.
    """
    k = top_k or settings.faiss_top_k

    if vector_store.is_empty():
        logger.info("retrieval_skipped", reason="Vector store is empty")
        return []

    # --- Embed query ---
    query_embedding = embedding_service.embed_query(query)

    # --- Build filter set from DB if needed ---
    filter_chunk_ids: Optional[set[str]] = None

    if company_filter or fiscal_year_filter:
        filter_chunk_ids = _get_eligible_chunk_ids(db, company_filter, fiscal_year_filter)
        if not filter_chunk_ids:
            logger.info("retrieval_no_matching_chunks", company=company_filter, year=fiscal_year_filter)
            return []

    # --- FAISS search ---
    raw_results = vector_store.search(query_embedding, top_k=k, filter_chunk_ids=filter_chunk_ids)

    if not raw_results:
        return []

    # --- Fetch chunk metadata from DB ---
    chunk_ids = [cid for cid, _ in raw_results]
    score_map = {cid: score for cid, score in raw_results}

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.id.in_(chunk_ids))
        .all()
    )

    # Build doc_id → document mapping for filenames
    doc_ids = {c.document_id for c in chunks}
    docs = db.query(Document).filter(Document.id.in_(doc_ids)).all()
    doc_map = {d.id: d for d in docs}

    # --- Assemble passages ---
    passages: list[RetrievedPassage] = []
    for chunk in chunks:
        doc = doc_map.get(chunk.document_id)
        passages.append(
            RetrievedPassage(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_name=doc.original_filename if doc else chunk.source_filename or "Unknown",
                company_name=chunk.company_name,
                ticker=chunk.ticker,
                fiscal_year=chunk.fiscal_year,
                document_type=chunk.document_type,
                page_number=chunk.page_number,
                text=chunk.text,
                similarity_score=score_map.get(chunk.id, 0.0),
            )
        )

    # Sort by similarity score descending (preserving FAISS ranking)
    passages.sort(key=lambda p: p.similarity_score, reverse=True)

    logger.info(
        "retrieval_complete",
        query_preview=query[:80],
        results=len(passages),
        top_score=passages[0].similarity_score if passages else None,
    )

    return passages


def _get_eligible_chunk_ids(
    db: Session,
    company_filter: Optional[str],
    fiscal_year_filter: Optional[str],
) -> set[str]:
    """
    Return chunk IDs that match the given company and/or fiscal year filters.
    """
    query = db.query(DocumentChunk.id)

    if company_filter:
        # Match against company_name (case-insensitive) or ticker
        company_upper = company_filter.upper()
        query = query.filter(
            (DocumentChunk.company_name.ilike(f"%{company_filter}%"))
            | (DocumentChunk.ticker == company_upper)
        )

    if fiscal_year_filter:
        query = query.filter(DocumentChunk.fiscal_year == fiscal_year_filter)

    result = query.all()
    return {row[0] for row in result}
