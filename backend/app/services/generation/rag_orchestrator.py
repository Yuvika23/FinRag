"""
FinRAG — Query router and RAG orchestrator.
Routes questions to: qualitative (RAG only), numerical (SQL only), or combined.
"""

from __future__ import annotations

import re
import time
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.schemas.schemas import ChatResponse, Citation, SQLResult
from app.services.financial_analysis.analysis_service import financial_analysis_service
from app.services.generation.llm_client import llm_client
from app.services.retrieval.retrieval_service import RetrievedPassage, retrieve_passages

logger = get_logger(__name__)

# Keywords that suggest numerical/SQL analysis is needed
NUMERICAL_KEYWORDS = {
    "revenue", "income", "profit", "margin", "growth", "change", "increase", "decrease",
    "earnings", "ebitda", "assets", "liabilities", "cash", "expenses", "cost",
    "percent", "%", "year-over-year", "yoy", "quarter", "fy20", "fy19", "fy21",
    "fy22", "fy23", "fy24", "fy25", "2020", "2021", "2022", "2023", "2024", "2025",
    "compare", "comparison", "trend", "metrics", "financial results",
}

QUALITATIVE_KEYWORDS = {
    "why", "reason", "explain", "cause", "factor", "strategy", "management",
    "outlook", "guidance", "risk", "challenge", "opportunity", "plan", "initiative",
    "comment", "note", "describe", "how did", "what happened",
}


def classify_query(question: str) -> str:
    """
    Classify a question into: 'numerical', 'qualitative', or 'combined'.
    """
    q_lower = question.lower()

    has_numerical = any(kw in q_lower for kw in NUMERICAL_KEYWORDS)
    has_qualitative = any(kw in q_lower for kw in QUALITATIVE_KEYWORDS)

    if has_numerical and has_qualitative:
        return "combined"
    elif has_numerical:
        return "numerical"
    else:
        return "qualitative"


def answer_question(
    question: str,
    db: Session,
    company_filter: Optional[str] = None,
    fiscal_year_filter: Optional[str] = None,
    top_k: int = 8,
    include_sql: bool = True,
) -> ChatResponse:
    """
    Main RAG orchestration entry point.
    Routes to the appropriate path and generates a cited answer.
    """
    start_time = time.time()
    query_type = classify_query(question)

    logger.info("chat_query", question=question[:100], query_type=query_type)

    passages: list[RetrievedPassage] = []
    sql_results: list[SQLResult] = []
    warnings: list[str] = []

    # --- Path A / C: Retrieve document passages ---
    if query_type in ("qualitative", "combined"):
        passages = retrieve_passages(
            query=question,
            db=db,
            top_k=top_k,
            company_filter=company_filter,
            fiscal_year_filter=fiscal_year_filter,
        )
        if not passages:
            warnings.append("No relevant document passages were found for this query.")

    # --- Path B / C: Fetch SQL-backed financial data ---
    if query_type in ("numerical", "combined") and include_sql:
        sql_results = _run_sql_analysis(question, db, company_filter, fiscal_year_filter)

    # --- Build citations ---
    citations = _build_citations(passages)

    # --- Generate answer ---
    answer, insufficient = _generate_answer(
        question=question,
        passages=passages,
        sql_results=sql_results,
        query_type=query_type,
        warnings=warnings,
    )

    latency_ms = (time.time() - start_time) * 1000

    return ChatResponse(
        answer=answer,
        citations=citations,
        sql_results=sql_results,
        query_type=query_type,
        retrieved_passages=[
            {
                "chunk_id": p.chunk_id,
                "document_name": p.document_name,
                "page_number": p.page_number,
                "text_preview": p.text[:300],
                "similarity_score": round(p.similarity_score, 4),
                "company_name": p.company_name,
                "fiscal_year": p.fiscal_year,
            }
            for p in passages[:5]
        ],
        warnings=warnings,
        insufficient_evidence=insufficient,
        latency_ms=round(latency_ms, 2),
    )


def _run_sql_analysis(
    question: str,
    db: Session,
    company_filter: Optional[str],
    fiscal_year_filter: Optional[str],
) -> list[SQLResult]:
    """
    Detect the metric and fiscal years in the question and run SQL analysis.
    Uses a controlled mapping — no LLM-generated SQL.
    """
    results = []

    # Detect company
    company_name = company_filter
    if not company_name:
        # Try to find a company name in the question from DB
        from app.models.company import Company
        companies = db.query(Company).all()
        q_lower = question.lower()
        for c in companies:
            c_name_lower = c.name.lower()
            name_tokens = [
                tok.strip(",.") for tok in c_name_lower.split()
                if tok not in ("corp", "corporation", "inc", "group", "co", "ltd", "holdings")
            ]
            if (
                c_name_lower in q_lower
                or (c.ticker and c.ticker.lower() in q_lower)
                or any(tok in q_lower for tok in name_tokens if len(tok) >= 3)
            ):
                company_name = c.name
                break

    if not company_name:
        return []

    # Detect fiscal years
    fiscal_years = re.findall(r"\bFY(\d{4})\b|\b(20\d{2})\b", question, re.IGNORECASE)
    years = []
    for fy, yr in fiscal_years:
        if fy:
            years.append(f"FY{fy}")
        elif yr:
            years.append(f"FY{yr}")

    if fiscal_year_filter and fiscal_year_filter not in years:
        years.append(fiscal_year_filter)

    # Detect metric
    metric = _detect_metric(question)
    if not metric:
        return []

    # Fetch values
    values = financial_analysis_service.get_metric_values(db, company_name, metric, fiscal_years=years or None)

    if not values:
        results.append(
            SQLResult(
                query_description=f"{metric} for {company_name}",
                metric_name=metric,
                company=company_name,
                values={},
                warning=f"No {metric} data found for {company_name}" + (f" in {', '.join(years)}" if years else ""),
            )
        )
        return results

    vals_dict = {v.fiscal_year: v.value for v in values}
    currency = values[0].currency if values else "USD"
    unit = values[0].unit if values else "millions"

    result = SQLResult(
        query_description=f"{metric} for {company_name}",
        metric_name=metric,
        company=company_name,
        values={k: v for k, v in vals_dict.items()},
    )

    # YoY calculation if two years found
    if len(years) == 2:
        yoy = financial_analysis_service.calculate_yoy_change(
            db, company_name, metric, years[0], years[1]
        )
        if yoy.percentage_change is not None:
            result.calculation = (
                f"YoY change from {years[0]} to {years[1]}: "
                f"{yoy.percentage_change:+.2f}% ({yoy.absolute_change:+.2f} {currency} {unit})\n"
                f"Formula: {yoy.calculation}"
            )
        if yoy.warning:
            result.warning = yoy.warning

    results.append(result)
    return results


def _detect_metric(question: str) -> Optional[str]:
    """Map question keywords to a supported metric name."""
    q = question.lower()
    metric_map = {
        "revenue": ["revenue", "sales", "turnover"],
        "net_income": ["net income", "net profit", "net earnings", "bottom line"],
        "gross_profit": ["gross profit", "gross income"],
        "operating_income": ["operating income", "operating profit", "ebit"],
        "operating_expenses": ["operating expenses", "opex", "operating costs"],
        "cost_of_revenue": ["cost of revenue", "cost of goods", "cogs"],
        "total_assets": ["total assets"],
        "total_liabilities": ["total liabilities"],
        "cash_flow_operations": ["cash flow", "operating cash"],
        "ebitda": ["ebitda"],
        "research_development": ["research and development", "r&d", "r and d"],
    }
    for metric_name, keywords in metric_map.items():
        if any(kw in q for kw in keywords):
            return metric_name
    return None


def _build_citations(passages: list[RetrievedPassage]) -> list[Citation]:
    return [
        Citation(
            chunk_id=p.chunk_id,
            document_id=p.document_id,
            document_name=p.document_name,
            company_name=p.company_name,
            fiscal_year=p.fiscal_year,
            page_number=p.page_number,
            passage_preview=p.text[:250],
            similarity_score=round(p.similarity_score, 4),
        )
        for p in passages
    ]


def _generate_answer(
    question: str,
    passages: list[RetrievedPassage],
    sql_results: list[SQLResult],
    query_type: str,
    warnings: list[str],
) -> tuple[str, bool]:
    """
    Generate answer text. Uses LLM if available, otherwise builds a structured evidence summary.
    Returns (answer_text, insufficient_evidence_flag).
    """
    has_evidence = bool(passages or sql_results)
    insufficient = not has_evidence

    if not llm_client.is_available():
        # Fallback: Build structured evidence summary without LLM
        return _build_evidence_summary(question, passages, sql_results, query_type, warnings), insufficient

    # Build the prompt
    system_prompt = (
        "You are a precise financial analysis assistant. "
        "Answer questions using ONLY the provided evidence — never invent figures or citations. "
        "Cite sources by their document name and page number. "
        "Distinguish reported facts from derived calculations. "
        "If evidence is insufficient, state exactly what is missing."
    )

    evidence_blocks = []

    if sql_results:
        evidence_blocks.append("=== STRUCTURED FINANCIAL DATA (from database) ===")
        for sr in sql_results:
            evidence_blocks.append(f"\nMetric: {sr.metric_name} | Company: {sr.company}")
            for year, val in sr.values.items():
                evidence_blocks.append(f"  {year}: {val}")
            if sr.calculation:
                evidence_blocks.append(f"  Calculation: {sr.calculation}")
            if sr.warning:
                evidence_blocks.append(f"  Warning: {sr.warning}")

    if passages:
        evidence_blocks.append("\n=== RETRIEVED DOCUMENT PASSAGES ===")
        for i, p in enumerate(passages[:6], 1):
            citation_ref = f"[Source: {p.document_name}, Page {p.page_number or 'N/A'}]"
            evidence_blocks.append(f"\n[{i}] {citation_ref}\n{p.text[:600]}")

    if not evidence_blocks:
        evidence_blocks.append(
            "No relevant evidence was found for this question. "
            "Please ensure the relevant documents have been ingested."
        )

    evidence_text = "\n".join(evidence_blocks)

    prompt = (
        f"Question: {question}\n\n"
        f"{evidence_text}\n\n"
        "Instructions:\n"
        "1. Answer the question using only the evidence above.\n"
        "2. Cite sources as (Document Name, p.X) for any factual claim.\n"
        "3. If you use a calculated figure, show the formula.\n"
        "4. If evidence is insufficient, say so explicitly.\n"
        "5. Do not invent any numbers or citations.\n\n"
        "Answer:"
    )

    llm_answer = llm_client.generate(prompt, system_prompt=system_prompt)

    if llm_answer:
        return llm_answer.strip(), insufficient
    else:
        return _build_evidence_summary(question, passages, sql_results, query_type, warnings), insufficient


def _build_evidence_summary(
    question: str,
    passages: list[RetrievedPassage],
    sql_results: list[SQLResult],
    query_type: str,
    warnings: list[str],
) -> str:
    """
    Build a structured evidence summary when no LLM is configured.
    This is transparent and citable but not prose-form.
    """
    lines = [
        "**Note:** LLM is not configured (set LLM_PROVIDER in .env to enable AI-generated answers). "
        "Showing retrieved evidence directly.\n"
    ]

    if sql_results:
        lines.append("### Structured Financial Data\n")
        for sr in sql_results:
            lines.append(f"**{sr.metric_name}** — {sr.company}")
            for year, val in sr.values.items():
                lines.append(f"- {year}: {val:,.2f}" if isinstance(val, float) else f"- {year}: {val}")
            if sr.calculation:
                lines.append(f"- **Calculation:** {sr.calculation}")
            if sr.warning:
                lines.append(f"- ⚠️ {sr.warning}")
            lines.append("")

    if passages:
        lines.append("### Retrieved Document Passages\n")
        for i, p in enumerate(passages[:5], 1):
            src = f"{p.document_name}" + (f", p.{p.page_number}" if p.page_number else "")
            lines.append(f"**[{i}]** *{src}* (similarity: {p.similarity_score:.3f})")
            lines.append(f"> {p.text[:400]}")
            lines.append("")

    if not sql_results and not passages:
        lines.append(
            "No relevant evidence was found. Please ingest documents and try again, "
            "or refine your question."
        )

    if warnings:
        lines.append("\n### Warnings")
        for w in warnings:
            lines.append(f"- ⚠️ {w}")

    return "\n".join(lines)
