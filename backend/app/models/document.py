"""
FinRAG — Document ORM model.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, DateTime, Text, Integer, BigInteger,
    ForeignKey, Enum as SAEnum, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.database import Base


class DocumentType(str, enum.Enum):
    ANNUAL_REPORT = "annual_report"
    QUARTERLY_FILING = "quarterly_filing"
    EARNINGS_TRANSCRIPT = "earnings_transcript"
    CSV_METRICS = "csv_metrics"
    OTHER = "other"


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    DELETED = "deleted"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    company_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256
    document_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType), nullable=False, default=DocumentType.OTHER
    )
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus), nullable=False, default=DocumentStatus.PENDING
    )
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fiscal_year: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reporting_period: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="documents")
    chunks: Mapped[list] = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    ingestion_jobs: Mapped[list] = relationship("IngestionJob", back_populates="document")
    financial_metrics: Mapped[list] = relationship("FinancialMetric", back_populates="document")

    def __repr__(self) -> str:
        return f"<Document(filename={self.filename!r}, status={self.status})>"
