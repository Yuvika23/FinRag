#!/usr/bin/env python3
"""
FinRAG — Demo Data Import Script
Imports synthetic sample documents and financial metrics into FinRAG.

Usage:
    cd backend
    python ../scripts/import_demo_data.py

Requires: backend dependencies installed, PostgreSQL running, .env configured.

IMPORTANT: All data imported by this script is SYNTHETIC and clearly labeled as such.
           It is NOT real financial information.
"""

import os
import sys
import uuid
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from app.db.database import create_tables, get_db_context
from app.models.company import Company
from app.models.document import DocumentStatus, DocumentType
from app.models.financial_metric import FinancialMetric
from app.services.ingestion.ingestion_pipeline import ingest_document

SAMPLE_DOCS_DIR = Path(__file__).parent.parent / "data" / "sample_documents"


def create_companies(db):
    """Create synthetic company records."""
    companies_data = [
        {
            "id": str(uuid.uuid4()),
            "name": "TechVision Corp",
            "ticker": "TVIZ",
            "sector": "Technology",
            "description": "[SYNTHETIC] Leading enterprise software and cloud infrastructure company. Demo data only.",
        },
        {
            "id": str(uuid.uuid4()),
            "name": "GlobalBank Financial Group",
            "ticker": "GBF",
            "sector": "Financials",
            "description": "[SYNTHETIC] Diversified financial services group. Demo data only.",
        },
    ]

    created = {}
    for data in companies_data:
        # Check if already exists
        existing = db.query(Company).filter(Company.ticker == data["ticker"]).first()
        if existing:
            print(f"  Company already exists: {data['name']} ({data['ticker']})")
            created[data["ticker"]] = existing
            continue

        company = Company(**data)
        db.add(company)
        db.flush()
        created[data["ticker"]] = company
        print(f"  Created company: {data['name']} ({data['ticker']})")

    db.commit()
    return created


def create_financial_metrics(db, companies: dict):
    """Insert synthetic structured financial metrics."""
    tviz = companies.get("TVIZ")
    gbf = companies.get("GBF")

    metrics = []

    if tviz:
        # TechVision FY2024
        tviz_fy24 = [
            ("revenue", "income_statement", 4250.0, "FY2024"),
            ("cost_of_revenue", "income_statement", 1530.0, "FY2024"),
            ("gross_profit", "income_statement", 2720.0, "FY2024"),
            ("operating_expenses", "income_statement", 1657.5, "FY2024"),
            ("operating_income", "income_statement", 1062.5, "FY2024"),
            ("net_income", "income_statement", 892.5, "FY2024"),
            ("total_assets", "balance_sheet", 8500.0, "FY2024"),
            ("total_liabilities", "balance_sheet", 3400.0, "FY2024"),
            ("cash_flow_operations", "cash_flow", 1275.0, "FY2024"),
            ("research_development", "income_statement", 765.0, "FY2024"),
            ("selling_general_admin", "income_statement", 892.5, "FY2024"),
        ]

        # TechVision FY2023
        tviz_fy23 = [
            ("revenue", "income_statement", 3750.0, "FY2023"),
            ("cost_of_revenue", "income_statement", 1387.5, "FY2023"),
            ("gross_profit", "income_statement", 2362.5, "FY2023"),
            ("operating_expenses", "income_statement", 1537.5, "FY2023"),
            ("operating_income", "income_statement", 825.0, "FY2023"),
            ("net_income", "income_statement", 637.5, "FY2023"),
            ("total_assets", "balance_sheet", 7250.0, "FY2023"),
            ("total_liabilities", "balance_sheet", 3100.0, "FY2023"),
            ("cash_flow_operations", "cash_flow", 1050.0, "FY2023"),
            ("research_development", "income_statement", 712.5, "FY2023"),
            ("selling_general_admin", "income_statement", 825.0, "FY2023"),
        ]

        for name, category, value, year in tviz_fy24 + tviz_fy23:
            # Skip if already exists
            exists = db.query(FinancialMetric).filter(
                FinancialMetric.company_id == tviz.id,
                FinancialMetric.metric_name == name,
                FinancialMetric.fiscal_year == year,
            ).first()
            if not exists:
                metrics.append(FinancialMetric(
                    id=str(uuid.uuid4()),
                    company_id=tviz.id,
                    metric_name=name,
                    metric_category=category,
                    value=value,
                    value_precise=value,
                    currency="USD",
                    unit="millions",
                    fiscal_year=year,
                    reporting_period="FY",
                    is_derived=False,
                    is_synthetic=True,
                    notes="SYNTHETIC DATA — not real financial information",
                ))

    if gbf:
        # GlobalBank FY2024
        gbf_fy24 = [
            ("revenue", "income_statement", 7980.0, "FY2024"),
            ("net_income", "income_statement", 2260.0, "FY2024"),
            ("operating_expenses", "income_statement", 4389.0, "FY2024"),
            ("total_assets", "balance_sheet", 185000.0, "FY2024"),
            ("total_liabilities", "balance_sheet", 169100.0, "FY2024"),
        ]

        gbf_fy23 = [
            ("revenue", "income_statement", 7200.0, "FY2023"),
            ("net_income", "income_statement", 1959.0, "FY2023"),
            ("operating_expenses", "income_statement", 4104.0, "FY2023"),
            ("total_assets", "balance_sheet", 170000.0, "FY2023"),
            ("total_liabilities", "balance_sheet", 154700.0, "FY2023"),
        ]

        for name, category, value, year in gbf_fy24 + gbf_fy23:
            exists = db.query(FinancialMetric).filter(
                FinancialMetric.company_id == gbf.id,
                FinancialMetric.metric_name == name,
                FinancialMetric.fiscal_year == year,
            ).first()
            if not exists:
                metrics.append(FinancialMetric(
                    id=str(uuid.uuid4()),
                    company_id=gbf.id,
                    metric_name=name,
                    metric_category=category,
                    value=value,
                    value_precise=value,
                    currency="USD",
                    unit="millions",
                    fiscal_year=year,
                    reporting_period="FY",
                    is_derived=False,
                    is_synthetic=True,
                    notes="SYNTHETIC DATA — not real financial information",
                ))

    if metrics:
        db.bulk_save_objects(metrics)
        db.commit()
        print(f"  Created {len(metrics)} financial metric records.")
    else:
        print("  All financial metrics already exist — skipping.")


def ingest_sample_documents(db, companies: dict):
    """Ingest synthetic sample documents into the vector index."""
    doc_configs = [
        {
            "filename": "TechVision_Annual_Report_FY2024.txt",
            "document_type": DocumentType.ANNUAL_REPORT,
            "company_name": "TechVision Corp",
            "ticker": "TVIZ",
            "fiscal_year": "FY2024",
            "reporting_period": "FY",
        },
        {
            "filename": "TechVision_Annual_Report_FY2023.txt",
            "document_type": DocumentType.ANNUAL_REPORT,
            "company_name": "TechVision Corp",
            "ticker": "TVIZ",
            "fiscal_year": "FY2023",
            "reporting_period": "FY",
        },
        {
            "filename": "GlobalBank_Annual_Report_FY2024.txt",
            "document_type": DocumentType.ANNUAL_REPORT,
            "company_name": "GlobalBank Financial Group",
            "ticker": "GBF",
            "fiscal_year": "FY2024",
            "reporting_period": "FY",
        },
    ]

    for config in doc_configs:
        file_path = SAMPLE_DOCS_DIR / config["filename"]
        if not file_path.exists():
            print(f"  WARNING: Sample file not found: {file_path}")
            continue

        try:
            print(f"  Ingesting: {config['filename']} ...")
            document, job = ingest_document(
                db=db,
                file_path=file_path,
                original_filename=config["filename"],
                document_type=config["document_type"],
                company_name=config["company_name"],
                ticker=config["ticker"],
                fiscal_year=config["fiscal_year"],
                reporting_period=config["reporting_period"],
                is_synthetic=True,
            )
            print(
                f"    [OK] Indexed: {document.chunk_count} chunks, "
                f"status={document.status.value}"
            )
        except ValueError as e:
            if "already exists" in str(e):
                print(f"    Already indexed — skipping.")
            else:
                print(f"    ERROR: {e}")
        except Exception as e:
            print(f"    FAILED: {e}")


def main():
    print("=" * 60)
    print("FinRAG — Demo Data Import")
    print("WARNING: All imported data is SYNTHETIC (not real financials)")
    print("=" * 60)

    # Initialize DB tables
    print("\n[1/4] Initializing database tables...")
    try:
        create_tables()
        print("  [OK] Database tables ready.")
    except Exception as e:
        print(f"  FATAL: Cannot connect to database: {e}")
        print("  Ensure PostgreSQL is running and .env is configured.")
        sys.exit(1)

    with get_db_context() as db:
        # Create companies
        print("\n[2/4] Creating company records...")
        companies = create_companies(db)

        # Create financial metrics
        print("\n[3/4] Inserting financial metrics...")
        create_financial_metrics(db, companies)

        # Ingest documents
        print("\n[4/4] Ingesting sample documents...")
        ingest_sample_documents(db, companies)

    print("\n" + "=" * 60)
    print("[OK] Demo data import complete!")
    print("You can now start asking questions in the FinRAG interface.")
    print("=" * 60)


if __name__ == "__main__":
    main()
