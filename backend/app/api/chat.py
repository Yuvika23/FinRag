"""
FinRAG — Chat/RAG API endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.database import get_db
from app.schemas.schemas import ChatRequest, ChatResponse
from app.services.generation.rag_orchestrator import answer_question

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = get_logger(__name__)


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Answer a financial question using RAG (retrieval + LLM) and/or SQL analysis.
    
    - Qualitative questions: retrieve document passages and generate cited answer.
    - Numerical questions: query PostgreSQL for structured financial metrics.
    - Combined questions: use both sources.
    """
    try:
        response = answer_question(
            question=request.question,
            db=db,
            company_filter=request.company_filter,
            fiscal_year_filter=request.fiscal_year_filter,
            top_k=request.top_k,
            include_sql=request.include_sql,
        )
        return response
    except Exception as e:
        logger.error("chat_error", question=request.question[:80], error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to process question: {e}")
