"""
FinRAG — Companies API endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.company import Company
from app.models.document import Document, DocumentStatus
from app.schemas.schemas import CompanyCreate, CompanyRead

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("", response_model=list[CompanyRead])
def list_companies(db: Session = Depends(get_db)):
    """List all companies."""
    companies = db.query(Company).order_by(Company.name).all()
    result = []
    for c in companies:
        doc_count = (
            db.query(Document)
            .filter(Document.company_id == c.id, Document.status != DocumentStatus.DELETED)
            .count()
        )
        data = CompanyRead.model_validate(c)
        data.document_count = doc_count
        result.append(data)
    return result


@router.post("", response_model=CompanyRead, status_code=201)
def create_company(company: CompanyCreate, db: Session = Depends(get_db)):
    """Create a new company record."""
    import uuid
    db_company = Company(
        id=str(uuid.uuid4()),
        name=company.name,
        ticker=company.ticker,
        sector=company.sector,
        description=company.description,
    )
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    data = CompanyRead.model_validate(db_company)
    data.document_count = 0
    return data


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(company_id: str, db: Session = Depends(get_db)):
    """Get company by ID."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    data = CompanyRead.model_validate(company)
    data.document_count = (
        db.query(Document)
        .filter(Document.company_id == company_id, Document.status != DocumentStatus.DELETED)
        .count()
    )
    return data
