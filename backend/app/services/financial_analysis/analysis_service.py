"""
FinRAG — SQL-backed financial analysis service.
Uses only parameterized SQLAlchemy queries — never raw LLM-generated SQL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.core.logging import get_logger
from app.models.company import Company
from app.models.financial_metric import FinancialMetric

logger = get_logger(__name__)

# Supported metric names (normalized)
SUPPORTED_METRICS = {
    "revenue", "net_revenue", "total_revenue",
    "cost_of_revenue", "cost_of_goods_sold", "cogs",
    "gross_profit",
    "operating_expenses", "opex",
    "operating_income", "ebit",
    "net_income", "net_earnings",
    "total_assets",
    "total_liabilities",
    "cash_flow_operations", "operating_cash_flow",
    "ebitda",
    "research_development", "r_and_d",
    "selling_general_admin", "sga",
}


@dataclass
class MetricValue:
    metric_name: str
    fiscal_year: str
    value: Optional[float]
    currency: str
    unit: str
    is_derived: bool
    source_page: Optional[int]
    document_id: Optional[str]
    is_synthetic: bool = False


@dataclass
class YoYChange:
    metric_name: str
    company_name: str
    base_year: str
    comparison_year: str
    base_value: Optional[float]
    comparison_value: Optional[float]
    absolute_change: Optional[float]
    percentage_change: Optional[float]
    currency: str
    unit: str
    calculation: str
    warning: Optional[str] = None


@dataclass
class FinancialSummaryResult:
    company_id: str
    company_name: str
    ticker: Optional[str]
    fiscal_years: list[str]
    metrics_by_year: dict[str, dict[str, MetricValue]]  # year → metric_name → value
    margins: dict[str, dict[str, Optional[float]]]  # year → margin_name → value
    warnings: list[str] = field(default_factory=list)


class FinancialAnalysisService:
    """
    Validated SQL-backed financial calculations.
    All queries use SQLAlchemy ORM — no raw LLM SQL.
    """

    def get_metric_values(
        self,
        db: Session,
        company_name: str,
        metric_name: str,
        fiscal_years: Optional[list[str]] = None,
    ) -> list[MetricValue]:
        """Fetch metric values for a company, optionally filtered by fiscal years."""
        company = self._find_company(db, company_name)
        if not company:
            return []

        normalized = self._normalize_metric_name(metric_name)

        query = db.query(FinancialMetric).filter(
            and_(
                FinancialMetric.company_id == company.id,
                FinancialMetric.metric_name == normalized,
            )
        )

        if fiscal_years:
            query = query.filter(FinancialMetric.fiscal_year.in_(fiscal_years))

        rows = query.order_by(FinancialMetric.fiscal_year).all()

        return [
            MetricValue(
                metric_name=r.metric_name,
                fiscal_year=r.fiscal_year,
                value=r.value,
                currency=r.currency,
                unit=r.unit,
                is_derived=r.is_derived,
                source_page=r.source_page,
                document_id=r.document_id,
                is_synthetic=r.is_synthetic,
            )
            for r in rows
        ]

    def calculate_yoy_change(
        self,
        db: Session,
        company_name: str,
        metric_name: str,
        base_year: str,
        comparison_year: str,
    ) -> YoYChange:
        """Calculate year-over-year absolute and percentage change for a metric."""
        values = self.get_metric_values(
            db, company_name, metric_name, fiscal_years=[base_year, comparison_year]
        )

        val_map = {v.fiscal_year: v for v in values}
        base = val_map.get(base_year)
        comp = val_map.get(comparison_year)

        company = self._find_company(db, company_name)
        company_display = company.name if company else company_name
        currency = base.currency if base else (comp.currency if comp else "USD")
        unit = base.unit if base else (comp.unit if comp else "millions")

        warnings = []
        absolute_change = None
        pct_change = None
        calculation = ""

        if base is None or base.value is None:
            warnings.append(f"No {metric_name} data found for {base_year}.")
        if comp is None or comp.value is None:
            warnings.append(f"No {metric_name} data found for {comparison_year}.")

        if base and base.value is not None and comp and comp.value is not None:
            # Validate compatible currencies
            if base.currency != comp.currency:
                warnings.append(
                    f"Currency mismatch: {base_year}={base.currency}, {comparison_year}={comp.currency}. "
                    "Cannot reliably compare."
                )
            else:
                absolute_change = comp.value - base.value
                if base.value != 0:
                    pct_change = (absolute_change / abs(base.value)) * 100
                    calculation = (
                        f"({comp.value:.2f} - {base.value:.2f}) / |{base.value:.2f}| × 100 "
                        f"= {pct_change:.2f}%"
                    )
                else:
                    calculation = f"Base year value is zero; percentage change undefined."
                    warnings.append("Base year value is zero; percentage change is undefined.")

        return YoYChange(
            metric_name=self._normalize_metric_name(metric_name),
            company_name=company_display,
            base_year=base_year,
            comparison_year=comparison_year,
            base_value=base.value if base else None,
            comparison_value=comp.value if comp else None,
            absolute_change=absolute_change,
            percentage_change=pct_change,
            currency=currency,
            unit=unit,
            calculation=calculation,
            warning="; ".join(warnings) if warnings else None,
        )

    def get_financial_summary(
        self,
        db: Session,
        company_name: str,
    ) -> Optional[FinancialSummaryResult]:
        """Get all financial metrics for a company, organized by year."""
        company = self._find_company(db, company_name)
        if not company:
            return None

        rows = (
            db.query(FinancialMetric)
            .filter(FinancialMetric.company_id == company.id)
            .order_by(FinancialMetric.fiscal_year, FinancialMetric.metric_name)
            .all()
        )

        fiscal_years = sorted({r.fiscal_year for r in rows})
        metrics_by_year: dict[str, dict[str, MetricValue]] = {}

        for row in rows:
            year = row.fiscal_year
            if year not in metrics_by_year:
                metrics_by_year[year] = {}
            metrics_by_year[year][row.metric_name] = MetricValue(
                metric_name=row.metric_name,
                fiscal_year=row.fiscal_year,
                value=row.value,
                currency=row.currency,
                unit=row.unit,
                is_derived=row.is_derived,
                source_page=row.source_page,
                document_id=row.document_id,
                is_synthetic=row.is_synthetic,
            )

        # Calculate margins
        margins: dict[str, dict[str, Optional[float]]] = {}
        for year, year_metrics in metrics_by_year.items():
            revenue = year_metrics.get("revenue")
            gross_profit = year_metrics.get("gross_profit")
            net_income = year_metrics.get("net_income")
            operating_income = year_metrics.get("operating_income")

            rev_val = revenue.value if revenue else None

            margins[year] = {
                "gross_margin": self._safe_pct(gross_profit.value if gross_profit else None, rev_val),
                "net_margin": self._safe_pct(net_income.value if net_income else None, rev_val),
                "operating_margin": self._safe_pct(operating_income.value if operating_income else None, rev_val),
            }

        return FinancialSummaryResult(
            company_id=company.id,
            company_name=company.name,
            ticker=company.ticker,
            fiscal_years=fiscal_years,
            metrics_by_year=metrics_by_year,
            margins=margins,
        )

    def get_all_companies_summary(self, db: Session) -> list[dict]:
        """Return a list of all companies with their available fiscal years."""
        companies = db.query(Company).all()
        results = []
        for company in companies:
            fiscal_years = (
                db.query(FinancialMetric.fiscal_year)
                .filter(FinancialMetric.company_id == company.id)
                .distinct()
                .all()
            )
            results.append({
                "id": company.id,
                "name": company.name,
                "ticker": company.ticker,
                "sector": company.sector,
                "fiscal_years": sorted([fy[0] for fy in fiscal_years]),
            })
        return results

    def is_metric_supported(self, metric_name: str) -> bool:
        return self._normalize_metric_name(metric_name) in SUPPORTED_METRICS

    @staticmethod
    def _normalize_metric_name(name: str) -> str:
        """Normalize metric name to lowercase with underscores."""
        normalized = name.lower().strip().replace(" ", "_").replace("-", "_")
        # Alias mapping
        aliases = {
            "net_revenue": "revenue",
            "total_revenue": "revenue",
            "cost_of_goods_sold": "cost_of_revenue",
            "cogs": "cost_of_revenue",
            "opex": "operating_expenses",
            "ebit": "operating_income",
            "net_earnings": "net_income",
            "operating_cash_flow": "cash_flow_operations",
            "r_and_d": "research_development",
            "sga": "selling_general_admin",
        }
        return aliases.get(normalized, normalized)

    @staticmethod
    def _find_company(db: Session, name_or_ticker: str) -> Optional[Company]:
        """Find company by name (case-insensitive) or ticker."""
        company = (
            db.query(Company)
            .filter(
                Company.name.ilike(f"%{name_or_ticker}%")
                | (Company.ticker == name_or_ticker.upper())
            )
            .first()
        )
        return company

    @staticmethod
    def _safe_pct(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
        if numerator is None or denominator is None or denominator == 0:
            return None
        return round((numerator / denominator) * 100, 2)


# Module-level singleton
financial_analysis_service = FinancialAnalysisService()
