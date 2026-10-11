"""
FinRAG — FinancialMetric ORM model.
Stores structured financial data extracted from filings.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, DateTime, Text, Integer, Float, Numeric,
    ForeignKey, Boolean, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class FinancialMetric(Base):
    __tablename__ = "financial_metrics"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )

    # Metric identification
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metric_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # e.g. income_statement, balance_sheet, cash_flow

    # Value
    value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Using Numeric for high-precision storage
    value_precise: Mapped[Optional[object]] = mapped_column(Numeric(20, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="millions")
    # e.g. millions, billions, units

    # Period
    fiscal_year: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reporting_period: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # e.g. Q1, Q2, Q3, Q4, FY, H1, H2

    # Source traceability
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_derived: Mapped[bool] = mapped_column(Boolean, default=False)
    # True = calculated from other metrics, False = directly reported
    derivation_formula: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="financial_metrics")
    document: Mapped[Optional["Document"]] = relationship("Document", back_populates="financial_metrics")

    def __repr__(self) -> str:
        return (
            f"<FinancialMetric(company={self.company_id!r}, "
            f"metric={self.metric_name!r}, year={self.fiscal_year!r}, "
            f"value={self.value})>"
        )
