"""
FinRAG — DocumentChunk ORM model.
Each chunk corresponds to a text segment extracted from a document page.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, DateTime, Text, Integer, Float, ForeignKey, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    start_char: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_char: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Denormalized metadata for fast retrieval
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fiscal_year: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    document_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_filename: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # FAISS vector index ID
    faiss_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return (
            f"<DocumentChunk(doc_id={self.document_id!r}, "
            f"idx={self.chunk_index}, page={self.page_number})>"
        )
