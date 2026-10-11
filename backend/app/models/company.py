"""
FinRAG — Company ORM model.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=True, index=True)
    sector: Mapped[str] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    documents: Mapped[list] = relationship("Document", back_populates="company")
    financial_metrics: Mapped[list] = relationship(
        "FinancialMetric", back_populates="company"
    )

    def __repr__(self) -> str:
        return f"<Company(name={self.name!r}, ticker={self.ticker!r})>"
