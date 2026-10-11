"""
FinRAG — Analytics API endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.database import get_db
from app.models.chunk import DocumentChunk
from app.models.company import Company
from app.models.document import Document, DocumentStatus
from app.models.financial_metric import FinancialMetric
from app.models.ingestion_job import IngestionJob
from app.schemas.schemas import OverviewStats
from app.services.financial_analysis.analysis_service import financial_analysis_service
from app.services.retrieval.vector_store import get_vector_store

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
logger = get_logger(__name__)
settings = get_settings()


@router.get("/overview", response_model=OverviewStats)
def get_overview(db: Session = Depends(get_db)):
    """Get system overview statistics."""
    total_docs = (
        db.query(func.count(Document.id))
        .filter(Document.status != DocumentStatus.DELETED)
        .scalar() or 0
    )
    total_companies = db.query(func.count(Company.id)).scalar() or 0
    total_chunks = db.query(func.count(DocumentChunk.id)).scalar() or 0
    total_metrics = db.query(func.count(FinancialMetric.id)).scalar() or 0

    # Distinct fiscal years across all metrics
    fiscal_years = (
        db.query(FinancialMetric.fiscal_year)
        .distinct()
        .all()
    )
    total_fiscal_years = len(fiscal_years)

    # Recent ingestion jobs
    recent_jobs = (
        db.query(IngestionJob)
        .order_by(IngestionJob.created_at.desc())
        .limit(5)
        .all()
    )

    vector_store = get_vector_store()

    return OverviewStats(
        total_documents=total_docs,
        total_companies=total_companies,
        total_fiscal_years=total_fiscal_years,
        total_chunks=total_chunks,
        total_metrics=total_metrics,
        faiss_total_vectors=vector_store.total_vectors,
        llm_provider=settings.llm_provider,
        recent_jobs=recent_jobs,
        recent_queries=[],
    )


@router.get("/companies")
def get_companies(db: Session = Depends(get_db)):
    """Get all companies with their financial data coverage."""
    return financial_analysis_service.get_all_companies_summary(db)


@router.get("/financials")
def get_financials(
    company_id: Optional[str] = Query(default=None),
    company_name: Optional[str] = Query(default=None),
    fiscal_year: Optional[str] = Query(default=None),
    metric_name: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Get financial metrics for one or all companies.
    Returns flat list of metric items compatible with the frontend analytics table and charts.
    """
    query = db.query(FinancialMetric, Company).join(Company, FinancialMetric.company_id == Company.id)

    if company_id:
        query = query.filter(FinancialMetric.company_id == company_id)
    elif company_name:
        query = query.filter(Company.name.ilike(f"%{company_name}%"))

    if fiscal_year:
        query = query.filter(FinancialMetric.fiscal_year == fiscal_year)

    if metric_name:
        normalized = metric_name.lower().strip().replace(" ", "_").replace("-", "_")
        query = query.filter(
            (FinancialMetric.metric_name == metric_name) |
            (FinancialMetric.metric_name == normalized)
        )

    rows = query.order_by(FinancialMetric.fiscal_year.desc(), FinancialMetric.metric_name.asc()).all()

    results = []
    for metric, comp in rows:
        results.append({
            "id": metric.id,
            "company_id": metric.company_id,
            "company_name": comp.name,
            "ticker": comp.ticker or "",
            "fiscal_year": metric.fiscal_year,
            "period_type": metric.reporting_period or "FY",
            "metric_name": metric.metric_name.replace("_", " ").title(),
            "metric_category": metric.metric_category or "income_statement",
            "value": metric.value,
            "unit": metric.unit or "M",
            "filing_reference": f"Page {metric.source_page}" if metric.source_page else "Annual Report",
            "is_synthetic": metric.is_synthetic,
        })

    return results


@router.get("/yoy")
def get_yoy_change(
    company_id: Optional[str] = Query(default=None),
    company_name: Optional[str] = Query(default=None),
    year1: Optional[str] = Query(default=None),
    year2: Optional[str] = Query(default=None),
    base_year: Optional[str] = Query(default=None),
    comparison_year: Optional[str] = Query(default=None),
    metric: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Calculate Year-over-Year change for a specific metric or all metrics of a company.
    Supports year1/year2 and base_year/comparison_year naming.
    """
    # Resolve company
    company = None
    if company_id:
        company = db.query(Company).filter(Company.id == company_id).first()
    elif company_name:
        company = db.query(Company).filter(
            (Company.name.ilike(f"%{company_name}%")) |
            (Company.ticker.ilike(f"%{company_name}%"))
        ).first()

    if not company:
        # Default to first company if none specified
        company = db.query(Company).first()
        if not company:
            raise HTTPException(status_code=404, detail="No companies found in database")

    # Resolve fiscal years
    y1 = year1 or base_year or "FY2023"
    y2 = year2 or comparison_year or "FY2024"

    # Single metric query
    if metric:
        yoy = financial_analysis_service.calculate_yoy_change(
            db, company.name, metric, y1, y2
        )
        return {
            "company_name": yoy.company_name,
            "ticker": company.ticker or "",
            "year1": yoy.base_year,
            "year2": yoy.comparison_year,
            "metric": yoy.metric_name,
            "base_year": yoy.base_year,
            "comparison_year": yoy.comparison_year,
            "base_value": yoy.base_value,
            "comparison_value": yoy.comparison_value,
            "absolute_change": yoy.absolute_change,
            "percentage_change": yoy.percentage_change,
            "currency": yoy.currency,
            "unit": yoy.unit,
            "calculation": yoy.calculation,
            "warning": yoy.warning,
            "metrics": [
                {
                    "metric_name": yoy.metric_name.replace("_", " ").title(),
                    "year1_value": yoy.base_value or 0.0,
                    "year2_value": yoy.comparison_value or 0.0,
                    "abs_change": yoy.absolute_change or 0.0,
                    "pct_change": yoy.percentage_change or 0.0,
                    "unit": yoy.unit,
                }
            ],
        }

    # All metrics query for company across y1 and y2
    m1_rows = (
        db.query(FinancialMetric)
        .filter(FinancialMetric.company_id == company.id, FinancialMetric.fiscal_year == y1)
        .all()
    )
    m2_rows = (
        db.query(FinancialMetric)
        .filter(FinancialMetric.company_id == company.id, FinancialMetric.fiscal_year == y2)
        .all()
    )

    m1_map = {m.metric_name: m for m in m1_rows}
    m2_map = {m.metric_name: m for m in m2_rows}

    all_metric_names = sorted(set(list(m1_map.keys()) + list(m2_map.keys())))
    yoy_metrics = []

    for m_name in all_metric_names:
        v1_obj = m1_map.get(m_name)
        v2_obj = m2_map.get(m_name)

        v1 = v1_obj.value if v1_obj else 0.0
        v2 = v2_obj.value if v2_obj else 0.0
        unit = (v2_obj.unit if v2_obj else None) or (v1_obj.unit if v1_obj else "M")

        abs_diff = round(v2 - v1, 2)
        pct_diff = round(((v2 - v1) / abs(v1) * 100), 2) if v1 != 0 else 0.0

        yoy_metrics.append({
            "metric_name": m_name.replace("_", " ").title(),
            "year1_value": v1,
            "year2_value": v2,
            "abs_change": abs_diff,
            "pct_change": pct_diff,
            "unit": unit,
        })

    return {
        "company_name": company.name,
        "ticker": company.ticker or "",
        "year1": y1,
        "year2": y2,
        "metrics": yoy_metrics,
    }
