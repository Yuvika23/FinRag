"""
FinRAG — EvaluationRun and EvaluationResult ORM models.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Text, Float, Integer, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Aggregate metrics
    avg_recall_at_k: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_precision_at_k: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_mrr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_citation_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_faithfulness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    failed_queries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    results: Mapped[list] = relationship("EvaluationResult", back_populates="run", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<EvaluationRun(name={self.name!r})>"


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_sources: Mapped[Optional[object]] = mapped_column(JSON, nullable=True)
    retrieved_sources: Mapped[Optional[object]] = mapped_column(JSON, nullable=True)

    # Individual metrics
    recall_at_k: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    precision_at_k: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mrr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    citation_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    faithfulness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    run: Mapped["EvaluationRun"] = relationship("EvaluationRun", back_populates="results")

    def __repr__(self) -> str:
        return f"<EvaluationResult(run_id={self.run_id!r}, question={self.question[:50]!r})>"
